"""Create a portable Career Context AI sheet. Python 3.11+, no packages or network."""
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
    for command in (demo, render):
        command.add_argument('output', type=Path, help='HTML destination outside this project')
        command.add_argument('--force', action='store_true', help='Replace an existing output file')
    args = parser.parse_args(argv)
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
        result = renderer().render(source, destination)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f'Could not create the sheet: {error}\n')
    print(f"Created {destination}\n{result['accounts']} work accounts; {result['sources']} selected sources.\nOpen the HTML in your browser. Nothing was uploaded.")


if __name__ == '__main__':
    main()
