"""
"pytmc template" is a command line utility to expand a template based on a
TwinCAT3 project (or XML-format file such as .TMC).

The template file is expected to be in Jinja template format.

The following dictionaries are available in the template context::

    solutions - {solution_filename: [project_fn: {...}, ...], ...}
    projects - {project_filename: {...}, ...}
    others - {filename: {...}, ...}

If installed and available, ``git_info`` will be available on each project.

The following helpers are available in the environment::

    config_to_pragma
    data_type_to_record_info
    determine_block_type
    element_to_class_name
    enumerate_types
    generate_records
    get_boxes
    get_data_type_by_reference
    get_data_types
    get_library_versions
    get_links
    get_linter_results
    get_motors
    get_nc
    get_plc_by_name
    get_pou_call_blocks
    get_symbols
    get_symbols_by_type
    list_types
    max
    min
    separate_by_classname

And the following filters::

    epics_prefix
    epics_suffix
    pragma
    title_fill

And the following variables::

    pytmc_version
    types
"""

import argparse
import functools
import logging
import os
import pathlib
import sys
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import jinja2

from .. import __version__ as pytmc_version
from .. import parser, pragmas
from ..record import RecordPackage
from . import pragmalint, stcmd, summary, util
from .db import generate_archive_settings
from .db import process as db_process

try:
    import git
except ImportError:
    git = None


DESCRIPTION = __doc__

logger = logging.getLogger(__name__)


def build_arg_parser(argparser=None):
    if argparser is None:
        argparser = argparse.ArgumentParser()

    argparser.description = DESCRIPTION
    argparser.formatter_class = argparse.RawTextHelpFormatter

    argparser.add_argument(
        'projects', type=str,
        help='Path to project or solution (.tsproj, .sln)',
        nargs='+',
    )

    argparser.add_argument(
        '-t', '--template',
        type=str,
        dest='templates',
        required=False,
        action="append",
        help=(
            f"Template filename with optional output filename. "
            f"In the form ``input_filename[{os.pathsep}output_filename]``."
            f"Defaults to '-' (standard input -> standard output)."
        ),
    )

    argparser.add_argument(
        "--macro",
        "-m",
        type=str,
        required=False,
        action="append",
        dest="macros",
        help="Define a macro for the template in the form MACRO=VALUE"
    )

    argparser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Post template generation, open an interactive Python session'
    )

    return argparser


def find_git_root(fn: pathlib.Path) -> Optional[pathlib.Path]:
    """Given a file, find the git repository root (if it exists)."""
    while fn:
        if (fn / ".git").exists():
            return fn
        fn = fn.parent


def _to_http_url(url: str) -> str:
    """Git over SSH -> GitHub https URL."""
    if url.startswith("git@github.com:"):
        _, repo_slug = url.split(':')
        return f"https://github.com/{repo_slug}"
    return url


def _to_doc_url(url: str) -> str:
    """Git over SSH -> GitHub https URL."""
    try:
        org, repo = _to_repo_slug(url).split('/')
        return f"https://{org}.github.io/{repo}"
    except Exception:
        return ""


def _to_tree_url(url: str, hash: str) -> str:
    """Get a github.com/org/repo/tree/master-style URL."""
    url = _to_http_url(url)
    if url.startswith("https://github.com"):
        return f"{url}/tree/{hash}"
    return url


def _to_repo_slug(url: str) -> str:
    """Get a org/repo from a full URL."""
    url = _to_http_url(url)
    github = "https://github.com/"
    if url.startswith(github):
        return url.split(github)[1]
    return url


def get_git_info(fn: pathlib.Path) -> Dict[str, Any]:
    """Get the git hash and other info for the repository that ``fn`` is in."""
    if git is None:
        raise RuntimeError("gitpython not installed")
    repo = git.Repo(find_git_root(fn))
    urls = [
        url
        for remote in repo.remotes
        for url in remote.urls
    ]
    repo_slugs = [_to_repo_slug(url) for url in urls]
    head_sha = repo.head.commit.hexsha
    if repo.git is not None:
        try:
            desc = repo.git.describe("--contains", head_sha)
        except git.GitCommandError:
            desc = repo.git.describe("--always", "--tags")
    else:
        desc = "unknown"

    return {
        "describe": desc or "unknown",
        "sha": head_sha,
        "repo_slug": repo_slugs[0] if repo_slugs else None,
        "repo_slugs": repo_slugs,
        "doc_urls": [_to_doc_url(url) for url in urls],
        "repo_urls": [_to_http_url(url) for url in urls],
        "tree_urls": [_to_tree_url(url, head_sha) for url in urls],
        "repo": repo,
    }


def project_to_dict(path: parser.AnyPath) -> Dict[str, Any]:
    """
    Create a user/template-facing dictionary of project information.

    In the case of a tsproj or solution, returns keys solutions and projects.
    All other formats (such as .tmc) fall under the "others" key, leaving it up
    to the template to classify.
    """
    path = pathlib.Path(path)
    suffix = path.suffix.lower()

    if suffix in {'.tsproj', '.sln'}:
        if suffix == '.sln':
            project_files = parser.projects_from_solution(path)
            solution = path
        else:
            project_files = [path]
            solution = None

        projects = {
            fn: parser.parse(fn)
            for fn in project_files
        }

        for fn, project in projects.items():
            try:
                project.git_info = get_git_info(fn)
            except Exception:
                project.git_info = {
                    "describe": "unknown",
                    "sha": "unknown",
                    "urls": [],
                    "links": [],
                    "repo_slug": "unknown",
                    "repo_slugs": [],
                    "doc_urls": [],
                    "repo_urls": [],
                    "tree_urls": [],
                    "repo": None,
                }

        solutions = {solution: projects} if solution is not None else {}

        return {
            'solutions': solutions,
            'projects': projects,
        }

    return {
        'others': {path: parser.parse(path)},
    }


def projects_to_dict(*paths) -> Dict[str, Dict[pathlib.Path, Any]]:
    """
    Create a user/template-facing dictionary of project information.

    Returns
    -------
    dict
        Information dictionary with keys::
            solutions - {solution_filename: [project_fn: {...}, ...], ...}
            projects - {project_filename: {...}, ...}
            others - {filename: {...}, ...}
    """
    result = {
        'solutions': {},
        'projects': {},
        'others': {},
    }
    for path in paths:
        for key, value in project_to_dict(path).items():
            result[key].update(value)
    return result


def get_jinja_filters(**user_config) -> Dict[str, callable]:
    """All jinja filters."""

    if 'delim' not in user_config:
        user_config['delim'] = ':'

    if 'prefix' not in user_config:
        user_config['prefix'] = 'PREFIX'

    def epics_prefix(obj: parser.TwincatItem) -> str:
        return stcmd.get_name(obj, user_config)[0]

    def epics_suffix(obj: parser.TwincatItem) -> str:
        return stcmd.get_name(obj, user_config)[1]

    def pragma(obj: parser.TwincatItem, key: str, default: str = "") -> str:
        item_and_config = pragmas.expand_configurations_from_chain([obj])
        if item_and_config:
            item_to_config = dict(item_and_config[0])
            config = pragmas.squash_configs(*item_to_config.values())
            return config.get(key, default)
        return default

    def title_fill(text: str, fill_char: str) -> str:
        return fill_char * len(text)

    return {
        key: value for key, value in locals().items()
        if not key.startswith('_')
    }


def get_symbols(plc) -> Generator[parser.Symbol, None, None]:
    """Get symbols for the PLC."""
    for symbol in plc.find(parser.Symbol):
        symbol.top_level_group = (
            symbol.name.split('.')[0] if symbol.name else 'Unknown')
        yield symbol


def get_symbols_by_type(plc: parser.Plc) -> Dict[str, List[parser.Symbol]]:
    """Get symbols for the PLC."""
    symbols = plc.find(parser.Symbol, recurse=False)
    return parser.separate_by_classname(symbols)


@functools.lru_cache()
def get_motors(plc: parser.Plc) -> List[parser.Symbol_DUT_MotionStage]:
    """Get pragma'd motor symbols for the PLC (non-pointer DUT_MotionStage)."""
    symbols = get_symbols_by_type(plc)
    return [
        stage
        for stage in symbols.get("Symbol_DUT_MotionStage", [])
        if not stage.is_pointer and pragmas.has_pragma(stage)
    ]


def get_plc_by_name(
    projects: Dict[parser.AnyPath, parser.TcSmProject],
    plc_name: str
) -> Tuple[Optional[parser.TcSmProject], Optional[parser.Plc]]:
    """
    Get a Plc instance by name.

    Parameters
    ----------
    projects : Dict[Path, parser.TcSmProject]
        The projects to search, as provided by pytmc template.
    plc_name : str
        The name of the PLC to search for.

    Returns
    -------
    project : parser.TcSmProject or None
        The project containing the PLC.
    plc : parser.Plc or None
        The PLC instance.
    """
    for _, project in projects.items():
        for plc in project.plcs:
            if plc.name == plc_name:
                return project, plc

    return None, None


@functools.lru_cache()
def get_plc_record_packages(
    plc: parser.Plc,
    dbd: Optional[str] = None,
) -> Tuple[List[RecordPackage], List[Exception]]:
    """
    Get EPICS record packages generated from a specific PLC.

    Returns
    -------
    records : list of RecordPackage
        Record packages generated.

    exceptions : list of Exception
        Any exceptions raised during the generation process.
    """
    if plc.tmc is None:
        return None, None

    try:
        packages, exceptions = db_process(
            plc.tmc, dbd_file=dbd, allow_errors=True,
            show_error_context=True,
        )
    except Exception:
        logger.exception(
            'Failed to create EPICS records'
        )
        return None, None

    return packages, exceptions


@functools.lru_cache()
def get_nc(project: parser.TopLevelProject) -> parser.NC:
    """Get the top-level NC settings for the project."""
    try:
        nc, = list(project.find(parser.NC, recurse=False))
        return nc
    except Exception:
        return None


@functools.lru_cache()
def get_data_types(project: parser.TwincatItem) -> List[dict]:
    """Get the data types container for the project."""
    data_types = getattr(project, 'DataTypes', [None])[0]
    if data_types is not None:
        return list(summary.enumerate_types(data_types))
    return []


@functools.lru_cache()
def get_boxes(project) -> List[parser.Box]:
    """Get boxes contained in the project."""
    return list(
        sorted(project.find(parser.Box),
               key=lambda box: int(box.attributes['Id']))
    )


def _get_box_to_children(boxes: List[parser.Box]) -> Dict[parser.Box, List[parser.Box]]:
    parent_to_children = {}

    for box in boxes:
        for child in box._children:
            if isinstance(child, parser.TcSmItem):
                child_box, = child.Box
            elif isinstance(child, parser.Box):
                child_box = child
            else:
                continue

            parent_to_children.setdefault(box, []).append(child_box)

    return parent_to_children


def _get_root_boxes(parent_to_children: Dict[parser.Box, List[parser.Box]]) -> List[parser.Box]:
    root = []
    for box in parent_to_children:
        for children in parent_to_children.values():
            if box in children:
                break
        else:
            root.append(box)
    return root


BoxHierarchy = Dict[parser.Box, "BoxHierarchy"]


def get_box_hierarchy(project) -> BoxHierarchy:
    """
    Get boxes contained in the project in a hierarchical fashion.

    This is in the form: ``{box: {child: grandchild: {}}}``.
    """

    def recurse_children(box: parser.Box) -> BoxHierarchy:
        return {
            child: recurse_children(child)
            for child in parent_to_children.get(box, [])
        }

    boxes = get_boxes(project)
    parent_to_children = _get_box_to_children(boxes)
    return {
        root: recurse_children(root)
        for root in _get_root_boxes(parent_to_children)
    }


def _clean_link(link: parser.Link):
    """Clean None from links for easier displaying."""
    link.a = tuple(value or '' for value in link.a)
    link.b = tuple(value or '' for value in link.b)
    return link


@functools.lru_cache()
def get_links(project: parser.TwincatItem) -> List[parser.Link]:
    """Get links contained in the project or PLC."""
    return list(_clean_link(link) for link in project.find(parser.Link))


def generate_records(
    plc: parser.Plc,
    path: Optional[parser.AnyPath] = None,
    dbd: Optional[parser.AnyPath] = None,
    allow_errors: bool = False,
    write_archive_file: bool = True,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Generate records from ``plc`` writing to ``path``.

    Optionally lint with ``dbd``.

    Parameters
    ----------
    plc : parser.Plc

    path : AnyPath, optional
        Defaults to {{plc.name}}.db

    dbd : parser.AnyPath, optional
        Lint the generated database file with the provided dbd.

    allow_errors : bool, optional
        Allow errors when generating the .db file.

    write_archive_file : bool, optional
        Write archive file to {{plc.name}}.archive

    Returns
    -------
    filenames : list of str
        Database filenames.
    records : Dict[str, RecordPackage]
        Records by name.
    """
    if plc.tmc is None:
        return [], {}

    packages, exceptions = get_plc_record_packages(plc, dbd=dbd)
    if exceptions and not allow_errors:
        logger.exception(
            'Linter errors - failed to create database. To create the database'
            ' ignoring these errors, set allow_errors=True'
        )
        sys.exit(1)

    db_string = "\n\n".join(package.render() or "" for package in packages)

    if path is None:
        path = f"{plc.name}.db"
        archive_path = f"{plc.name}.archive"
    else:
        archive_path = f"{path}.archive"

    with open(path, "wt") as fp:
        fp.write(db_string)

    if write_archive_file:
        with open(archive_path, "wt") as fp:
            fp.write('\n'.join(generate_archive_settings(packages)))

    by_pvname = {
        record.pvname: record
        for package in packages
        for record in package.records
    }
    return [str(path)], by_pvname


@functools.lru_cache()
def get_linter_results(plc: parser.Plc) -> Dict[str, Any]:
    """
    Lint the provided PLC code pragmas.

    Returns
    -------
    dict
        Includes "pragma_count", "pragma_errors", and "linter_results" keys.
    """
    pragma_count = 0
    linter_errors = 0
    results = []

    for fn, source in plc.source.items():
        for info in pragmalint.lint_source(fn, source):
            pragma_count += 1
            if info.exception is not None:
                linter_errors += 1
                results.append(info)

    return {
        'pragma_count': pragma_count,
        'pragma_errors': linter_errors,
        'linter_results': results,
    }


def config_to_pragma(
    config: dict,
    skip_desc: bool = True,
    skip_pv: bool = True
) -> Generator[Tuple[str, str], None, None]:
    """
    Convert a configuration dictionary into a single pragma string.

    Yields
    ------
    key: str
        Pragma key.

    value: str
        Pragma value.
    """
    if not config:
        return

    for key, value in config.items():
        if key == 'archive':
            seconds = value.get('seconds', 'unknown')
            method = value.get('method', 'unknown')
            fields = value.get('fields', {'VAL'})
            if seconds != 1 or method != 'scan':
                yield ('archive', f'{seconds}s {method}')
            if fields != {'VAL'}:
                yield ('archive_fields', ' '.join(fields))
        elif key == 'update':
            frequency = value.get('frequency', 1)
            method = value.get('method', 'unknown')
            if frequency != 1 or method != 'poll':
                yield (key, f'{frequency}hz {method}')
        elif key == 'field':
            for field, value in value.items():
                if field != 'DESC' or not skip_desc:
                    yield ('field', f'{field} {value}')
        elif key == 'pv':
            if not skip_pv:
                yield (key, ':'.join(value))
        else:
            yield (key, value)


@functools.lru_cache()
def get_library_versions(plc: parser.Plc) -> Dict[str, Dict[str, Any]]:
    """Get library version information for the given PLC."""
    def find_by_name(cls_name):
        try:
            cls = parser.TWINCAT_TYPES[cls_name]
        except KeyError:
            return []
        else:
            return list(plc.find(cls, recurse=False))

    versions = {}

    for category in ('PlaceholderReference', 'PlaceholderResolution',
                     'LibraryReference'):
        for obj in find_by_name(category):
            info = obj.get_resolution_info()
            info['category'] = category
            if info['name'] not in versions:
                versions[info['name']] = {}

            versions[info['name']][category] = info

    return versions


def render_template(
    template: str,
    context: dict,
    trim_blocks=True,
    lstrip_blocks=True,
    **env_kwargs
):
    """
    One-time-use jinja environment + template rendering helper.
    """
    env = jinja2.Environment(
        loader=jinja2.DictLoader({'template': template}),
        trim_blocks=trim_blocks,
        lstrip_blocks=lstrip_blocks,
        **env_kwargs,
    )

    env.filters.update(get_jinja_filters())
    return env.get_template('template').render(context)


helpers = [
    config_to_pragma,
    generate_records,
    get_boxes,
    get_box_hierarchy,
    get_data_types,
    get_library_versions,
    get_links,
    get_linter_results,
    get_motors,
    get_nc,
    get_plc_by_name,
    get_symbols,
    get_symbols_by_type,
    max,
    min,
    parser.determine_block_type,
    parser.element_to_class_name,
    parser.get_data_type_by_reference,
    parser.get_pou_call_blocks,
    parser.separate_by_classname,
    summary.data_type_to_record_info,
    summary.enumerate_types,
    summary.list_types,
]


def get_render_context() -> Dict[str, Any]:
    """Jinja template context dictionary - helper functions."""
    context = {func.__name__: func for func in helpers}
    context['types'] = parser.TWINCAT_TYPES
    context['pytmc_version'] = pytmc_version
    return context


def _split_macro(macro: str) -> Tuple[str, str]:
    """
    Split a macro of the form NAME=VALUE into ("NAME", "VALUE").

    Parameters
    ----------
    macro : str
        The raw macro string.

    Returns
    -------
    name : str
    value : str
    """
    parts = macro.split("=", 1)
    if len(parts) != 2:
        raise ValueError(f"Macro not in the format ``NAME=VALUE``: {macro!r}")
    return tuple(parts)


def main(
    projects: List[parser.AnyPath],
    templates: Optional[Union[List[str], str]] = None,
    macros: Union[List[str], Dict[str, str], None] = None,
    debug: bool = False,
) -> Dict[str, str]:
    """
    Render template(s) based on a TwinCAT3 project, or XML-format file such as
    TMC.

    Parameters
    ----------
    projects : list
        List of projects or TwinCAT project files (.sln, .tsproj, .tmc, etc.)

    templates : str or list of str, optional
        Template filename (default: standard input) to output filename
        in the form ``input_filename[{os.pathsep}output_filename]``
        Defaults to '-' (standard input -> standard output)

    debug : bool, optional
        Open a debug session after rendering with IPython.
    """

    macros = macros or {}
    if not isinstance(macros, dict):
        macros = dict(_split_macro(macro) for macro in macros)

    logger.debug("Macros: %s", macros)
    if not templates:
        templates = ["-"]
    if isinstance(templates, str):
        templates = [templates]

    all_rendered = {}
    for template in templates:
        input_filename, output_filename = template.split(os.pathsep, 1)
        if input_filename == "-":
            # Check if it's an interactive user to warn them what we're doing:
            is_tty = os.isatty(sys.stdin.fileno())
            if is_tty:
                logger.warning('Reading template from standard input...')
                logger.warning('Press ^D on a blank line when done.')

            template_text = sys.stdin.read()
            if is_tty:
                logger.warning('Read template from standard input (len=%d)',
                               len(template_text))
        else:
            with open(input_filename, "rt") as fp:
                template_text = fp.read()

        stashed_exception = None
        try:
            template_args = get_render_context()
            template_args.update(projects_to_dict(*projects))
            template_args.update(**macros)
            rendered = render_template(template_text, template_args)
        except Exception as ex:
            stashed_exception = ex
            rendered = None

        if not debug:
            if stashed_exception is not None:
                raise stashed_exception

            if output_filename:
                with open(output_filename, "wt") as fp:
                    print(rendered, file=fp)
            else:
                print(rendered)
        else:
            message = [
                'Variables: projects, template_text, rendered, template_args. '
            ]
            if stashed_exception is not None:
                message.append(f'Exception: {type(stashed_exception)} '
                               f'{stashed_exception}')

            util.python_debug_session(
                namespace=locals(),
                message='\n'.join(message)
            )
        all_rendered[input_filename] = rendered

    return all_rendered
