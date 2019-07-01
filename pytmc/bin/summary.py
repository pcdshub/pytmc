"""
"pytmc-summary" is a command line utility for inspecting TwinCAT3
.tsproj projects.
"""

import argparse
import ast
import logging
import pathlib

from pytmc import parser


DESCRIPTION = __doc__


def build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser(
            description=DESCRIPTION,
            formatter_class=argparse.RawTextHelpFormatter
        )

    parser.add_argument(
        'tsproj_project', type=str,
        help='Path to .tsproj project'
    )

    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='All possible information'
    )

    parser.add_argument(
        '--plcs', '-p',
        action='store_true',
        help='Show plcs'
    )

    parser.add_argument(
        '--nc', '-n',
        action='store_true',
        help='Show NC axes'
    )

    parser.add_argument(
        '--symbols', '-s',
        action='store_true',
        help='Show symbols'
    )

    parser.add_argument(
        '--links', '-l',
        action='store_true',
        help='Show links'
    )

    parser.add_argument(
        '--log',
        default='INFO',
        type=str,
        help='Python logging level (e.g. DEBUG, INFO, WARNING)'
    )

    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Access'
    )

    return parser


def summary(args):
    logger = logging.getLogger('pytmc')
    logger.setLevel(args.log)
    logging.basicConfig()

    proj_path = pathlib.Path(args.tsproj_project)
    project = parser.parse(proj_path)

    if args.plcs or args.all:
        for i, plc in enumerate(project.plcs, 1):
            print(f'--- PLC Project ({i}): {plc.project_path.stem}')
            print(f'    Project path: {plc.project_path}')
            print(f'    TMC path:     {plc.tmc_path}')
            print(f'')
            proj_info = [('Source files', plc.source_filenames),
                         ('POUs', plc.pou_by_name),
                         ('GVLs', plc.gvl_by_name),
                         ]

            for category, items in proj_info:
                if items:
                    print(f'    {category}:')
                    for j, text in enumerate(items, 1):
                        print(f'        {j}.) {text}')
                    print()

    if args.symbols or args.all:
        print('--- Symbols:')
        for symbol in project.find(parser.Symbol):
            print(f'    {symbol.info}')
        print()

    if args.nc or args.all:
        print('--- NC axes:')
        for nc in project.find(parser.NC):
            for axis_id, axis in sorted(nc.axis_by_id.items()):
                print(f'    {axis_id}.) {axis.short_name!r}:')
                for category, info in axis.summarize():
                    try:
                        info = ast.literal_eval(info)
                    except Exception:
                        ...
                    print(f'        {category} = {info!r}')
                print()

    if args.links or args.all:
        print('--- Links:')
        for i, link in enumerate(project.find(parser.Link), 1):
            print(f'    {i}.) A {link.a}')
            print(f'          B {link.b}')
        print()

    if args.debug:
        # for interactive debugging ease-of-use, import `parse`
        from tcparse import parse  # noqa
        try:
            from IPython import embed
        except ImportError:
            import pdb
            pdb.set_trace()
        else:
            embed()

    return project


def main(*, cmdline_args=None):
    parser = build_arg_parser()
    args = parser.parse_args(cmdline_args)
    return summary(args)


if __name__ == '__main__':
    main()
