import logging
import pathlib

import pytest

import pytmc
from pytmc import linter, parser

logger = logging.getLogger(__name__)
TEST_PATH = pathlib.Path(__file__).parent
DBD_FILE = TEST_PATH / 'ads.dbd'

TMC_ROOT = TEST_PATH / 'tmc_files'
TMC_FILES = list(TMC_ROOT.glob('*.tmc'))
INVALID_TMC_FILES = list((TMC_ROOT / 'invalid').glob('*.tmc'))
PROJ_ROOT = TEST_PATH / 'projects'
TSPROJ_PROJECTS = list(str(fn) for fn in TEST_PATH.glob('**/*.tsproj'))
TEMPLATES = TEST_PATH / 'templates'


@pytest.fixture(scope='module')
def dbd_file():
    return pytmc.linter.DbdFile(DBD_FILE)


@pytest.fixture(params=TMC_FILES,
                ids=[f.name for f in TMC_FILES])
def tmc_filename(request):
    return request.param


@pytest.fixture(scope='module')
def tmc_xtes_sxr_plc():
    """
    generic .tmc file
    """
    return TMC_ROOT / "xtes_sxr_plc.tmc"


@pytest.fixture(scope='module')
def tmc_arbiter_plc():
    """
    generic .tmc file
    """
    return TMC_ROOT / "ArbiterPLC.tmc"


@pytest.fixture(scope='module')
def tmc_pmps_dev_arbiter():
    """
    .tmc file containing pinned global variables
    """
    path = PROJ_ROOT / "pmps-dev-arbiter/Arbiter/ArbiterPLC/ArbiterPLC.tmc"
    return path


@pytest.fixture(params=TSPROJ_PROJECTS)
def project_filename(request):
    return request.param


def _generate_project_and_plcs():
    for project_filename in TSPROJ_PROJECTS:
        project = parser.parse(project_filename)
        for plc_name in project.plcs_by_name:
            yield project_filename, plc_name


@pytest.fixture(
    params=[
        pytest.param((project_filename, plc_name),
                     id=f'{project_filename} {plc_name}')
        for project_filename, plc_name in _generate_project_and_plcs()
    ]
)
def project_and_plc(request):
    class Item:
        project = request.param[0]
        plc_name = request.param[1]
    return Item


@pytest.fixture(scope='function')
def project(project_filename):
    return parser.parse(project_filename)


def lint_record(dbd_file, record):
    assert record.valid
    linted = linter.lint_db(dbd=dbd_file, db=record.render())
    assert not len(linted.errors)
