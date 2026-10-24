"""Defence in depth for the bundled CLI demo, not an OS security sandbox."""
import os
import sys
from pathlib import Path


def install(root):
    root = root.resolve()
    workspace = root.parent
    inputs = set()

    def audit(event, args):
        if event in {"socket.connect", "socket.bind", "socket.getaddrinfo", "subprocess.Popen", "os.system"}:
            raise PermissionError("The synthetic research run cannot use network or subprocesses")
        if event not in {"open", "sqlite3.connect"} or not isinstance(args[0], (str, bytes, os.PathLike)):
            return
        if str(args[0]) == ":memory:":
            return
        path = Path(os.fsdecode(args[0])).resolve()
        if path.is_relative_to(workspace) and not path.is_relative_to(root):
            raise PermissionError("Private workspace files are outside the demo boundary")
        runtime_paths = [Path(sys.base_prefix).resolve(), Path(sys.prefix).resolve()]
        if not path.is_relative_to(root) and not any(path.is_relative_to(p) for p in runtime_paths):
            raise PermissionError("File is outside the demo and Python runtime")
        if path.is_relative_to(root / "fixtures"):
            if path.name.endswith(".gold.json"):
                raise PermissionError("The researcher cannot read evaluator answer keys")
            if path.suffix == ".json":
                inputs.add(path.relative_to(root).as_posix())

    sys.addaudithook(audit)
    return inputs
