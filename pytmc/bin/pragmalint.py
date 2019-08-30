"""
"pytmc pragmalint" is a command line utility for linting PyTMC pragmas in a
given TwinCAT project or source code file
"""

import argparse
import logging
import pathlib
import re
import sys
import textwrap

from .. import parser
from . import util
from .db import LinterError


DESCRIPTION = __doc__
logger = logging.getLogger(__name__)

PRAGMA_START_RE = re.compile('{attribute')
PRAGMA_RE = re.compile(
    r"^{\s*attribute[ \t]+'pytmc'[ \t]*:=[ \t]*'([\s\S]*)'}$",
    re.MULTILINE
)


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    argparser.description = DESCRIPTION
    argparser.formatter_class = argparse.RawTextHelpFormatter

    argparser.add_argument(
        'filename', type=str,
        help='Path to .tsproj project or source code file'
    )

    argparser.add_argument(
        '--markdown', dest='use_markdown',
        action='store_true',
        help='Make output more markdown-friendly, for easier sharing'
    )

    argparser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show all pragmas, including good ones'
    )

    return argparser


def match_single_pragma(code):
    curly_count = 0
    for i, char in enumerate(code):
        if char == '{':
            curly_count += 1
        elif char == '}':
            curly_count -= 1
            if i > 0 and curly_count == 0:
                return code[:i + 1]


def find_pragmas(code):
    for match in PRAGMA_START_RE.finditer(code):
        yield match.start(0), match_single_pragma(code[match.start(0):])


def lint_pragma(pragma):
    if 'pytmc' not in pragma:
        return

    pragma = pragma.strip()
    match = PRAGMA_RE.match(pragma)
    if not match:
        raise LinterError()
    return match


def _build_map_of_offset_to_line_number(source):
    start_index = 0
    index_to_line_number = {}
    # A slow and bad algorithm, but only to be used in parsing declarations
    # which are rather small
    for line_number, line in enumerate(source.splitlines(), 1):
        for index in range(start_index, start_index + len(line) + 1):
            index_to_line_number[index] = line_number
        start_index += len(line) + 1
    return index_to_line_number


def lint_source(filename, source, verbose=False):
    heading_shown = False

    for decl in source.find(parser.Declaration):
        if not decl.text.strip():
            continue

        offset_to_line_number = _build_map_of_offset_to_line_number(decl.text)

        parent = decl.parent
        path_to_source = []
        while parent is not source:
            if parent.name is not None:
                path_to_source.insert(0, parent.name)
            parent = parent.parent

        pragmas = list(find_pragmas(decl.text))
        if not pragmas:
            continue

        if verbose:
            if not heading_shown:
                print()
                util.sub_heading(f'{filename} ({source.tag})')
                heading_shown = True

            util.sub_sub_heading(
                f'{".".join(path_to_source)}: {decl.tag} - '
                f'{len(pragmas)} pragmas'
            )

        for offset, pragma in pragmas:
            try:
                lint_pragma(pragma)
            except LinterError as ex:
                ex.tag = source.tag
                ex.filename = filename
                ex.pragma = pragma
                ex.line_number = offset_to_line_number[offset]
                yield pragma, ex
            else:
                yield pragma, None


def main(filename, use_markdown=False, verbose=False):
    proj_path = pathlib.Path(filename)
    # if proj_path.suffix.lower() not in ('.tsproj', ):
    #     raise ValueError('Expected a .tsproj file')

    project = parser.parse(proj_path)
    pragma_count = 0
    linter_errors = 0

    if hasattr(project, 'plcs'):
        for i, plc in enumerate(project.plcs, 1):
            util.heading(f'PLC Project ({i}): {plc.project_path.stem}')
            for fn, source in plc.source.items():
                for pragma, ex in lint_source(fn, source, verbose=verbose):
                    pragma_count += 1
                    if ex is not None:
                        linter_errors += 1
                        logger.error('Linter error: %s\n%s:line %s: %s',
                                     ex, fn, ex.line_number,
                                     textwrap.indent(ex.pragma, '    '))
    else:
        source = project
        for pragma, ex in lint_source(filename, source, verbose=verbose):
            pragma_count += 1
            if ex is not None:
                linter_errors += 1
                logger.error('Linter error: %s\n%s:line %s: %s',
                             ex, filename, ex.line_number,
                             textwrap.indent(ex.pragma, '    '))

    logger.info('Total pragmas found: %d Total linter errors: %d',
                pragma_count, linter_errors)

    if linter_errors > 0:
        sys.exit(1)
