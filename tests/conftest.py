import contextlib
import pytest
import logging
import pathlib
import xml.etree.ElementTree as ET
import os

import pytmc
from pytmc import TmcFile, epics
from pytmc.xml_collector import TmcChain
from pytmc.xml_obj import BaseElement, Configuration


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


@pytest.fixture(scope='function')
def tmc_root(tmc_filename):
    tree = ET.parse(tmc_filename)
    return tree.getroot()


@pytest.fixture(scope='function')
def generic_tmc_path():
    return TMC_ROOT / "invalid" / "generic_w_pragmas180426.tmc"


@pytest.fixture(scope='function')
def generic_tmc_root(generic_tmc_path):
    tree = ET.parse(generic_tmc_path)
    return tree.getroot()


@pytest.fixture(scope='function')
def string_tmc_path():
    return TMC_ROOT / "invalid" / "generic_w_pragmas180921.tmc"


@pytest.fixture(scope='function')
def string_tmc_root(string_tmc_path):
    tree = ET.parse(string_tmc_path)
    return tree.getroot()


@pytest.fixture(scope='function')
def safe_record_factory():
    rec = SingleRecordData(
        pv="GDET:FEE1:241:ENRC",
        rec_type="ai",
        fields=dict([
            ("DTYP", "asynInt32"),
            ("INP", None),
            ("ZNAM", "Z"),
        ]),
        comment="sample comment",
    )
    return rec


@pytest.fixture(scope='function')
def generic_file():
    return TmcFile(TMC_ROOT / "generic.tmc")


@pytest.fixture(scope='function')
def generic_explorer(generic_file):
    return TmcExplorer(generic_file)


@pytest.fixture(scope='function')
def leaf_bool_pragma_string():
    sample_str = """
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
    return sample_str


@pytest.fixture(scope='function')
def leaf_bool_pragma_string_w_semicolon(leaf_bool_pragma_string):
    sample_str = """
                     ensure: that ; semicolons: work;
    """
    return leaf_bool_pragma_string + sample_str


@pytest.fixture(scope='function')
def leaf_bool_pragma_string_single_line():
    sample_str = """pv:pv_name"""
    return sample_str


@pytest.fixture(scope='function')
def light_leaf_bool_pragma_string():
    str = """
                     pv: TEST:MAIN:NEW_VAR_OUT
                     io: o
                     pv: TEST:MAIN:NEW_VAR_IN
                     io: i
                     pv: TEST:MAIN:NEW_VAR_IO
                     io: io
                     pv: TEST:MAIN:NEW_VAR_SIMPLE
    """
    return str


@pytest.fixture(scope='function')
def branch_bool_pragma_string():
    string = """
            pv: FIRST
            pv: SECOND
    """
    return string


@pytest.fixture(scope='function')
def branch_bool_pragma_string_empty(branch_bool_pragma_string):
    string = branch_bool_pragma_string + """
            pv:
            pv:"""

    return string


@pytest.fixture(scope='function')
def branch_connection_pragma_string():
    string = """
            pv: MIDDLE
            aux: nothing
    """
    return string


@pytest.fixture(scope='function')
def empty_pv_pragma_string():
    string = """
            pv:
    """
    return string


@pytest.fixture(scope='function')
def branch_skip_pragma_string():
    str = """
            skip:
    """
    return str


@pytest.fixture(scope='function')
def example_singular_tmc_chains(light_leaf_bool_pragma_string,
                                branch_bool_pragma_string,
                                branch_connection_pragma_string):
    stem = BaseElement(element=None)
    stem.pragma = Configuration(branch_connection_pragma_string)
    leaf_a = BaseElement(element=None)
    leaf_a.pragma = Configuration(branch_bool_pragma_string)
    leaf_b = BaseElement(element=None)
    leaf_b.pragma = Configuration(light_leaf_bool_pragma_string)

    chain = TmcChain(
        [stem, leaf_a, leaf_b]
    )
    return chain.build_singular_chains()


def lint_record(dbd_file, record):
    assert record.valid
    linted = epics.lint_db(dbd=dbd_file, db=record.render_record())
    assert not len(linted.errors)
