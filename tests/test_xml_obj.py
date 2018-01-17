import pytest
import logging

import xml.etree.ElementTree as ET

#from pytpy.xml_obj import Symbol, DataType
from pytpy import Symbol, DataType


logger = logging.getLogger(__name__)

def test_Symbol_instantiation(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find("./Modules/Module/DataAreas/DataArea/Symbol")
    logging.debug(str(sym.find("./Name").text))
    try:
        s = Symbol(sym)
    except:
        pytest.fail("Instantiation of Symbol not completed")

    pytest.fail("Instantiation of DataType not completed")

def test_DataType_instantiation(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find("./DataTypes/DataType")
    logging.debug(str(sym.find("./Name").text))
    try:
        s = Symbol()
    except:
        pytest.fail("Instantiation of DataType not completed")
    
