import pytest
import logging

import xml.etree.ElementTree as ET

#from pytmc.xml_obj import Symbol, DataType
from pytmc import Symbol, DataType, SubItem
from pytmc.xml_obj import BaseElement, PvNotFrozenError, Configuration
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
                'pytmc':'name: ITERATORNAME'}, "Incorrect properties found"


def test_BaseElement_pragma(generic_tmc_root):
    root = generic_tmc_root
    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.NEW_VAR']"
    )
    base_element = BaseElement(symbol_xml)

    base_element.pragma.fix_to_config_name('TEST:MAIN:NEW_VAR_OUT')
    data = [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag':{'f_name':'ZNAM','f_set':'SINGLE'}},
        {'title': 'field', 'tag':{'f_name':'ONAM','f_set':'MULTI'}},
        {'title': 'field', 'tag':{'f_name':'SCAN','f_set':'1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init','tag':'True'},
    ]

    assert base_element.pragma.config == data


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


def test_DataType_datatype(generic_tmc_root):
    root = generic_tmc_root
    sym = root.find("./DataTypes/DataType/[Name='iterator']")
    logging.debug(str(sym.find("./Name").text))
    s = DataType(sym)

    assert s.datatype == "FunctionBlock"

    sym = root.find("./DataTypes/DataType/[Name='VERSION']")
    logging.debug(str(sym.find("./Name").text))
    s = DataType(sym)

    assert s.datatype == "Struct"

    sym = root.find("./DataTypes/DataType/[Name='_Implicit_KindOfTask']")
    logging.debug(str(sym.find("./Name").text))
    s = DataType(sym)

    assert s.datatype == "Enum"


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


def test_DataType_is_enum(string_tmc_root):
    root = string_tmc_root
    symbol_xml = root.find(
        "./DataTypes/DataType/[Name='DUT_ENUMTEST']"
    )
    print(symbol_xml)
    nonstr_symbol_element = DataType(symbol_xml)
    assert nonstr_symbol_element.is_enum == True

    root = string_tmc_root
    symbol_xml = root.find(
        "./DataTypes/DataType/[Name='DUT_STRUCT']"
    )
    print(symbol_xml)
    nonstr_symbol_element = DataType(symbol_xml)
    assert nonstr_symbol_element.is_enum == False


def test_raw_config(generic_tmc_root):
    root = generic_tmc_root

    element= root.find(
        "./DataTypes/DataType/[Name='iterator']"
    )
    el = DataType(element)
    assert el.raw_config == 'name: ITERATORNAME'


def test_has_config(generic_tmc_root):
    root = generic_tmc_root
    subitem_xml = root.find(
        "./DataTypes/DataType/[Name='iterator']/SubItem/[Name='lim']"
    )
    subitem_element = SubItem(subitem_xml)
    assert subitem_element.has_config == True

    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.count']"
    )
    symbol_element = Symbol(symbol_xml)
    assert symbol_element.has_config == False




def test_BaseElement_is_array(generic_tmc_root):
    root = generic_tmc_root

    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/"
        +"[Name='MAIN.dtype_samples_int_array']"
    )
    symbol_element = Symbol(symbol_xml)
    assert symbol_element.is_array

    datatype_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/"
        +"[Name='MAIN.dtype_samples_int_array']"
    )
    symbol_element = Symbol(symbol_xml)
    assert symbol_element.is_array

    item_xml = root.find(
        "./DataTypes/DataType/[Name='DUT_CONTAINER']/SubItem/"
        +"[Name='dtype_samples_iter_array']"
    )
    subitem_element = SubItem(item_xml)
    assert subitem_element.is_array


def test_BaseElement_iterable_length(string_tmc_root):
    root = string_tmc_root
    non_iter_symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/[Name='MAIN.NEW_VAR']"
    )
    non_iter_symbol_element = Symbol(non_iter_symbol_xml)
    assert non_iter_symbol_element.iterable_length is None
    array_symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/"
        +"[Name='MAIN.dtype_samples_int_array']"
    )
    array_symbol_element = BaseElement(array_symbol_xml)
    assert array_symbol_element.iterable_length == 5

    str_symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/"
        +"[Name='MAIN.StringTest']"
    )
    str_symbol_element = BaseElement(str_symbol_xml)
    assert str_symbol_element.iterable_length == 55


def test_BaseElement_is_string(string_tmc_root):
    root = string_tmc_root
    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/"
        +"[Name='MAIN.dtype_samples_int_array']"
    )
    nonstr_symbol_element = BaseElement(symbol_xml)
    assert nonstr_symbol_element.is_str == False

    symbol_xml = root.find(
        "./Modules/Module/DataAreas/DataArea/Symbol/"
        +"[Name='MAIN.StringTest']"
    )
    str_symbol_element = BaseElement(symbol_xml)
    assert str_symbol_element.is_str == True

@pytest.mark.parametrize("model_set",[
    (0),
    (1),
])
def test_Configuration_config_lines(leaf_bool_pragma_string_w_semicolon,
        leaf_bool_pragma_string_single_line, model_set):
    if model_set is 0:
        string = leaf_bool_pragma_string_w_semicolon
        test =  [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
            {'title': 'type', 'tag': 'bo'},
            {'title': 'field', 'tag':'ZNAM\tSINGLE'},
            {'title': 'field', 'tag':'ONAM\tMULTI'},
            {'title': 'field', 'tag':'SCAN\t1 second'},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'o'},
            {'title': 'init', 'tag': 'True'},
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_IN'},
            {'title': 'type', 'tag': 'bi'},
            {'title': 'field', 'tag':'ZNAM\tSINGLE'},
            {'title': 'field', 'tag':'ONAM\tMULTI'},
            {'title': 'field', 'tag':'SCAN\t1 second'},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'i'},
            {'title': 'ensure', 'tag': 'that'},
            {'title': 'semicolons', 'tag': 'work'},
        ]
    if model_set is 1:
        string = leaf_bool_pragma_string_single_line
        test = [{'title': "pv", 'tag':'pv_name'}]


    print(type(string))
    print(string)
    cfg = Configuration(string)
    result = cfg._config_lines()
    assert result == test


def test_Configuration_neaten_field(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    cfg_lines = cfg._config_lines()
    result = cfg._neaten_field(cfg_lines[2]['tag'])

    assert result == {'f_name':'ZNAM','f_set':'SINGLE'}


def test_Configuration_formatted_config_lines(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg._formatted_config_lines()
    assert result == [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag':{'f_name':'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag':{'f_name':'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init', 'tag': 'True'},
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_IN'},
        {'title': 'type', 'tag': 'bi'},
        {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag':{'f_name':'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag':{'f_name':'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'i'},
    ]


def test_Configuration_config_by_name(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg._config_by_name()
    assert result == [
        [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
            {'title': 'type', 'tag': 'bo'},
            {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
            {'title': 'field', 'tag':{'f_name':'ONAM', 'f_set': 'MULTI'}},
            {'title': 'field', 'tag':{'f_name':'SCAN', 'f_set': '1 second'}},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'o'},
            {'title': 'init', 'tag': 'True'},
        ],
        [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_IN'},
            {'title': 'type', 'tag': 'bi'},
            {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
            {'title': 'field', 'tag':{'f_name':'ONAM', 'f_set': 'MULTI'}},
            {'title': 'field', 'tag':{'f_name':'SCAN', 'f_set': '1 second'}},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'i'},
        ]
    ]


def test_Configuration_select_config_by_name(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg._select_config_by_name('TEST:MAIN:NEW_VAR_OUT')
    assert result == [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag':{'f_name':'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag':{'f_name':'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init', 'tag': 'True'},
    ]


def test_Configuration_config_names(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg.config_names()
    assert result == [
        "TEST:MAIN:NEW_VAR_OUT",
        "TEST:MAIN:NEW_VAR_IN"
    ]


def test_Configuration_fix_to_config_name(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg.fix_to_config_name('TEST:MAIN:NEW_VAR_OUT')
    assert cfg.config == [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag':{'f_name':'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag':{'f_name':'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init', 'tag': 'True'},
    ]


def test_Configuration_add_config_line(branch_bool_pragma_string):
    cfg = Configuration(branch_bool_pragma_string)
    cfg.add_config_line('pv','THIRD')
    assert cfg.config == [
        {'title': 'pv', 'tag': 'FIRST'},
        {'title': 'pv', 'tag': 'SECOND'},
        {'title': 'pv', 'tag': 'THIRD'},
    ]


def test_Configuration_add_config_field(branch_bool_pragma_string):
    cfg = Configuration(branch_bool_pragma_string)
    cfg.add_config_field('ABC','XYZ',1)
    assert cfg.config == [
        {'title': 'pv', 'tag': 'FIRST'},
        {'title': 'field', 'tag': {'f_name': 'ABC', 'f_set': 'XYZ'}},
        {'title': 'pv', 'tag': 'SECOND'},
    ]


def test_Configuration_get_config_lines(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    response = cfg.get_config_lines('io')

    assert response == [
        {'title': 'io', 'tag': 'o'},
        {'title': 'io', 'tag': 'i'},
    ]


def test_Configuration_get_config_lines(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    response = cfg.get_config_fields('ZNAM')
    assert response == [
        {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag':{'f_name':'ZNAM', 'f_set': 'SINGLE'}},
    ]


def test_Configuration__eq__(leaf_bool_pragma_string):
    cfg_A = Configuration(leaf_bool_pragma_string)
    cfg_B = Configuration(leaf_bool_pragma_string)
    assert cfg_A == cfg_B
    cfg_A.add_config_line("a","b")
    assert cfg_A != cfg_B


def test_Configuration_concat(branch_connection_pragma_string,
            branch_bool_pragma_string_empty, empty_pv_pragma_string):
    cfg_A = Configuration(branch_connection_pragma_string)
    cfg_AA = Configuration(empty_pv_pragma_string)
    cfg_B = Configuration(branch_bool_pragma_string_empty)
    cfg_B.fix_to_config_name("FIRST")
    new_config = Configuration(config=[])
    new_config.concat(cfg_A)
    new_config.concat(cfg_AA)
    new_config.concat(cfg_B)
    print(new_config.config)
    assert new_config.config == [
        {'title':'pv', 'tag':'MIDDLE:FIRST'},
        {'title':'aux', 'tag':'nothing'},
    ]
    #assert False


def test_Configuration_seek():
    c = Configuration(config=[])
    c.add_config_line(title="pv",tag="ABC")
    c.add_config_field(f_name="ONAM",f_set="ABC")
    assert c.seek(['title'],'pv') == [{'title':'pv','tag':'ABC'}]
    assert c.seek(['tag','f_name'],'ONAM') == [
        {'title':'field','tag':{'f_name':'ONAM','f_set':'ABC'}}
    ]
    assert c.seek(['bad'],3) == []
