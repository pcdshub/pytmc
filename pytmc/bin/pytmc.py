"""
`pytmc` is the top-level command for accessing various subcommands.

Try::

    $ pytmc db --help
    $ pytmc stcmd --help
    $ pytmc summary --help
    $ pytmc debug --help
"""

import argparse

from .summary import (build_arg_parser as build_summary_arg_parser,
                      summary as summary_main)
from .stcmd import (build_arg_parser as build_stcmd_arg_parser,
                    render as render_stcmd)
from .db import (build_arg_parser as build_db_arg_parser,
                 make_db as db_main)
from .xmltranslate import (build_arg_parser as build_translate_arg_parser,
                           translate as translate_main)
from .debug import (build_arg_parser as build_debug_arg_parser,
                    create_debug_window as debug_main)
from .types import (build_arg_parser as build_types_arg_parser,
                    create_types_window as types_main)

DESCRIPTION = __doc__


def stcmd_main(args):
    _, _, template = render_stcmd(args)
    print(template)


COMMANDS = {
    'stcmd': (build_stcmd_arg_parser, stcmd_main),
    'summary': (build_summary_arg_parser, summary_main),
    'db': (build_db_arg_parser, db_main),
    'debug': (build_debug_arg_parser, debug_main),
    'types': (build_types_arg_parser, types_main),
    'translate': (build_translate_arg_parser, translate_main),
}


def main():
    top_parser = argparse.ArgumentParser(
        prog='pytmc',
        description=DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter
    )

    top_parser.add_argument(
        '--log',
        '-l',
        default='INFO',
        type=str,
        help='Python logging level (e.g. DEBUG, INFO, WARNING)'
    )

    subparsers = top_parser.add_subparsers(help='Possible subcommands')
    for command_name, (build_func, main) in COMMANDS.items():
        sub = subparsers.add_parser(command_name)
        build_func(sub)
        sub.set_defaults(func=main)

    args = top_parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        top_parser.print_help()


if __name__ == '__main__':
    main()
