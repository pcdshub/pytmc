"""
"pytmc" is a command line utility for generating epics records files from
TwinCAT3 .tmc files. This program is designed to work in conjunction with
ESSS' m-epics-twincat-ads driver.
"""

import logging
import argparse

import pytmc


logger = logging.getLogger(__name__)
description = __doc__


def make_db_text(tmc_file_obj):
    '''
    Create an EPICS database from a TmcFile

    Parameters
    ----------
    tmc_file_obj : TmcFile

    Returns
    -------
    dbtext : str
        The rendered database text
    '''
    tmc_file_obj.create_chains()
    tmc_file_obj.isolate_chains()
    tmc_file_obj.create_packages()
    tmc_file_obj.configure_packages()
    return tmc_file_obj.render()



def main():
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
        '--log',
        '-l',
        metavar="LOG_LEVEL",
        default=30,  # WARN level messages
        type=int,
        help='Python numeric logging level (e.g. 10 for DEBUG, 20 for INFO'
    )

    args = parser.parse_args()
    pytmc_logger = logging.getLogger('pytmc')
    pytmc_logger.setLevel(args.log)
    with open(args.tmc_file, 'r') as tmc_file:
        tmc_file_obj = pytmc.TmcFile(tmc_file)

    db_string = make_db_text(tmc_file_obj)

    with open(args.record_file, 'wt') as record_file:
        record_file.write(db_string)


if __name__ == '__main__':
    main()
