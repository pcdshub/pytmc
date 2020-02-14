"""
"pytmc code" is a command line utility for extracting the source code of
TwinCAT3 .tsproj projects.
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
        'filename', type=str,
        help='Path to project (.tsproj)'
    )

    return argparser


def dump_source_code(tsproj_project):
    'Return the source code for a given tsproj project'
    proj_path = pathlib.Path(tsproj_project)

    if proj_path.suffix.lower() not in ('.tsproj', ):
        raise ValueError('Expected a .tsproj file')

    project = parser.parse(proj_path)
    full_source = []

    for plc in project.plcs:
        source_items = (
            list(plc.dut_by_name.items()) +
            list(plc.gvl_by_name.items()) +
            list(plc.pou_by_name.items())
        )
        for name, source in source_items:
            if hasattr(source, 'get_source_code'):
                source_text = source.get_source_code() or ''
                if source_text.strip():
                    full_source.append(source_text)

    return project, '\n\n'.join(full_source)


def main(filename):
    '''
    Output the source code of a project given its filename.
    '''

    path = pathlib.Path(filename)
    if path.suffix.lower() in ('.tsproj', ):
        project_fns = [path]
    else:
        raise ValueError(f'Expected a tsproj, but got: {path.suffix}')

    projects = {}
    for fn in project_fns:
        project, source_code = dump_source_code(fn)
        print(source_code)
        projects[project] = source_code

    return projects
