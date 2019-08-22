"""
"pytmc-db" is a command line utility for generating epics records files from
TwinCAT3 .tmc files. This program is designed to work in conjunction with ESS's
m-epics-twincat-ads driver.
"""

import argparse
import logging
import sys

from collections import defaultdict

from .. import linter, parser
from ..pragmas import find_pytmc_symbols, record_packages_from_symbol


logger = logging.getLogger(__name__)
DESCRIPTION = __doc__


class LinterError(Exception):
    ...


def validate_with_dbd(packages, dbd_file, remove_invalid_fields=True,
                      **linter_options):
    '''
    Validate all to-be-generated record fields

    Parameters
    ----------
    packages : list
        List of RecordPackage
    dbd_file : str or DbdFile
        The dbd file with which to validate
    remove_invalid_fields : bool, optional
        Remove fields marked by the linter as invalid
    **linter_options : dict
        Options to pass to the linter

    Returns
    -------
    pytmc.linter.LinterResults
        Results from the linting process

    Raises
    ------
    DBSyntaxError
        If db/dbd processing fails

    See also
    --------
    pytmc.linter.lint_db
    '''
    db_text = '\n\n'.join(record.render() for record in packages)
    results = linter.lint_db(dbd=dbd_file, db=db_text, **linter_options)
    if remove_invalid_fields:
        all_invalid_fields = [
            error['format_args']
            for error in results.errors
            if error['name'] == 'bad-field'
            and len(error['format_args']) == 2
        ]
        invalid_fields_by_record = defaultdict(set)
        for record_type, field_name in all_invalid_fields:
            invalid_fields_by_record[record_type].add(field_name)

        for pack in packages:
            for record in getattr(pack, 'records', []):
                for field in invalid_fields_by_record.get(
                        record.record_type, []):
                    pack.cfg.remove_config_field(field)
    return results, db_text


def process(tmc, *, dbd_file=None, allow_errors=False,
            show_error_context=True):
    '''
    Process a TMC

    Parameters
    ----------
    tmc : TcModuleClass

    Returns
    -------
    records : list
        List of RecordPackage
    '''
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

    records = [record
               for symbol in find_pytmc_symbols(tmc)
               for record in record_packages_from_symbol(symbol)
               ]

    record_names = [record.pvname for record in records]
    if len(record_names) != len(set(record_names)):
        dupes = {name: record_names.count(name)
                 for name in record_names
                 if record_names.count(name) > 1
                 }
        message = '\n'.join(['Duplicate records encountered:'] +
                            [f'    {dupe} ({count})'
                             for dupe, count in sorted(dupes.items())])
        if not allow_errors:
            raise LinterError(message)
        logger.error(message)

    if dbd_file is not None:
        results, rendered = validate_with_dbd(records, dbd_file)
        for warning in results.warnings:
            logger.warning('[%s line %s] %s', warning['file'], warning['line'],
                           warning['message'])
        for error in results.errors:
            logger.error('[%s line %s] %s', error['file'], error['line'],
                         error['message'])
            if "Can't change record" in error['message']:
                logger.error('[%s line %s] One or more pragmas result in the '
                             'same generated PV name.  This must be fixed.',
                             error['file'], error['line'])

            if show_error_context:
                _show_context_from_line(rendered, error['line'])
        if not results.success and not allow_errors:
            raise LinterError('Failed to create database')

    return records


def build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    parser.description = DESCRIPTION
    parser.formatter_class = argparse.RawTextHelpFormatter

    parser.add_argument(
        'tmc_file', metavar="INPUT", type=str,
        help='Path to interpreted .tmc file'
    )

    parser.add_argument(
        'record_file', metavar="OUTPUT", type=str,
        nargs='?',
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

    return parser


def main(tmc_file, record_file=None, *, dbd=None, allow_errors=False,
         no_error_context=False):
    tmc = parser.parse(tmc_file)

    try:
        records = process(
            tmc, dbd_file=dbd, allow_errors=allow_errors,
            show_error_context=not no_error_context,
        )
    except LinterError:
        logger.exception(
            'Linter errors - failed to create database. To create the database'
            ' ignoring these errors, use the flag `--allow-errors`')
        sys.exit(1)

    db_string = '\n\n'.join(record.render() for record in records)

    if not record_file:
        print(db_string)
    else:
        with open(record_file, 'wt') as record_file:
            record_file.write(db_string)
