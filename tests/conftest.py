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
def tmc_lcls_twincat_pmps_tmc():
    """
    .tmc file containing pinned global variables
    """
    path = PROJ_ROOT / "lcls-twincat-pmps/lcls-twincat-pmps/Library/Library.tmc"
    return path

@pytest.fixture(params=list(str(fn) for fn in TEST_PATH.glob('**/*.tsproj')))
def project_filename(request):
    return request.param


@pytest.fixture(scope='function')
def project(project_filename):
    return parser.parse(project_filename)


def lint_record(dbd_file, record):
    assert record.valid
    linted = linter.lint_db(dbd=dbd_file, db=record.render())
    assert not len(linted.errors)
