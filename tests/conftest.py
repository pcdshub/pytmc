import pytest
import logging
import xml.etree.ElementTree as ET
import os

logger = logging.getLogger(__name__)

def load_generic_tmc():
    f = open("generic.tmc","r")
    return f


@pytest.fixture(scope='function')
def generic_tmc_root():
    directory = os.path.dirname(os.path.realpath(__file__))
    test_path = os.path.join(directory, "generic.tmc")
    tree = ET.parse(test_path)
    root = tree.getroot()
    return root
