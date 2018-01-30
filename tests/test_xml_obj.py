import pytest
import logging

import xml.etree.ElementTree as ET

#from pytmc.xml_obj import Symbol, DataType
from pytmc import Symbol, DataType, SubItem
from pytmc.xml_obj import BaseElement
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
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.count']"
    )
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    prop_out = s._get_raw_properties()

    prop_actual = root.findall(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
        + "/Properties/Property"
    )
    
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


def test_BaseElement_properties(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find("./DataTypes/DataType/[Name='iterator']")
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    prop_out = s.properties 
    assert prop_out == {
                'PouType':'FunctionBlock',
                'iterator attr':'42',
                'pytmc_dt_name':'ITERATORNAME'}, "Incorrect properties found"
   

@pytest.mark.parametrize(
    "path,result",
    [
        (
            "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.NEW_VAR']",
            {'NEW_VAR attr':'17'}
        ),
        (
            "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']",
            {}
        ),
        (
            "./DataTypes/DataType/[Name='iterator']",
            {
                'iterator attr':'42',
            }
        ),
        (
            "./DataTypes/DataType/SubItem/[Name='lim']",
            {'lim attr':None}
        ),
    ]
)
def test_Symbol_pragmas(generic_tmc_root, path, result):
    root = generic_tmc_root
    sym = root.find(path)
    logging.debug(str(sym.find("./Name").text))    
    s = BaseElement(sym)
    s.registered_pragmas += [
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


def test_Symbol_tc_type(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
    )
    logging.debug(str(sym.find("./Name").text))
    s = Symbol(sym)
    
    assert s.tc_type == "DINT"
    
    sym = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.test_iterator']"
    )
    logging.debug(str(sym.find("./Name").text))
    s = Symbol(sym)
    
    assert s.tc_type == "iterator"


def test_DataType_tc_type(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find("./DataTypes/DataType/[Name='iterator']")
    logging.debug(str(sym.find("./Name").text))
    s = DataType(sym)
    
    assert s.tc_type == "FunctionBlock"
    
    sym = root.find("./DataTypes/DataType/[Name='VERSION']")
    logging.debug(str(sym.find("./Name").text))
    s = DataType(sym)
    
    assert s.tc_type == "Struct"
    
    sym = root.find("./DataTypes/DataType/[Name='_Implicit_KindOfTask']")
    logging.debug(str(sym.find("./Name").text))
    s = DataType(sym)
    
    assert s.tc_type == "Enum"


def test_SubItem_tc_type(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    ) 
    logging.debug(str(sym.find("./Name").text))
    s = SubItem(sym)
    
    assert s.tc_type == "DINT"
    
    sym = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='out']"
    ) 
    logging.debug(str(sym.find("./Name").text))
    s = SubItem(sym)
    
    assert s.tc_type == "DINT"


def test_eq(generic_tmc_root):
    root = generic_tmc_root
    
    par_element= root.find(
        "./DataTypes/DataType/[Name='iterator']"
    )
    par = DataType(par_element)
    c0_element = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='increment']"
    ) 
    c0 = SubItem(c0_element)
    c1_element = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='out']"
    ) 
    c1 = SubItem(c1_element)
    c2_element = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='out']"
    )
    c2 = SubItem(c2_element)
   
    assert c0 != par
    assert c0 != c1
    assert c1 == c2
 

def test_parent_relation(generic_tmc_root):
    root = generic_tmc_root
    
    par_element= root.find(
        "./DataTypes/DataType/[Name='iterator']"
    )
    par = DataType(par_element)
    c0_element = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='increment']"
    ) 
    c0 = SubItem(c0_element)
    c1_element = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='out']"
    ) 
    c1 = SubItem(c1_element)
    c2_element = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='value']"
    )
    c2 = SubItem(c2_element)


    c0.parent = par
    c1.parent = par
    c2.parent = par
    

    assert c0 in par.children
    assert c1 in par.children
    assert c2 in par.children
    assert c0.parent == par
    assert c1.parent == par
    assert c2.parent == par

    print(par.children)
    print(c1.parent)
    del c1.parent 

    assert c0 in par.children
    assert c1 not in par.children
    assert c2 in par.children
    assert c0.parent == par
    assert c1.parent == None
    assert c2.parent == par

    c0.parent = None

    assert c0 not in par.children
    assert c1 not in par.children
    assert c2 in par.children
    assert c0.parent == None
    assert c1.parent == None
    assert c2.parent == par


def test_BaseElement_name(generic_tmc_root):
    root = generic_tmc_root
    
    element= root.find(
        "./DataTypes/DataType/[Name='iterator']"
    )
    el = DataType(element)
    assert el.name == 'iterator'
    

def test_DataType_tc_extends(generic_tmc_root):
    root = generic_tmc_root
    
    element= root.find(
        "./DataTypes/DataType/[Name='DUT_STRUCT']"
    )
    el = DataType(element)
    assert el.tc_extends == None

    element= root.find(
        "./DataTypes/DataType/[Name='DUT_EXTENSION_STRUCT']"
    )
    el = DataType(element)
    assert el.tc_extends == 'DUT_STRUCT'

def test_all_dtname(generic_tmc_root):
    root = generic_tmc_root
    
    element= root.find(
        "./DataTypes/DataType/[Name='iterator']"
    )
    el = DataType(element)
    assert el.dt == 'ITERATORNAME'

def test_all_fields(generic_tmc_root):
    root = generic_tmc_root
    subitem_xml = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    ) 
    subitem_element = SubItem(subitem_xml)
    assert subitem_element.field == {'DTYP':'asynFloat64','EGU':'mm'}
    
    root = generic_tmc_root
    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
    ) 
    symbol_element = Symbol(symbol_xml)
    assert subitem_element.field == {'DTYP':'asynFloat64','EGU':'mm'}

def test_all_pv(generic_tmc_root):
    root = generic_tmc_root
    subitem_xml = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    ) 
    subitem_element = SubItem(subitem_xml)
    assert subitem_element.pv == 'LIM'
    
    root = generic_tmc_root
    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
    ) 
    symbol_element = Symbol(symbol_xml)
    assert subitem_element.pv== 'TEST:MAIN:MULTI'

def test_all_record_type(generic_tmc_root):
    root = generic_tmc_root
    subitem_xml = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    ) 
    subitem_element = SubItem(subitem_xml)
    assert subitem_element.record_type == 'ao'
    
    root = generic_tmc_root
    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.ulimit']"
    ) 
    symbol_element = Symbol(symbol_xml)
    assert subitem_element.record_type== 'TEST:MAIN:MULTI'
