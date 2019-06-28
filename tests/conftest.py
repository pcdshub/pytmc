import logging
import pathlib

import pytest

import pytmc
from pytmc import epics


logger = logging.getLogger(__name__)
TEST_PATH = pathlib.Path(__file__).parent
DBD_FILE = TEST_PATH / 'ads.dbd'

TMC_ROOT = TEST_PATH / 'tmc_files'
TMC_FILES = list(TMC_ROOT.glob('*.tmc'))
INVALID_TMC_FILES = list((TMC_ROOT / 'invalid').glob('*.tmc'))


@pytest.fixture(scope='module')
def dbd_file():
    return pytmc.epics.DbdFile(DBD_FILE)


@pytest.fixture(params=TMC_FILES,
                ids=[f.name for f in TMC_FILES])
def tmc_filename(request):
    return request.param


@pytest.fixture()
def leaf_bool_pragma_string():
    return """
                     pv: TEST:MAIN:NEW_VAR_OUT
                     type: bo
                     field: ZNAM	SINGLE
                     field: ONAM	MULTI
                     field:   SCAN	1 second
                     str: %d
                     io: o
                     init: True
                     pv: TEST:MAIN:NEW_VAR_IN
                     type:bi
                     field: ZNAM	SINGLE
                     field: ONAM	MULTI
                     field: SCAN	1 second
                     str: %d
                     io: i
    """


@pytest.fixture()
def leaf_bool_pragma_string_w_semicolon(leaf_bool_pragma_string):
    return leaf_bool_pragma_string + """
                     ensure: that ; semicolons: work;
    """


@pytest.fixture()
def leaf_bool_pragma_string_single_line():
    return """pv:pv_name"""


@pytest.fixture()
def light_leaf_bool_pragma_string():
    return """
                     pv: TEST:MAIN:NEW_VAR_OUT
                     io: o
                     pv: TEST:MAIN:NEW_VAR_IN
                     io: i
                     pv: TEST:MAIN:NEW_VAR_IO
                     io: io
                     pv: TEST:MAIN:NEW_VAR_SIMPLE
    """


@pytest.fixture(scope='function')
def branch_bool_pragma_string():
    return """
            pv: FIRST
            pv: SECOND
    """


@pytest.fixture(scope='function')
def branch_bool_pragma_string_empty(branch_bool_pragma_string):
    return branch_bool_pragma_string + """
            pv:
            pv:"""



@pytest.fixture(scope='function')
def branch_connection_pragma_string():
    return """
            pv: MIDDLE
            aux: nothing
    """


@pytest.fixture(scope='function')
def empty_pv_pragma_string():
    return """
            pv:
    """


@pytest.fixture(scope='function')
def branch_skip_pragma_string():
    return """
            skip:
    """


def lint_record(dbd_file, record):
    assert record.valid
    linted = epics.lint_db(dbd=dbd_file, db=record.render())
    assert not len(linted.errors)
