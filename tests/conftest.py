import pytest
import logging
import xml.etree.ElementTree as ET
import os

from pytmc import SingleRecordData, TmcFile, TmcExplorer

logger = logging.getLogger(__name__)

def load_generic_tmc():
    f = open("generic.tmc","r")
    return f


@pytest.fixture(scope='function')
def generic_tmc_root():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic_w_pragmas5.tmc")
    tree = ET.parse(test_path)
    root = tree.getroot()
    return root

@pytest.fixture(scope='function')
def generic_tmc_path():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic_w_pragmas5.tmc")
    return test_path


@pytest.fixture(scope='function')
def safe_record_factory():
    rec = SingleRecordData(
        pv = "GDET:FEE1:241:ENRC",
        rec_type = "ai",
        fields = dict([
            ("DTYP","asynInt32"),
            ("INP",None),
            ("ZNAM",""),
        ]),
        comment = "sample comment",
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
