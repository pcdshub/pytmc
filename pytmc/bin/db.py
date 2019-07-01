"""
"pytmc-db" is a command line utility for generating epics records files from
TwinCAT3 .tmc files. This program is designed to work in conjunction with ESS's
m-epics-twincat-ads driver.
"""

import argparse
import logging
import sys

import pytmc

logger = logging.getLogger(__name__)
description = __doc__


class LinterError(Exception):
    ...


def process(tmc_file_obj, *, dbd_file=None, allow_errors=False,
            show_error_context=True):
    '''
    Process a TmcFile, readying it for database generation

    Parameters
    ----------
    tmc_file_obj : TmcFile


    '''
    tmc_file_obj.create_chains()
    tmc_file_obj.isolate_chains()
    tmc_file_obj.create_packages()
    tmc_file_obj.configure_packages()

    def _show_context_from_line(rendered, from_line):
        lines = list(enumerate(rendered.splitlines()[:from_line + 1], 1))
        context = []
        for line_num, line in reversed(lines):
            context.append((line_num, line))
            if line.lstrip().startswith('record'):
                break

        context.reverse()
        for line_num, line in context:
            logger.error('   [db:%d] %s', line_num, line)
        return context

    if dbd_file is not None:
        results = tmc_file_obj.validate_with_dbd(dbd_file)
        for warning in results.warnings:
            logger.warning('[%s line %s] %s', warning['file'], warning['line'],
                           warning['message'])
        if show_error_context:
            rendered = tmc_file_obj.render()
        for error in results.errors:
            logger.error('[%s line %s] %s', error['file'], error['line'],
                         error['message'])
            if show_error_context:
                _show_context_from_line(rendered, error['line'])
        if not results.success and not allow_errors:
            logger.error('Linter errors - failed to create database. '
                         'To disable this behavior, use the flag '
                         '--allow-errors')
            raise LinterError('Failed to create database')

    return tmc_file_obj


def build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser(
            description=description,
            formatter_class=argparse.RawTextHelpFormatter
        )

    parser.add_argument(
        'tmc_file', metavar="INPUT", type=str,
        help='Path to interpreted .tmc file'
    )

    parser.add_argument(
        'record_file', metavar="OUTPUT", type=str,
        help='Path to output .db file'
    )

    parser.add_argument(
        '--dbd',
        '-d',
        default=None,
        type=str,
        help=('Specify an expanded .dbd file for validating fields '
              '(requires pyPDB)')
    )

    parser.add_argument(
        '--allow-errors',
        '-i',
        action='store_true',
        default=False,
        help='Generate the .db file even if linter issues are found'
    )

    parser.add_argument(
        '--no-error-context',
        action='store_true',
        default=False,
        help='Do not show db file context around errors'
    )

    parser.add_argument(
        '--log',
        '-l',
        metavar="LOG_LEVEL",
        default=30,  # WARN level messages
        type=int,
        help='Python numeric logging level (e.g. 10 for DEBUG, 20 for INFO'
    )

    return parser


def make_db(args):
    pytmc_logger = logging.getLogger('pytmc')
    pytmc_logger.setLevel(args.log)
    with open(args.tmc_file, 'r') as tmc_file:
        tmc_file_obj = pytmc.TmcFile(tmc_file)

    try:
        process(
            tmc_file_obj, dbd_file=args.dbd, allow_errors=args.allow_errors,
            show_error_context=not args.no_error_context,
        )
    except LinterError:
        sys.exit(1)

    db_string = tmc_file_obj.render()

    if args.record_file == '-':
        print(db_string)
    else:
        with open(args.record_file, 'wt') as record_file:
            record_file.write(db_string)


def main(*, cmdline_args=None):
    parser = build_arg_parser()
    return make_db(parser.parse_args(cmdline_args))


if __name__ == '__main__':
    main()
