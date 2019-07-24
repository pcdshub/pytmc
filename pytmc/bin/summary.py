"""
"pytmc-summary" is a command line utility for inspecting TwinCAT3
.tsproj projects.
"""

import argparse
import ast
import pathlib
import sys

from .. import parser
from . import util


DESCRIPTION = __doc__


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    argparser.description = DESCRIPTION
    argparser.formatter_class = argparse.RawTextHelpFormatter

    argparser.add_argument(
        'tsproj_project', type=str,
        help='Path to .tsproj project'
    )

    argparser.add_argument(
        '--all', '-a', dest='show_all',
        action='store_true',
        help='All possible information'
    )

    argparser.add_argument(
        '--outline', dest='show_outline',
        action='store_true',
        help='Outline XML'
    )

    argparser.add_argument(
        '--boxes', '-b', dest='show_boxes',
        action='store_true',
        help='Show boxes'
    )

    argparser.add_argument(
        '--code', '-c', dest='show_code',
        action='store_true',
        help='Show code'
    )

    argparser.add_argument(
        '--plcs', '-p', dest='show_plcs',
        action='store_true',
        help='Show plcs'
    )

    argparser.add_argument(
        '--nc', '-n', dest='show_nc',
        action='store_true',
        help='Show NC axes'
    )

    argparser.add_argument(
        '--symbols', '-s', dest='show_symbols',
        action='store_true',
        help='Show symbols'
    )

    argparser.add_argument(
        '--links', '-l', dest='show_links',
        action='store_true',
        help='Show links'
    )

    argparser.add_argument(
        '--markdown', dest='use_markdown',
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


def main(tsproj_project, use_markdown=False, show_all=False,
         show_outline=False, show_boxes=False, show_code=False,
         show_plcs=False, show_nc=False, show_symbols=False, show_links=False,
         log_level=None, debug=False):

    proj_path = pathlib.Path(tsproj_project)
    if proj_path.suffix.lower() not in ('.tsproj', ):
        raise ValueError('Expected a .tsproj file')

    project = parser.parse(proj_path)

    def heading(text):
        print(text)
        print('=' * len(text))
        print()

    def sub_heading(text):
        print(text)
        print('-' * len(text))
        print()

    def sub_sub_heading(text, level=3):
        if use_markdown:
            print('#' * level, text)
        else:
            print(' ' * level, '-', text)
        print()

    def text_block(text, indent=4, language='vhdl'):
        if use_markdown:
            print(f'```{language}')
            print(text)
            print(f'```')
        else:
            for line in text.splitlines():
                print(' ' * indent, line)
        print()

    if show_plcs or show_all:
        for i, plc in enumerate(project.plcs, 1):
            heading(f'PLC Project ({i}): {plc.project_path.stem}')
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

            if show_code:
                for fn, source in plc.source.items():
                    sub_heading(f'{fn} ({source.tag})')
                    for decl_or_impl in source.find((parser.ST,
                                                     parser.Declaration,
                                                     parser.Implementation)):
                        if not decl_or_impl.text.strip():
                            continue

                        parent = decl_or_impl.parent
                        path_to_source = []
                        while parent is not source:
                            if parent.name is not None:
                                path_to_source.insert(0, parent.name)
                            parent = parent.parent
                        sub_sub_heading(f'{".".join(path_to_source)}: '
                                        f'{decl_or_impl.tag}')
                        text_block(decl_or_impl.text)
                    print()

    if show_symbols or show_all:
        sub_heading('Symbols')
        symbols = list(project.find(parser.Symbol))
        for symbol in symbols:
            info = symbol.info
            print('    {name} : {qualified_type_name} ({bit_offs} {bit_size})'
                  ''.format(**info))
        print()

    if show_boxes or show_all:
        sub_heading('Boxes')
        boxes = list(project.find(parser.Box))
        for box in boxes:
            print(f'    {box.attributes["Id"]}.) {box.name}')

    if show_nc or show_all:
        sub_heading('NC axes')
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

    if show_links or show_all:
        sub_heading('Links')
        links = list(project.find(parser.Link))
        for i, link in enumerate(links, 1):
            print(f'    {i}.) A {link.a}')
            print(f'          B {link.b}')
        print()

    if show_outline:
        outline(project)

    if debug:
        util.python_debug_session(
            namespace=locals(),
            message=('The top-level project is accessible as `project`, and '
                     'TWINCAT_TYPES are in the IPython namespace as well.'
                     )
        )

    return project
