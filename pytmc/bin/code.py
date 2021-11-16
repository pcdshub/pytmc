"""
"pytmc code" is a command line utility for extracting the source code of
TwinCAT3 .tsproj projects.
"""

import argparse
import pathlib

from .. import parser

DESCRIPTION = __doc__


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    argparser.description = DESCRIPTION
    argparser.formatter_class = argparse.RawTextHelpFormatter

    argparser.add_argument(
        'filename', type=str,
        help='Path to project (.tsproj) or source code filename'
    )

    return argparser


def dump_source_code(filename):
    'Return the source code for a given tsproj project'
    proj_path = pathlib.Path(filename)

    if proj_path.suffix.lower() not in ('.tsproj', ):
        parsed = parser.parse(proj_path)
        code_containers = [
            item for item in parsed.find(parser.TwincatItem, recurse=False)
            if hasattr(item, "get_source_code")
        ]
        source = "\n\n".join(
            code_container.get_source_code() or ""
            for code_container in code_containers
        )
        return parsed, source

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
                source_text = source.get_source_code() or ""
                if source_text.strip():
                    full_source.append(source_text)

    return project, "\n\n".join(full_source)


def main(filename):
    '''
    Output the source code of a project given its filename.
    '''

    results = {}
    path = pathlib.Path(filename)

    project, source_code = dump_source_code(path)
    print(source_code)
    results[project] = source_code
    return results
