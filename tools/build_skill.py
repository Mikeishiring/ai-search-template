"""Build the standalone skill from an explicit, reproducible file set."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path("skills/career-context-sheet")
MEMBERS = (
    "SKILL.md",
    "agents/openai.yaml",
    "assets/sheet.html",
    "assets/interview.html",
    "assets/resume.html",
    "assets/notebook.html",
    "references/adaptation-and-discovery.md",
    "references/deepening-and-story.md",
    "references/format.md",
    "references/interview-prep.md",
    "references/local-archive.md",
    "references/resume.md",
    "references/notebook.md",
    "references/source-research.md",
    "scripts/render_context.py",
    "scripts/render_interview.py",
    "scripts/render_resume.py",
    "scripts/render_notebook.py",
    "scripts/archive_context.py",
)
PREFIX = "career-context-sheet"


def bundle_bytes(root):
    """Read only the named resources; unlisted files never enter the bundle."""
    entries = {name: root / SKILL / name for name in MEMBERS}
    entries["LICENSE"] = root / "LICENSE"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(entries.items()):
            relative = path.relative_to(root)
            current = root
            for part in relative.parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError(f"Bundle inputs must not be symbolic links: {relative}")
            if not path.is_file():
                raise ValueError(f"Missing bundle input: {relative}")
            # The selected inputs are text. Normalize checkout line endings so
            # Windows and Unix checkouts produce the same bytes.
            content = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
            entry = zipfile.ZipInfo(f"{PREFIX}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buffer.getvalue()


def build(output, force=False):
    requested = Path(output).expanduser().absolute()
    if requested.is_symlink():
        raise ValueError("The output must not be a symbolic link.")
    destination = requested.resolve()
    if destination.is_relative_to(ROOT.resolve()):
        raise ValueError("Save the bundle outside the checkout.")
    if destination.suffix.lower() != ".zip":
        raise ValueError("Choose an output ending in .zip.")
    if not destination.parent.is_dir():
        raise ValueError("Create the output folder first.")
    if destination.exists() and not force:
        raise ValueError("Output already exists; use --force to replace it.")
    content = bundle_bytes(ROOT)
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".career-skill-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        if force:
            os.replace(temporary, destination)
        else:
            # A concurrent build cannot replace an output created after our check.
            if os.name == 'nt':
                os.rename(temporary, destination)
            else:
                os.link(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": str(destination), "files": len(MEMBERS) + 1,
            "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--force", action="store_true", help="Replace an existing bundle")
    args = parser.parse_args(argv)
    try:
        result = build(args.output, args.force)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Could not build the skill: {error}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
