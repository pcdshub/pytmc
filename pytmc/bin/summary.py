"""
"pytmc-summary" is a command line utility for inspecting TwinCAT3
.tsproj projects.
"""

import argparse
import ast
import logging
import pathlib
import sys

from .. import parser
from . import util


DESCRIPTION = __doc__


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser(
            description=DESCRIPTION,
            formatter_class=argparse.RawTextHelpFormatter
        )

    argparser.add_argument(
        'tsproj_project', type=str,
        help='Path to .tsproj project'
    )

    argparser.add_argument(
        '--all', '-a',
        action='store_true',
        help='All possible information'
    )

    argparser.add_argument(
        '--outline',
        action='store_true',
        help='Outline XML'
    )

    argparser.add_argument(
        '--boxes', '-b',
        action='store_true',
        help='Show boxes'
    )

    argparser.add_argument(
        '--code', '-c',
        action='store_true',
        help='Show code'
    )

    argparser.add_argument(
        '--plcs', '-p',
        action='store_true',
        help='Show plcs'
    )

    argparser.add_argument(
        '--nc', '-n',
        action='store_true',
        help='Show NC axes'
    )

    argparser.add_argument(
        '--symbols', '-s',
        action='store_true',
        help='Show symbols'
    )

    argparser.add_argument(
        '--links', '-l',
        action='store_true',
        help='Show links'
    )

    argparser.add_argument(
        '--log',
        default='INFO',
        type=str,
        help='Python logging level (e.g. DEBUG, INFO, WARNING)'
    )

    argparser.add_argument(
        '--markdown',
        action='store_true',
        help='Make output more markdown-friendly, for easier sharing'
    )

    argparser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Post-summary, open an interactive Python session'
    )

    return argparser


def outline(item, *, depth=0, f=sys.stdout):
    indent = '  ' * depth
    num_children = len(item._children)
    has_container = 'C' if hasattr(item, 'container') else ' '
    flags = ''.join((has_container, ))
    name = item.name or ''
    print(f'{flags}{indent}{item.__class__.__name__} {name} '
          f'[{num_children}]', file=f)
    for child in item._children:
        outline(child, depth=depth + 1, f=f)


def summary(args):
    logger = logging.getLogger('pytmc')
    logger.setLevel(args.log)
    logging.basicConfig()

    proj_path = pathlib.Path(args.tsproj_project)
    if proj_path.suffix.lower() not in ('.tsproj', ):
        raise ValueError('Expected a .tsproj file')

    project = parser.parse(proj_path)

    def heading(text):
        print(text)
        print('=' * len(text))

    def sub_heading(text):
        print(text)
        print('-' * len(text))

    def sub_sub_heading(text, level=3):
        if args.markdown:
            print('#' * level, text)
        else:
            print(' ' * level, '-', text)
        print()

    def text_block(text, indent=4, language='vhdl'):
        if args.markdown:
            print(f'```{language}')
            print(text)
            print(f'```')
        else:
            for line in text.splitlines():
                print(' ' * indent, line)
        print()

    if args.plcs or args.all:
        for i, plc in enumerate(project.plcs, 1):
            heading(f'PLC Project ({i}): {plc.project_path.stem}')
            print(f'Project path: {plc.project_path}')
            print(f'TMC path:     {plc.tmc_path}')
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

            if args.code:
                for fn, source in plc.source.items():
                    sub_heading(f'{fn} ({source.tag})')
                    for decl_or_impl in source.find((parser.ST,
                                                     parser.Declaration,
                                                     parser.Implementation)):
                        parent = decl_or_impl.parent
                        path_to_source = []
                        while parent is not source:
                            if parent.name is not None:
                                path_to_source.insert(0, parent.name)
                            parent = parent.parent
                        sub_sub_heading(f'{".".join(path_to_source)}: {parent.tag} '
                                        f'{decl_or_impl.tag}')
                        text_block(decl_or_impl.text)
                    print()
                    print()

    if args.symbols or args.all:
        print('--- Symbols:')
        symbols = list(project.find(parser.Symbol))
        for symbol in symbols:
            info = symbol.info
            print('    {name} : {qualified_type_name} ({bit_offs} {bit_size})'
                  ''.format(**info))
        print()

    if args.boxes or args.all:
        print('--- Boxes:')
        boxes = list(project.find(parser.Box))
        for box in boxes:
            print(f'    {box.attributes["Id"]}.) {box.name}')

    if args.nc or args.all:
        print('--- NC axes:')
        ncs = list(project.find(parser.NC))
        for nc in ncs:
            for axis_id, axis in sorted(nc.axis_by_id.items()):
                print(f'    {axis_id}.) {axis.name!r}:')
                for category, info in axis.summarize():
                    try:
                        info = ast.literal_eval(info)
                    except Exception:
                        ...
                    print(f'        {category} = {info!r}')
                print()

    if args.links or args.all:
        print('--- Links:')
        links = list(project.find(parser.Link))
        for i, link in enumerate(links, 1):
            print(f'    {i}.) A {link.a}')
            print(f'          B {link.b}')
        print()

    if args.outline:
        outline(project)

    if args.debug:
        util.python_debug_session(
            namespace=locals(),
            message=('The top-level project is accessible as `project`, and '
                     'TWINCAT_TYPES are in the IPython namespace as well.'
                     )
        )

    return project


def main(*, cmdline_args=None):
    parser = build_arg_parser()
    args = parser.parse_args(cmdline_args)
    return summary(args)


if __name__ == '__main__':
    main()
