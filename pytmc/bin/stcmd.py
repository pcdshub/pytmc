"""
"pytmc-stcmd" is a command line utility for generating ESS/ethercatmc-capable
EPICS startup st.cmd files directly from TwinCAT3 .tsproj projects.

Relies on the existence (and linking) of FB_MotionStage function blocks.
"""

import argparse
import getpass
import logging
import pathlib

import jinja2

from . import db, util
from .. import pragmas

from ..parser import parse, Symbol, separate_by_classname


DESCRIPTION = __doc__


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
        '--plc', type=str, default=None,
        help='PLC project name, if multiple exist'
    )

    parser.add_argument(
        '-p', '--prefix', type=str, default=None,
        help='PV prefix for the IOC'
    )

    parser.add_argument(
        '--binary', type=str, default='adsMotion',
        help='IOC application binary name'
    )

    parser.add_argument(
        '-n', '--name', type=str, default=None,
        help='IOC name (defaults to project name)'
    )

    parser.add_argument(
        '--only-motor', action='store_true',
        help=('Parse the project only for motor records, skipping other '
              'variables with pytmc pragmas')
    )

    parser.add_argument(
        '--db-path', type=str, default='.',
        help='Path for db files'
    )

    parser.add_argument(
        '--dbd', type=str, default=None,
        help='Path to the IOC dbd file'
    )

    parser.add_argument(
        '--delim', type=str, default=':',
        help='Preferred PV delimiter'
    )

    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Post-stcmd, open an interactive Python session'
    )

    parser.add_argument(
        '--template', type=str, default='stcmd_default.cmd',
        help='st.cmd Jinja2 template',
    )

    parser.add_argument(
        '--log',
        '-l',
        default='INFO',
        type=str,
        help='Python logging level (e.g. DEBUG, INFO, WARNING)'
    )

    return parser


def get_name(obj, args):
    'Returns: (motor_prefix, motor_name)'
    # First check if there is a pytmc pragma
    configs = pragmas.expand_configurations_from_chain([obj])
    if configs:
        config = pragmas.squash_configs(*configs)
        # PV name specified in the pragma - use it as-is
        return '', args.delim.join(config['pv'])

    if hasattr(obj, 'nc_axis'):
        nc_axis = obj.nc_axis
        # Fall back to using the NC axis name, replacing underscores/spaces
        # with the user-specified delimiter
        name = nc_axis.name.replace(' ', args.delim)
        return args.prefix + args.delim, name.replace('_', args.delim)
    return '', obj.name


def jinja_filters(args):
    'All jinja filters'
    # TODO all can be cached based on object, if necessary

    @jinja2.evalcontextfilter
    def epics_prefix(eval_ctx, obj):
        return get_name(obj, args)[0]

    @jinja2.evalcontextfilter
    def epics_suffix(eval_ctx, obj):
        return get_name(obj, args)[1]

    @jinja2.evalcontextfilter
    def pragma(eval_ctx, obj, key, default=''):
        configs = pragmas.expand_configurations_from_chain([obj])
        if configs:
            config = pragmas.squash_configs(*configs)
            return config.get(key, default)
        return default

    return {k: v for k, v in locals().items()
            if not k.startswith('_')}


def render(args):
    logger = logging.getLogger('pytmc')
    logger.setLevel(args.log)

    pytmc_logger = logging.getLogger('pytmc')
    pytmc_logger.setLevel(args.log)
    logging.basicConfig()

    jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader("pytmc", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    if not args.name:
        args.name = pathlib.Path(args.tsproj_project).stem

    if not args.prefix:
        args.prefix = args.name.upper()

    jinja_env.filters.update(**jinja_filters(args))

    template = jinja_env.get_template(args.template)

    project = parse(args.tsproj_project)
    symbols = separate_by_classname(project.find(Symbol))

    additional_db_files = []
    try:
        plc, = project.plcs
    except ValueError:
        by_name = project.plcs_by_name
        if not args.plc:
            raise RuntimeError(f'Only single PLC projects supported.  '
                               f'Use --plc and choose from {list(by_name)}')

        try:
            plc = project.plcs_by_name[args.plc]
        except KeyError:
            raise RuntimeError(f'PLC project {args.plc!r} not found. '
                               f'Projects: {list(by_name)}')

    if not args.only_motor:
        other_records = db.process(plc.tmc, dbd_file=args.dbd)
        if not other_records:
            logger.info('No additional records from pytmc found in %s',
                        plc.tmc.filename)
        else:
            db_filename = f'{plc.filename.stem}.db'
            db_path = pathlib.Path(args.db_path) / db_filename
            logger.info('Found %d additional records; writing to %s',
                        len(other_records), db_path)
            with open(db_path, 'wt') as db_file:
                db_file.write('\n\n'.join(rec.render()
                                          for rec in other_records))
            additional_db_files.append({'file': db_filename, 'macros': ''})

    template_args = dict(
        binary_name=args.binary,
        name=args.name,
        prefix=args.prefix,
        delim=args.delim,
        user=getpass.getuser(),

        motor_port='PLC_ADS',
        asyn_port='ASYN_PLC',
        plc_ams_id=plc.ams_id,
        plc_ip=plc.target_ip,
        plc_ads_port=plc.port,

        additional_db_files=additional_db_files,
        symbols=symbols,
    )

    stashed_exception = None
    try:
        rendered = template.render(**template_args)
    except Exception as ex:
        stashed_exception = ex
        rendered = None

    if not args.debug:
        if stashed_exception is not None:
            raise stashed_exception
    else:
        message = ['Variables: project, symbols, plc, template. ']
        if stashed_exception is not None:
            message.append(f'Exception: {type(stashed_exception)} '
                           f'{stashed_exception}')

        util.python_debug_session(
            namespace=locals(),
            message='\n'.join(message)
        )

    return project, symbols, rendered


def main(*, cmdline_args=None):
    parser = build_arg_parser()
    args = parser.parse_args(cmdline_args)
    _, _, template = render(args)
    print(template)


if __name__ == '__main__':
    main()
