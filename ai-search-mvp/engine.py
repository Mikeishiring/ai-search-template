"""Durable, bounded local research runner. The adapter only exposes synthetic reads."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from adapter import SourceError, digest
from reviewer import STAGES, components, inspect, validate_finding


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, manifest TEXT NOT NULL, enumerated_end INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, lane TEXT NOT NULL, source TEXT NOT NULL,
 operation TEXT NOT NULL, args TEXT NOT NULL, reason TEXT NOT NULL, state TEXT DEFAULT 'pending',
 attempts INTEGER DEFAULT 0, error TEXT, created INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS versions(id TEXT NOT NULL, hash TEXT NOT NULL, payload TEXT NOT NULL,
 observed_at TEXT NOT NULL, PRIMARY KEY(id,hash));
CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, source TEXT NOT NULL, hash TEXT NOT NULL,
 scanned INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS attachments(id TEXT PRIMARY KEY, hash TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS edges(origin TEXT, target TEXT, kind TEXT, PRIMARY KEY(origin,target,kind));
CREATE TABLE IF NOT EXISTS receipts(seq INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, operation TEXT,
 request TEXT, response TEXT, error TEXT, observed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY, record_id TEXT NOT NULL, hash TEXT NOT NULL, payload TEXT NOT NULL);
"""


def now():
    return datetime.now(timezone.utc).isoformat()


class Runner:
    def __init__(self, path, adapter, scope, refresh=False):
        self.path, self.adapter, self.scope = path, adapter, scope
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        stored = self.meta("scope")
        if stored and json.loads(stored) != scope:
            raise ValueError("Cannot resume a different scope in the same ledger")
        if self.meta("fixture_hash") and self.meta("fixture_hash") != digest(adapter.corpus) and not refresh:
            raise ValueError("Fixture changed; use explicit refresh")
        with self.db:
            self.setmeta("scope", json.dumps(scope))
            self.setmeta("fixture_hash", digest(adapter.corpus))
            self.setmeta("reviewer", "lexical-v1; not semantic review")
            self.setmeta("status", "running")
            if refresh:
                self.db.execute("UPDATE tasks SET state='pending',error=NULL")
                self.db.execute("UPDATE sources SET enumerated_end=0")
                self.db.execute("UPDATE records SET scanned=0")
                self.db.execute("DELETE FROM findings")
                self.db.execute("DELETE FROM edges")
                for row in self.db.execute("SELECT id,args FROM tasks").fetchall():
                    args = json.loads(row["args"])
                    args.pop("cursor", None)
                    args.pop("after", None)
                    self.db.execute("UPDATE tasks SET args=? WHERE id=?", (json.dumps(args), row["id"]))
            for source in scope["sources"]:
                result = adapter.call("describe_access", source)
                manifest = result["items"][0]
                self.db.execute("INSERT INTO sources(id,manifest) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET manifest=excluded.manifest",
                                (source, json.dumps(manifest)))
                self.enqueue("coverage", source, "list_records", {"start": scope["start"], "end": scope["end"]}, "Enumerate the declared window, including earlier roots active inside it")
                self.enqueue("question", source, "search_records", {"query": scope["query"], "horizon": scope["horizon"]}, "Initial question discovery; search cannot certify coverage")

    def meta(self, key):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def setmeta(self, key, value):
        self.db.execute("INSERT INTO meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def enqueue(self, lane, source, operation, args, reason):
        if source not in self.scope["sources"]:
            return
        stable = {k: v for k, v in args.items() if k not in {"cursor", "after"}}
        key = digest([source, operation, stable])
        self.db.execute("INSERT OR IGNORE INTO tasks(id,lane,source,operation,args,reason,created) VALUES(?,?,?,?,?,?,?)",
                        (key, lane, source, operation, json.dumps(args), reason, self.db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]))

    def accept_record(self, record, observed_at):
        key = record["id"]
        if record["source"] not in self.scope["sources"] or record["date"] > self.scope["horizon"]:
            return
        h = digest(record)
        self.db.execute("INSERT OR IGNORE INTO versions VALUES(?,?,?,?)", (key, h, json.dumps(record), observed_at))
        self.db.execute("INSERT INTO records(id,source,hash) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET hash=excluded.hash,scanned=CASE WHEN records.hash=excluded.hash THEN records.scanned ELSE 0 END", (key, record["source"], h))
        self.enqueue("question", record["source"], "read_record", {"id": key}, "Read full source and inspect exact evidence spans")

    def scan(self, record):
        h = digest(record)
        self.db.execute("DELETE FROM findings WHERE record_id=?", (record["id"],))
        for finding in inspect(record):
            validate_finding(finding, {record["id"]: record})
            self.db.execute("INSERT OR REPLACE INTO findings VALUES(?,?,?,?)", (digest(finding), record["id"], h, json.dumps(finding)))
        self.db.execute("UPDATE records SET scanned=1 WHERE id=?", (record["id"],))
        if record.get("parent"):
            self.db.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?)", (record["id"], record["parent"], "replies_to"))
        for ref in record.get("links", []):
            if ref["source"] in self.scope["sources"]:
                self.db.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?)", (record["id"], ref["id"], "references"))
                self.enqueue("question", ref["source"], "read_record", {"id": ref["id"]}, f"Follow explicit source link from {record['id']}")
        if record.get("repost_of"):
            self.db.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?)", (record["id"], record["repost_of"], "reposts"))
        self.enqueue("question", record["source"], "read_context", {"id": record["id"], "horizon": self.scope["horizon"]}, "Read all available replies or nested blocks through the follow-up horizon")
        for attachment in record.get("attachments", []):
            self.enqueue("question", record["source"], "read_attachment", {"id": attachment}, f"Preserve original attachment referenced by {record['id']}")

    def plan_gaps(self):
        records = self.current_records()
        findings = self.current_findings()
        mapping = {r["id"]: r for r in records}
        added = False
        # Explicitly connected components only; never merge matching titles.
        for group in components(records):
            if not any(self.scope["query"].casefold() in (mapping[i].get("title", "") + " " + mapping[i]["body"]).casefold() for i in group):
                continue
            present = {f["category"] for f in findings if f["record_id"] in group}
            for stage in STAGES:
                if stage in present:
                    continue
                for source in self.scope["sources"]:
                    count = self.db.total_changes
                    self.enqueue("question", source, "search_records", {"query": f"{self.scope['query']} {stage.replace('_', ' ')}", "horizon": self.scope["horizon"]}, f"Missing {stage} signal in connected group {group[0]}; seek context, do not infer absence")
                    added |= self.db.total_changes > count
        return added

    def step(self, crash_before_commit=False):
        lane = "question" if self.meta("last_lane") == "coverage" else "coverage"
        task = self.db.execute("SELECT * FROM tasks WHERE state='pending' ORDER BY (lane=?) DESC, created LIMIT 1", (lane,)).fetchone()
        if task is None:
            with self.db:
                if self.plan_gaps():
                    return True
                self.setmeta("status", "retrieval_finished_with_review_limits")
            return False
        args = json.loads(task["args"])
        try:
            result = self.adapter.call(task["operation"], task["source"], **args)
        except SourceError as error:
            with self.db:
                self.db.execute("INSERT INTO receipts(task,operation,request,error,observed_at) VALUES(?,?,?,?,?)", (task["id"], task["operation"], json.dumps(args), error.code, now()))
                if error.code == "invalid_continuation":
                    args.pop("cursor", None)
                    self.db.execute("UPDATE tasks SET args=?,attempts=attempts+1 WHERE id=?", (json.dumps(args), task["id"]))
                else:
                    self.db.execute("UPDATE tasks SET state='blocked',error=?,attempts=attempts+1 WHERE id=?", (error.code, task["id"]))
                self.setmeta("last_lane", task["lane"])
            return True
        with self.db:
            self.db.execute("INSERT INTO receipts(task,operation,request,response,observed_at) VALUES(?,?,?,?,?)", (task["id"], task["operation"], json.dumps(args), json.dumps(result), result["observed_at"]))
            op = task["operation"]
            if op in {"list_records", "search_records", "read_context", "read_record"}:
                for record in result["items"]:
                    self.accept_record(record, result["observed_at"])
                    if op == "read_record" and record["date"] <= self.scope["horizon"]:
                        self.scan(record)
            elif op == "read_attachment":
                for attachment in result["items"]:
                    self.db.execute("INSERT OR REPLACE INTO attachments VALUES(?,?,?)", (attachment["id"], digest(attachment), json.dumps(attachment)))
            continuation = result["continuation"]
            if continuation and continuation["token"]:
                args.update(cursor=continuation["token"], after=continuation["durable_after"])
                self.db.execute("UPDATE tasks SET args=?,attempts=attempts+1 WHERE id=?", (json.dumps(args), task["id"]))
            else:
                self.db.execute("UPDATE tasks SET state='done',attempts=attempts+1,error=NULL WHERE id=?", (task["id"],))
                if op == "list_records":
                    self.db.execute("UPDATE sources SET enumerated_end=1 WHERE id=?", (task["source"],))
            self.setmeta("last_lane", task["lane"])
            if crash_before_commit:
                raise RuntimeError("Injected crash before atomic commit")
        return True

    def run(self, max_steps=1000):
        for _ in range(max_steps):
            if not self.step():
                return self.export()
        with self.db:
            self.setmeta("status", "budget_reached")
        return self.export()

    def current_records(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT v.payload FROM records r JOIN versions v ON r.id=v.id AND r.hash=v.hash ORDER BY r.id")]

    def current_findings(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT f.payload FROM findings f JOIN records r ON f.record_id=r.id AND f.hash=r.hash ORDER BY f.record_id,f.id")]

    def export(self):
        records = self.current_records()
        tasks = [dict(t) | {"args": json.loads(t["args"])} for t in self.db.execute("SELECT * FROM tasks ORDER BY created")]
        coverage = []
        for row in self.db.execute("SELECT * FROM sources ORDER BY id"):
            manifest = json.loads(row["manifest"])
            local = [r for r in records if r["source"] == row["id"]]
            st = [t for t in tasks if t["source"] == row["id"]]
            pending, blocked = sum(t["state"] == "pending" for t in st), sum(t["state"] == "blocked" for t in st)
            coverage.append({"source": row["id"], "platform": manifest["platform"],
                             "enumeration_end": bool(row["enumerated_end"]),
                             "records_retrieved": len(local),
                             "records_rule_scanned": self.db.execute("SELECT COUNT(*) FROM records WHERE source=? AND scanned=1", (row["id"],)).fetchone()[0],
                             "semantic_reviews": 0, "pending": pending, "blocked": blocked,
                             "retrieval_state": "partial" if pending else "with_limits" if blocked or not row["enumerated_end"] else "complete_within_fixture_scope",
                             "review_state": "candidate_evidence_only"})
        return {"synthetic": True, "scope": self.scope, "status": self.meta("status"),
                "reviewer": self.meta("reviewer"), "records": records, "findings": self.current_findings(),
                "coverage": coverage, "tasks": tasks, "components": components(records),
                "edges": [dict(r) for r in self.db.execute("SELECT * FROM edges ORDER BY origin,target,kind")],
                "receipts": self.db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0],
                "versions": self.db.execute("SELECT COUNT(*) FROM versions").fetchone()[0],
                "attachments": [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM attachments ORDER BY id")]}

    def close(self):
        self.db.close()
