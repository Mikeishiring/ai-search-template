"""Offline source adapter. No networking, arbitrary paths, or write operations."""
from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone


READS = {"describe_access", "list_records", "search_records", "read_record",
         "read_context", "read_attachment"}


class SourceError(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(detail)


class SyntheticAdapter:
    def __init__(self, corpus, page_size=2):
        if corpus.get("synthetic") is not True:
            raise ValueError("This MVP accepts its bundled synthetic fixtures only")
        self.corpus = copy.deepcopy(corpus)
        self.records = {r["id"]: r for r in self.corpus["records"]}
        self.sources = {s["id"]: s for s in self.corpus["sources"]}
        self.attachments = {a["id"]: a for a in self.corpus["attachments"]}
        self.session = uuid.uuid4().hex
        self.page_size = page_size
        self.calls = []

    def call(self, operation, source, **args):
        if operation not in READS:
            raise SourceError("operation_denied", "Operation is outside the read allowlist")
        if source not in self.sources:
            raise SourceError("access_denied", "Source is outside the fixture allowlist")
        self.calls.append({"operation": operation, "source": source, "args": args})
        items, continuation, limits = self._dispatch(operation, source, args)
        return {"request_id": uuid.uuid4().hex, "source_id": source,
                "operation": operation, "observed_at": datetime.now(timezone.utc).isoformat(),
                "items": items, "continuation": continuation, "limits": limits, "error": None}

    @staticmethod
    def key(record):
        return record["date"], record["id"]

    def page(self, rows, args):
        rows = sorted(rows, key=self.key)
        token = args.get("cursor")
        if token:
            session, offset = token.split(":")
            if session != self.session:
                raise SourceError("invalid_continuation", "Session cursor expired; use durable boundary")
            offset = int(offset)
        else:
            # Inclusive replay at the last committed record prevents boundary loss.
            boundary = args.get("after")
            offset = next((i for i, r in enumerate(rows) if self.key(r) >= tuple(boundary)), len(rows)) if boundary else 0
        batch = rows[offset:offset + self.page_size]
        nxt = offset + len(batch)
        return batch, {"token": f"{self.session}:{nxt}" if nxt < len(rows) else None,
                       "reuse_across_sessions": False,
                       "durable_after": list(self.key(batch[-1])) if batch else args.get("after")}, {
                           "expected_count": len(rows), "returned_count": len(batch),
                           "end_reached": nxt >= len(rows), "truncated": False}

    def root(self, record):
        seen = set()
        while record.get("parent"):
            if record["id"] in seen:
                raise SourceError("malformed", "Cyclic parent relationship")
            seen.add(record["id"])
            record = self.records[record["parent"]]
        return record

    def _dispatch(self, op, source, args):
        capability = self.sources[source]
        if op == "describe_access":
            return [capability], None, {"inventory": "declared_fixture_sources", "snapshot": self.corpus["snapshot"]}
        if op == "list_records":
            if not capability["enumeration"]:
                raise SourceError("unsupported", "Source offers search only; enumeration unavailable")
            start, end = args["start"], args["end"]
            roots = {}
            for r in self.records.values():
                if r["source"] == source and start <= r["date"] <= end and not r.get("link_only"):
                    root = self.root(r)
                    roots[root["id"]] = root
            return self.page(list(roots.values()), args)
        if op == "search_records":
            # Deliberately realistic limitation: only top-ranked roots; no hidden replies.
            terms = args["query"].casefold().split()
            rows = [r for r in self.records.values() if r["source"] == source and not r.get("parent")
                    and not r.get("link_only") and r["date"] <= args["horizon"]
                    and any(t in (r.get("title", "") + " " + r["body"]).casefold() for t in terms)]
            rows.sort(key=lambda r: (-sum(t in (r.get("title", "") + " " + r["body"]).casefold() for t in terms), r["id"]))
            return rows[:2], None, {"expected_count": None, "returned_count": min(len(rows), 2),
                                    "truncated": len(rows) > 2, "inventory_complete": False}
        if op == "read_record":
            r = self.records.get(args["id"])
            if not r or r["source"] != source:
                raise SourceError("unavailable_or_hidden", "Record unavailable within source")
            return [r], None, {"returned_count": 1}
        if op == "read_context":
            rows = [r for r in self.records.values() if r["source"] == source and r.get("parent") == args["id"]
                    and r["date"] <= args["horizon"]]
            return self.page(rows, args)
        if op == "read_attachment":
            a = self.attachments.get(args["id"])
            if not a or a["source"] != source or a.get("unavailable"):
                raise SourceError("unavailable_or_hidden", "Original attachment is unavailable")
            return [a], None, {"returned_count": 1}
        raise SourceError("unsupported", op)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
