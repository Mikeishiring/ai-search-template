"""Create local Career Context AI sheets; optionally research selected sources."""
import argparse
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def renderer():
    spec = importlib.util.spec_from_file_location(
        'career_context_renderer', ROOT / 'skills/career-context-sheet/scripts/render_context.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='Create a sheet using the included fictional example')
    render = commands.add_parser('render', help='Build a sheet from your JSON or existing HTML')
    render.add_argument('input', type=Path, help='Selected career context, kept outside this project')
    research = commands.add_parser('research-demo', help='Use authenticated Codex to research only the fixed fictional sources and build a sheet')
    research.add_argument('output', type=Path)
    research.add_argument('--workspace', type=Path, help='Private research state outside this project')
    research.add_argument('--resume', action='store_true', help='Resume saved state; rebuild a sealed run without another model call')
    research.add_argument('--force', action='store_true')
    research_build = commands.add_parser('research-build', help='Build HTML from an existing checked research journal without a model call')
    research_build.add_argument('workspace', type=Path)
    research_build.add_argument('output', type=Path)
    research_build.add_argument('--force', action='store_true')
    setup = commands.add_parser('start', help='Choose work, exact sources, privacy and a local context folder')
    setup.add_argument('workspace', type=Path)
    setup.add_argument('--policy', type=Path, help='Use an explicit saved policy instead of interactive questions')
    local_import = commands.add_parser('local-import', help='Import only permitted locations from a selected normalized export')
    local_import.add_argument('workspace', type=Path)
    local_import.add_argument('file', type=Path)
    local_status = commands.add_parser('local-status', help='Show local captures and the research-depth checklist')
    local_status.add_argument('workspace', type=Path)
    local_serve = commands.add_parser('research-serve', help='Serve selected local context to an AI host only when the policy permits it')
    local_serve.add_argument('workspace', type=Path)
    extract = commands.add_parser('research-extract', help='Count pending sections, or extract bounded batches with authenticated Codex')
    extract.add_argument('workspace', type=Path)
    extract.add_argument('--max-batches', type=int, default=0, help='Explicit model-call limit (1–20); omitted means a local plan only')
    extract.add_argument('--timeout', type=int, default=300, help='Per-batch timeout in seconds (30–600)')
    for command in (demo, render):
        command.add_argument('output', type=Path, help='HTML destination outside this project')
        command.add_argument('--force', action='store_true', help='Replace an existing output file')
    args = parser.parse_args(argv)
    if args.command in {'start', 'local-import', 'local-status', 'research-serve', 'research-extract'}:
        import json
        import local_context
        try:
            if args.command == 'start':
                workspace = (local_context.initialize(args.workspace, local_context.read_json(args.policy), args.policy.resolve().parent)
                             if args.policy else local_context.wizard(args.workspace))
                print(f'Created local context in {workspace}\nOpen CAREER-CONTEXT.html. Nothing was uploaded.')
            elif args.command == 'local-import':
                print(json.dumps(local_context.import_export(args.workspace, args.file)))
            elif args.command == 'local-status':
                print(json.dumps(local_context.status(args.workspace), indent=2))
            elif args.command == 'research-extract':
                import extraction_batches
                result = (extraction_batches.run(args.workspace, args.max_batches, args.timeout)
                          if args.max_batches else extraction_batches.plan(args.workspace))
                print(json.dumps(result, indent=2))
            else:
                from research_sheet_server import serve
                serve(args.workspace)
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
            parser.exit(2, f'Could not use local context: {error}\n')
        return
    if args.command in {'research-demo', 'research-build'}:
        try:
            if args.command == 'research-demo':
                from tools.run_research_demo import run
                result = run(args.output, args.workspace, args.resume, args.force)
            else:
                from research_sheet import build
                result = build(args.workspace, args.output, args.force)
        except (ValueError, KeyError, TypeError, OSError) as error:
            parser.exit(2, f'Could not build the research sheet: {error}\n')
        print(f"Created {result['path']}\nChecked research compiled into {result['accounts']} work accounts. Draft for review.")
        return
    source = ROOT / 'examples/career-context.json' if args.command == 'demo' else args.input.expanduser().resolve()
    destination = args.output.expanduser().resolve()
    try:
        if destination.is_relative_to(ROOT):
            raise ValueError('Choose an output outside the public project, such as ../my-context/career-context.html.')
        if args.command == 'render' and source.is_relative_to(ROOT):
            raise ValueError('Keep personal inputs outside the public project. Use demo to try the included example.')
        if destination.suffix.lower() not in {'.html', '.htm'}:
            raise ValueError('Choose an output ending in .html or .htm.')
        if destination.exists() and not args.force:
            raise ValueError('Output already exists. Choose another path or add --force to replace it.')
        if not destination.parent.is_dir():
            raise ValueError('The output folder does not exist. Create it first, outside this project.')
        result = renderer().render(source, destination, overwrite=args.force)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f'Could not create the sheet: {error}\n')
    print(f"Created {destination}\n{result['accounts']} work accounts; {result['sources']} selected sources.\nOpen the HTML in your browser. Nothing was uploaded.")


if __name__ == '__main__':
    main()
