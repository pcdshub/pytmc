import pytest
import logging

import xml.etree.ElementTree as ET

#from pytpy.xml_obj import Symbol, DataType
from pytpy import Symbol, DataType, SubItem
from pytpy.xml_obj import BaseElement
from collections import defaultdict

logger = logging.getLogger(__name__)


def test_BaseElement_type_rejection(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
    )
    logging.debug(str(sym.find("./Name").text))
    try:
        s = BaseElement(sym)
    except:
        pytest.fail("No error should have been raised")

    with pytest.raises(TypeError, message="TypeError expected"):
        s = BaseElement("string")


def test_BaseElement_get_raw_properties(generic_tmc_root):
    #Read properties of MAIN variable w/ pragma
    root = generic_tmc_root
    sym = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.NEW_VAR']"
    )
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    prop_out = s._get_raw_properties()
    prop_actual = root.findall(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.NEW_VAR']"
        + "/Properties/Property"
    )

    assert prop_out == prop_actual, "Reported Properties lists don't match"
    
    #Read properties of MAIN variable w/o pragma
    root = generic_tmc_root
    sym = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
    )
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    prop_out = s._get_raw_properties()
    assert prop_out == [], "Reported Properties lists don't match"
    
    #Read properties of DataType w/ pragma
    root = generic_tmc_root
    sym = root.find(
        "./DataTypes/DataType/[Name='iterator']"
    )
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    prop_out = s._get_raw_properties()
    prop_actual = root.findall(
        "./DataTypes/DataType/[Name='iterator']/Properties/Property"
    )
    assert prop_out == prop_actual, "Reported Properties lists don't match"

    #Read properties of DataType variable w/ pragma
    root = generic_tmc_root
    sym = root.find(
        "./DataTypes/DataType/SubItem/[Name='lim']"
    )
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    prop_out = s._get_raw_properties()
    prop_actual = root.findall(
        "./DataTypes/DataType/SubItem/[Name='lim']/Properties/Property"
    )
    assert prop_out == prop_actual, "Reported Properties lists don't match"


@pytest.mark.parametrize(
    "path,result",
    [
        (
            "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.NEW_VAR']",
            defaultdict(list,{'NEW_VAR attr':['17']})
        ),
        (
            "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']",
            defaultdict(list,{})
        ),
        (
            "./DataTypes/DataType/[Name='iterator']",
            defaultdict(list,{
                'PouType':['FunctionBlock'],
                'iterator attr':['42'],
            })
        ),
        (
            "./DataTypes/DataType/SubItem/[Name='lim']",
            defaultdict(list,{'lim attr':[None]})
        ),
    ]
)
def test_BaseElement_properties(generic_tmc_root, path, result):
    root = generic_tmc_root
    sym = root.find(path)
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    prop_out = s.properties 
    assert prop_out == result, "Incorrect properties found"
    

@pytest.mark.parametrize(
    "path,result",
    [
        (
            "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.NEW_VAR']",
            defaultdict(list,{'NEW_VAR attr':['17']})
        ),
        (
            "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']",
            defaultdict(list,{})
        ),
        (
            "./DataTypes/DataType/[Name='iterator']",
            defaultdict(list,{
                'iterator attr':['42'],
            })
        ),
        (
            "./DataTypes/DataType/SubItem/[Name='lim']",
            defaultdict(list,{'lim attr':[None]})
        ),
    ]
)
def test_Symbol_pragmas(generic_tmc_root, path, result):
    root = generic_tmc_root
    sym = root.find(path)
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    s.registered_pragmas = [
        'NEW_VAR attr',
        'iterator attr',
        'lim attr',
    ]
    pragma_out = s.pragmas
    print(pragma_out)
    assert pragma_out == result, "Incorrect pragmas found"


def test_Symbol_instantiation(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
    )
    logging.debug(str(sym.find("./Name").text))
    try:
        s = Symbol(sym)
    except:
        pytest.fail("Instantiation of Symbol not completed")


def test_DataType_instantiation(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find("./DataTypes/DataType/[Name='iterator']")
    logging.debug(str(sym.find("./Name").text))
    try:
        s = DataType(sym)
    except:
        pytest.fail("Instantiation of DataType not completed")
    

def test_SubItem_instantiation(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    ) 
    logging.debug(str(sym.find("./Name").text))
    try:
        s = SubItem(sym)
    except:
        pytest.fail("Instantiation of DataType not completed")


def test_BaseElement_get_raw_parent(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    ) 
    logging.debug(str(sym.find("./Name").text))
    s = BaseElement(sym)
    parent = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    )
    #pytest.fail("!!!!")


