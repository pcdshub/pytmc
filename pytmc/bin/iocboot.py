"""
"pytmc iocboot" is a command line utility for bootstrapping new EPICS IOCs
based on TwinCAT3 .tsproj projects.
"""

import argparse
import getpass
import logging
import os
import pathlib

import jinja2

from . import db, util
from .. import pragmas

from ..parser import parse, Symbol, separate_by_classname


DESCRIPTION = __doc__
logger = logging.getLogger(__name__)


def build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    parser.description = DESCRIPTION
    parser.formatter_class = argparse.RawTextHelpFormatter

    parser.add_argument(
        'tsproj_project', type=str,
        help='Path to .tsproj project'
    )

    parser.add_argument(
        'ioc_template_path', type=str,
        help='Path to IOC template directory'
    )

    parser.add_argument(
        '--prefix', type=str, default='ioc-',
        help='IOC boot directory prefix [default: ioc-]'
    )

    parser.add_argument(
        '--makefile-name', type=str,
        default='Makefile.ioc',
        help='Jinja2 template for the IOC Makefile [default: Makefile.ioc]',
    )

    parser.add_argument(
        '--overwrite', action='store_true',
        help='Overwrite existing files'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry-run only - do not write files'
    )

    parser.add_argument(
        '--plcs',
        type=str,
        action='append',
        help='Specify one or more PLC names to generate'
    )

    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Post-stcmd, open an interactive Python session'
    )

    return parser


def main(tsproj_project, ioc_template_path, *, prefix='ioc-', debug=False,
         overwrite=False, makefile_name='Makefile.ioc', dry_run=False,
         plcs=None):
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(ioc_template_path),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    tsproj_project = pathlib.Path(tsproj_project).expanduser().absolute()
    project = parse(tsproj_project)

    solution_path = tsproj_project.parent.parent
    repo_path = solution_path.parent

    ioc_template_path = pathlib.Path(ioc_template_path)
    makefile_template_path = ioc_template_path / makefile_name
    if not makefile_template_path.exists():
        raise RuntimeError(f'File not found: {makefile_template_path}')

    template = jinja_env.get_template(makefile_name)

    for plc_name, plc in project.plcs_by_name.items():
        if plcs is not None and plc_name not in plcs:
            continue

        ioc_path = pathlib.Path(f'{prefix}{plc_name}').absolute()
        if not dry_run:
            os.makedirs(ioc_path, exist_ok=True)
        makefile_path = ioc_path / 'Makefile'

        plc_path = pathlib.Path(plc.filename).parent
        template_args = dict(
            project_name=tsproj_project.stem,
            plc_name=plc_name,
            tsproj_path=os.path.relpath(tsproj_project, ioc_path),
            project_path=os.path.relpath(tsproj_project.parent, ioc_path),
            template_path=ioc_template_path,
            solution_path=os.path.relpath(solution_path, ioc_path),
            plcproj=os.path.relpath(plc.filename, ioc_path),
            plc_path=os.path.relpath(plc_path, ioc_path),
            plc_ams_id=plc.ams_id,
            plc_ip=plc.target_ip,
            plc_ads_port=plc.port,
            user=getpass.getuser(),
        )

        stashed_exception = None
        try:
            rendered = template.render(**template_args)
        except Exception as ex:
            stashed_exception = ex
            rendered = None

        if not debug:
            if dry_run:
                print()
                print('---' * 30)
                print(makefile_path)
                print('---' * 30)

                if stashed_exception is not None:
                    print('Failed:', type(stashed_exception).__name__,
                          stashed_exception)
                    print()
                else:
                    if makefile_path.exists():
                        print('** OVERWRITING **'
                              if overwrite else '** FAIL: already exists **')
                        print()
                    print(rendered)
            else:
                if stashed_exception is not None:
                    raise stashed_exception

                if makefile_path.exists() and not overwrite:
                    raise RuntimeError('Must specify --overwrite to write over '
                                       'existing Makefiles')
                with open(makefile_path, 'wt') as f:
                    print(rendered, file=f)

        else:
            message = ['Variables: project, plc, template ']
            if stashed_exception is not None:
                message.append(f'Exception: {type(stashed_exception)} '
                               f'{stashed_exception}')

            util.python_debug_session(
                namespace=locals(),
                message='\n'.join(message)
            )
