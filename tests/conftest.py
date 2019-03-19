import pytest
import logging
import xml.etree.ElementTree as ET
import os

from pytmc import TmcFile
from pytmc.xml_collector import BaseElement, Configuration, TmcChain
logger = logging.getLogger(__name__)


def load_generic_tmc():
    f = open("generic.tmc", "r")
    return f


@pytest.fixture(scope='function')
def generic_tmc_root():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic_w_pragmas180426.tmc")
    tree = ET.parse(test_path)
    root = tree.getroot()
    return root


@pytest.fixture(scope='function')
def string_tmc_path():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic_w_pragmas180921.tmc")
    return test_path


@pytest.fixture(scope='function')
def string_tmc_root():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic_w_pragmas180921.tmc")
    tree = ET.parse(test_path)
    root = tree.getroot()
    return root


@pytest.fixture(scope='function')
def generic_tmc_path():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic_w_pragmas180426.tmc")
    return test_path


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
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic.tmc")
    return TmcFile(test_path)


@pytest.fixture(scope='function')
def generic_explorer():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic.tmc")
    tmc = TmcFile(test_path)
    return TmcExplorer(tmc)


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
