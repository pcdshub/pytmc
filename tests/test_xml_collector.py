import pytest
import logging
import textwrap
from copy import deepcopy
import xml.etree.ElementTree as ET

from pytmc import Symbol, DataType, SubItem
from pytmc.xml_obj import BaseElement, Configuration

from pytmc import TmcFile, PvPackage
from pytmc.xml_collector import ElementCollector, TmcChain, BaseRecordPackage
from pytmc.xml_collector import ChainNotSingularError

from collections import defaultdict, OrderedDict as odict

logger = logging.getLogger(__name__)

# ElementCollector tests

def test_ElementCollector_instantiation(generic_tmc_root):
    try:
        col = ElementCollector()
    except Error as e:
        pytest.fail(
            "Instantiation of XmlObjCollector should not generate errors"
        )


def test_ElementCollector_add(generic_tmc_root):
    root = generic_tmc_root
    iterator = DataType(root.find("./DataTypes/DataType/[Name='iterator']"))
    version = DataType(root.find("./DataTypes/DataType/[Name='VERSION']"))
    col = ElementCollector()
    col.add(iterator)
    col.add(version)
    assert 'iterator' in col
    assert 'VERSION' in col

    col.add(version)
    assert len(col) == 2

    assert col['iterator'] == iterator
    assert col['VERSION'] == version


def test_ElementCollector_registered(generic_tmc_root):
    root = generic_tmc_root
    iterator = DataType(root.find("./DataTypes/DataType/[Name='iterator']"))

    version = DataType(root.find("./DataTypes/DataType/[Name='VERSION']"))
    col = ElementCollector()

    col.add(iterator)
    col.add(version)

    assert col.registered == {'iterator': iterator}


# TmcFile tests

def test_TmcFile_instantiation(generic_tmc_path, generic_tmc_root):
    try:
        tmc = TmcFile(generic_tmc_path)
    except Error as e:
        pytest.fail("Instantiation of TmcFile should not generate errors")


def test_TmcFile_isolate_Symbols(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_Symbols()

    assert "MAIN.ulimit" in tmc.all_Symbols
    assert "MAIN.count" in tmc.all_Symbols
    assert "MAIN.NEW_VAR" in tmc.all_Symbols
    assert "MAIN.test_iterator" in tmc.all_Symbols
    assert "Constants.RuntimeVersion" in tmc.all_Symbols

    assert len(tmc.all_Symbols) == 25


def test_TmcFile_isolate_DataTypes(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_DataTypes()

    assert "iterator" in tmc.all_DataTypes
    assert "VERSION" in tmc.all_DataTypes

    assert len(tmc.all_DataTypes) == 11


def test_TmcFile_isolate_SubItems(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_DataTypes(process_subitems=False)
    tmc.isolate_SubItems('iterator')

    assert 'increment' in tmc.all_SubItems['iterator']
    assert 'out' in tmc.all_SubItems['iterator']
    assert 'value' in tmc.all_SubItems['iterator']
    assert 'lim' in tmc.all_SubItems['iterator']
    assert 'extra1' in tmc.all_SubItems['iterator']
    assert 'extra2' in tmc.all_SubItems['iterator']
   
    assert len(tmc.all_SubItems['iterator']) == 6


def test_TmcFile_isolate_all(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_all()
    
    assert "MAIN.ulimit" in tmc.all_Symbols
    assert "MAIN.count" in tmc.all_Symbols
    assert "MAIN.NEW_VAR" in tmc.all_Symbols
    assert "MAIN.test_iterator" in tmc.all_Symbols
    assert "Constants.RuntimeVersion" in tmc.all_Symbols

    assert len(tmc.all_Symbols) == 25


    assert "iterator" in tmc.all_DataTypes
    assert "VERSION" in tmc.all_DataTypes

    assert len(tmc.all_DataTypes) == 11

    assert 'increment' in tmc.all_SubItems['iterator']
    assert 'out' in tmc.all_SubItems['iterator']
    assert 'value' in tmc.all_SubItems['iterator']
    assert 'lim' in tmc.all_SubItems['iterator']
    assert 'extra1' in tmc.all_SubItems['iterator']
    assert 'extra2' in tmc.all_SubItems['iterator']
   
    assert len(tmc.all_SubItems['iterator']) == 6


def test_TmcFile_explore_all(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_all()
    complete_chain_list = tmc.explore_all()

    #assert len(complete_chain_list) == 27
    assert [tmc.all_Symbols['MAIN.ulimit']] in complete_chain_list

    target = [
        tmc.all_Symbols['MAIN.test_iterator'],
        tmc.all_SubItems['iterator']['extra1'],
        tmc.all_SubItems['DUT_STRUCT']['struct_var']
    ]
    assert target in complete_chain_list


def test_TmcFile_recursive_explore(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_all()

    root_path = [tmc.all_SubItems['iterator']['extra1']]
    response = tmc.recursive_explore(root_path)
    assert response == [
        [tmc.all_SubItems['iterator']['extra1'],
            tmc.all_SubItems['DUT_STRUCT']['struct_var']],
        [tmc.all_SubItems['iterator']['extra1'],
            tmc.all_SubItems['DUT_STRUCT']['struct_var2']],
    ]

    root_path = [tmc.all_Symbols['MAIN.struct_extra']]
    response = tmc.recursive_explore(root_path)
    print(response)
    assert response == [
        [tmc.all_Symbols['MAIN.struct_extra'],
            tmc.all_SubItems['DUT_STRUCT']['struct_var']],
        [tmc.all_Symbols['MAIN.struct_extra'],
            tmc.all_SubItems['DUT_STRUCT']['struct_var2']],
        [tmc.all_Symbols['MAIN.struct_extra'],
            tmc.all_SubItems['DUT_EXTENSION_STRUCT']['tertiary']],
    ]


def test_TmcFile_recursive_list_SubItems(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_all()
    response = tmc.recursive_list_SubItems(
        tmc.all_DataTypes['DUT_EXTENSION_STRUCT']
    )
    assert response == [
            tmc.all_SubItems['DUT_STRUCT']['struct_var'],
            tmc.all_SubItems['DUT_STRUCT']['struct_var2'],
            tmc.all_SubItems['DUT_EXTENSION_STRUCT']['tertiary'],
    ]


def test_TmcFile_create_chains(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.create_chains()
    target = [tmc.all_Symbols['MAIN.ulimit']]
    accept = False
    for row in tmc.all_TmcChains:
        if row.chain == target:
            accept = True
            break
    assert accept

    
    target = [
        tmc.all_Symbols['MAIN.test_iterator'],
        tmc.all_SubItems['iterator']['extra1'],
        tmc.all_SubItems['DUT_STRUCT']['struct_var']
    ]
    accept = False
    for row in tmc.all_TmcChains:
        if row.chain == target:
            accept = True
            break
    assert accept


def test_TmcFile_isolate_chains(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    
    tmc.create_chains()
    tmc.isolate_chains()
    print(len(tmc.all_TmcChains))
    print(len(tmc.all_singular_TmcChains))
    
    target = [
        tmc.all_Symbols['MAIN.test_iterator'],
        tmc.all_SubItems['iterator']['extra1'],
        tmc.all_SubItems['DUT_STRUCT']['struct_var']
    ]
    accept = False
    count = 0
    for row in tmc.all_singular_TmcChains:
        if row.chain[0].name == 'MAIN.container_struct':
            if row.chain[1].name == 'dtype_samples_iter_array':
                if row.chain[2].name == 'extra1':
                     if row.chain[3].name == 'struct_var':
                        count += 1

    assert count == 4


def test_TmcFile_create_packages(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.create_chains()
    tmc.create_packages()
    assert False



# TmcChain tests

def test_TmcChain_forkmap(generic_tmc_path, leaf_bool_pragma_string,
            branch_bool_pragma_string, branch_connection_pragma_string):
    stem = BaseElement(element=None)
    stem.pragma = Configuration(branch_connection_pragma_string) 
    leaf_a = BaseElement(element=None)
    leaf_a.pragma = Configuration(branch_bool_pragma_string)
    leaf_b = BaseElement(element=None)
    leaf_b.pragma = Configuration(leaf_bool_pragma_string)

    chain = TmcChain(
        [stem, leaf_a, leaf_b]
    )

    result = chain.forkmap()

    assert result == [
        ['MIDDLE'],
        ['FIRST', 'SECOND'],
        ['TEST:MAIN:NEW_VAR_OUT', 'TEST:MAIN:NEW_VAR_IN']
    ]


def test_TmcChain_is_singular(generic_tmc_path, leaf_bool_pragma_string,
            branch_bool_pragma_string, branch_connection_pragma_string):
    stem = BaseElement(element=None)
    stem.pragma = Configuration(branch_connection_pragma_string) 
    leaf_a = BaseElement(element=None)
    leaf_a.pragma = Configuration(branch_bool_pragma_string)
    leaf_b = BaseElement(element=None)
    leaf_b.pragma = Configuration(leaf_bool_pragma_string)

    chain = TmcChain(
        [stem, leaf_a, leaf_b]
    )
    logger.debug(str(chain.forkmap()))
    assert chain.is_singular() == False

    for element in chain.chain:
        element.pragma.fix_to_config_name(element.pragma.config_names()[0])
    
    # for element in chain.chain:
        # print(element.pragma.config)

    assert chain.is_singular() == True


def test_TmcChain_recursive_permute():
    l = [['a'],['b','c','d'],['e','f']]
    chain = TmcChain(None)
    result = chain._recursive_permute(l)
    for s in result:
        print(s)
    assert result == [
        [['a'],['b'],['e']],
        [['a'],['c'],['e']],
        [['a'],['d'],['e']],
        [['a'],['b'],['f']],
        [['a'],['c'],['f']],
        [['a'],['d'],['f']],
    ]


def test_TmcChain_build_singular_chains(generic_tmc_path, 
            leaf_bool_pragma_string, branch_bool_pragma_string,
            branch_connection_pragma_string):
    stem = BaseElement(element=None)
    stem.pragma = Configuration(branch_connection_pragma_string) 
    leaf_a = BaseElement(element=None)
    leaf_a.pragma = Configuration(branch_bool_pragma_string)
    leaf_b = BaseElement(element=None)
    leaf_b.pragma = Configuration(leaf_bool_pragma_string)

    chain = TmcChain(
        [stem, leaf_a, leaf_b]
    )
    logger.debug(str(chain.forkmap()))

    response_set = chain.build_singular_chains()
    assert len(response_set) == 4
    for x in response_set:
        logger.debug(str(x.forkmap()))
        assert x.is_singular()
    
    for x in response_set:
        for y in response_set:
            if x is y:
                continue
            if x == y:
                assert False

    assert response_set[0].forkmap() == [
        ['MIDDLE'],
        ['FIRST'],
        ['TEST:MAIN:NEW_VAR_OUT'],
    ]
    assert response_set[1].forkmap() == [
        ['MIDDLE'],
        ['SECOND'],
        ['TEST:MAIN:NEW_VAR_OUT'],
    ]
    assert response_set[2].forkmap() == [
        ['MIDDLE'],
        ['FIRST'],
        ['TEST:MAIN:NEW_VAR_IN'],
    ]
    assert response_set[3].forkmap() == [
        ['MIDDLE'],
        ['SECOND'],
        ['TEST:MAIN:NEW_VAR_IN'],
    ]


@pytest.fixture(scope='function')
def sample_TmcChain(generic_tmc_path, 
            leaf_bool_pragma_string, branch_bool_pragma_string,
            branch_connection_pragma_string):
    stem = BaseElement(element=None)
    stem.pragma = Configuration(branch_connection_pragma_string) 
    leaf_a = BaseElement(element=None)
    leaf_a.pragma = Configuration(branch_bool_pragma_string)
    leaf_b = BaseElement(element=None)
    leaf_b.pragma = Configuration(leaf_bool_pragma_string)

    chain = TmcChain(
        [stem, leaf_a, leaf_b]
    )
    
    return chain


def test_TmcChain_naive_config(sample_TmcChain):
    with pytest.raises(ChainNotSingularError):
        sample_TmcChain.naive_config()

    test_chain = sample_TmcChain.build_singular_chains()[0]
    cfg = test_chain.naive_config()
    for x in test_chain.chain:
        print(x.pragma.config)
    print(cfg.config)
    assert cfg.config[0:3] == [
        {'title':'pv', 'tag':'MIDDLE:FIRST:TEST:MAIN:NEW_VAR_OUT'},
        {'title':'aux', 'tag':'nothing'},
        {'title':'type', 'tag':'bo'},
    ]


def test_TmcChain_name_list():
    stem = BaseElement(element=None)
    stem.name = "stem"
    branch = BaseElement(element=None)
    branch.name = "branch"
    leaf = BaseElement(element=None)
    leaf.name = "leaf"

    chain = TmcChain(
        [stem, branch, leaf]
    )
    assert chain.name_list == ["stem", "branch", "leaf"]


# BaseRecordPackage tests

def test_BaseRecordPackage_generate_naive_config(sample_TmcChain):
    test_chain = sample_TmcChain.build_singular_chains()[0]
    brp = BaseRecordPackage(test_chain)
    brp.generate_naive_config()
    assert brp.cfg.config[0:3] == [
        {'title':'pv', 'tag':'MIDDLE:FIRST:TEST:MAIN:NEW_VAR_OUT'},
        {'title':'aux', 'tag':'nothing'},
        {'title':'type', 'tag':'bo'},
    ]


def test_BaseRecordPackage_apply_config_valid(sample_TmcChain):
    test_chain = sample_TmcChain.build_singular_chains()[0]
    brp = BaseRecordPackage(test_chain)
    brp.generate_naive_config()
    for x in brp.cfg.config:
        print(x)
    
    brp.validation_list = [
        {'path':[],'target':3},
    ]
    assert brp.apply_config_validation() == [
        {'path':[],'target':3},
    ]

    brp.validation_list = [
        {'path':['tag','f_name'],'target':'SCAN'},
        {'path':['title'],'target':'pv'},
    ]
    assert len(brp.apply_config_validation()) == 0


def test_BaseRecordPackage_standard_as_dict():
    brp = BaseRecordPackage()
    brp.cfg.add_config_line('pv','example_pv')
    brp.cfg.add_config_line('type','ao')
    brp.cfg.add_config_field('ABC','test 0')
    assert brp.standard_as_dict() == {
        'pv':'example_pv',
        'type':'ao',
        'field':{
            'ABC':'test 0'
        }
    }


def test_BaseRecordPackage_render_standard():
    brp = BaseRecordPackage()
    brp.cfg.add_config_line('pv','example_pv')
    brp.cfg.add_config_line('type','ao')
    brp.cfg.add_config_field("PINI","1")
    brp.cfg.add_config_field('ABC','test 0')
    target_response="""\
    record(ao,"example_pv"){
        field(PINI, "1")
        field(ABC, "test 0")
    }\
    """
    target_response = textwrap.dedent(target_response).strip()
    assert target_response == brp.render_standard()


@pytest.mark.skip(reason="Feature pending")
def test_BaseRecordPackage_ID_type():
    brp = BaseRecordPackage()
    brp.cfg.add_config_line('pv','example_pv')
    brp.cfg.add_config_line('type','ao')
    brp.cfg.add_config_field("PINI","1")
    assert brp.ID_type() == 'standard'
    
    brp = BaseRecordPackage()
    brp.cfg.add_config_line('pv','example_pv')
    brp.cfg.add_config_line('type','motor')
    brp.cfg.add_config_field("PINI","1")
    assert brp.ID_type() == 'motor'


def test_BaseRecordPackage_guess_common():
    brp = BaseRecordPackage()
    assert True == brp.guess_common()
    print(brp.cfg.config)
    [pini] = brp.cfg.get_config_fields('PINI')
    assert pini['tag']['f_set'] == '"1"'
    [tse] = brp.cfg.get_config_fields('TSE')
    assert tse['tag']['f_set'] == '-2'


@pytest.mark.parametrize("tc_type, sing_index, final_type",[
        ("BOOL", 0, 'bo'),
        ("BOOL", 2, 'bi'),
        ("BOOL", 4, 'bo'),
        ("INT", 0, 'ao'),
        ("INT", 2, 'ai'),
        ("INT", 4, 'ao'),
        ("LREAL", 0, 'ao'),
        ("LREAL", 2, 'ai'),
        ("LREAL", 4, 'ao'),
        ("STRING", 0, 'waveform'),
        ("STRING", 2, 'waveform'),
        ("STRING", 4, 'waveform'),
])
def test_BaseRecordPackage_guess_type(example_singular_tmc_chains,
            tc_type, sing_index, final_type):
    # chain must be broken into singular
    # for x in example_singular_tmc_chains:
    #     z = BaseRecordPackage(x)
    #     print(z.cfg.config)
    #     z.generate_naive_config()
    #     print(z.cfg.config)
    # assert False
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    logger.debug(str(record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    assert True == record.guess_type()
    [field] = record.cfg.get_config_lines('type')
    assert field['tag'] == final_type 


@pytest.mark.parametrize("tc_type, sing_index, final_io",[
        ("BOOL", 6, 'io'),
        ("INT", 6, 'io'),
        ("LREAL", 6, 'io'),
        ("STRING", 6, 'io'),
])
def test_BaseRecordPackage_guess_io(example_singular_tmc_chains,
            tc_type, sing_index, final_io):
    # chain must be broken into singular
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    logger.debug(str(record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    assert True == record.guess_io()
    print(record.cfg.config)
    [field] = record.cfg.get_config_lines('io')
    assert field['tag'] == final_io 


@pytest.mark.parametrize("tc_type, sing_index, final_DTYP",[
        ("BOOL", 0, '"asynInt32"'),
        ("BOOL", 2, '"asynInt32"'),
        ("INT", 0, '"asynInt32"'),
        ("INT", 2, '"asynInt32"'),
        ("LREAL", 0, '"asynFloat64"'),
        ("LREAL", 2, '"asynFloat64"'),
        ("STRING", 0, '"asynInt8ArrayOut"'),
        ("STRING", 2, '"asynInt8ArrayIn"'),
        ("STRING", 4, '"asynInt8ArrayOut"'),
])
def test_BaseRecordPackage_guess_DTYP(example_singular_tmc_chains,
            tc_type, sing_index, final_DTYP):
    # chain must be broken into singular
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    logger.debug((record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    assert True == record.guess_DTYP()
    logger.debug((record.cfg.config))
    [field] = record.cfg.get_config_fields('DTYP')
    assert field['tag']['f_set'] == final_DTYP 


@pytest.mark.parametrize("tc_type, sing_index, field_type, final_INP_OUT",[
        ("BOOL", 0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
        ("BOOL", 2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
        ("BOOL", 6, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
        ("INT", 0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
        ("INT", 2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
        ("INT", 6, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
        ("LREAL", 0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
        ("LREAL", 2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
        ("LREAL", 6, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
        ("STRING", 0, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
        ("STRING", 2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
        ("STRING", 6, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
])
def test_BaseRecordPackage_guess_INP_OUT(example_singular_tmc_chains,
            tc_type, sing_index, field_type, final_INP_OUT):
    # chain must be broken into singular
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    if tc_type == "STRING":
        record.chain.last.is_str = True
    for element, idx in zip(record.chain.chain,range(3)):
        element.name = chr(97+idx)
    record.generate_naive_config()
    record.guess_io()
    assert True == record.guess_INP_OUT()
    print(record.cfg.config)
    
    [field] = record.cfg.get_config_fields(field_type)
    if field_type == "OUT":
        assert record.cfg.get_config_fields('INP') == []
    if field_type == "INP":
        assert record.cfg.get_config_fields('OUT') == []
    
    assert field['tag']['f_set'] == final_INP_OUT


@pytest.mark.parametrize("tc_type, sing_index, final_SCAN",[
        ("BOOL", 0, 'Passive'),
        ("BOOL", 2, 'I/O Intr'),
        ("BOOL", 6, 'Passive'),
        ("INT", 0, 'Passive'),
        ("INT", 2, '.5 second'),
        ("INT", 6, 'Passive'),
        ("LREAL", 0, 'Passive'),
        ("LREAL", 2, '.5 second'),
        ("LREAL", 6, 'Passive'),
        ("STRING", 0, 'Passive'),
        ("STRING", 2, '.5 second'),
        ("STRING", 6, 'Passive'),
])
def test_BaseRecordPackage_guess_SCAN(example_singular_tmc_chains,
            tc_type, sing_index, final_SCAN):
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    logger.debug((record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    record.guess_io()
    assert True == record.guess_SCAN()
    logger.debug(str(record.cfg.config))
    [field] = record.cfg.get_config_fields('SCAN')
    assert field['tag']['f_set'] == final_SCAN 

@pytest.mark.parametrize("tc_type, sing_index, final_ZNAM, final_ONAM, ret",[
        ("BOOL", 0, 'Zero', "One", True),
        ("STRING", 0, None, None, False),
])
def test_BaseRecordPackage_guess_OZ_NAM(example_singular_tmc_chains,
            tc_type, sing_index, final_ZNAM, final_ONAM, ret):
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    assert ret == record.guess_OZ_NAM()
    o = record.cfg.get_config_fields('ONAM')
    z = record.cfg.get_config_fields('ZNAM')
    if final_ONAM is not None:
        assert o[0]['tag']['f_set'] == final_ONAM
    else:
        assert len(o) == 0
    if final_ZNAM is not None:
        assert z[0]['tag']['f_set'] == final_ZNAM 
    else :
        assert len(z) == 0

@pytest.mark.parametrize("tc_type, sing_index, final_PREC, ret",[
        ("LREAL", 0, '3', True),
        ("STRING", 0, None, False),
])
def test_BaseRecordPackage_guess_PREC(example_singular_tmc_chains,
            tc_type, sing_index, final_PREC, ret):
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    print(record.cfg.config)
    record.guess_type()
    if final_PREC is None:
        assert False == record.guess_PREC()
        with pytest.raises(ValueError):
            [out] = record.cfg.get_config_fields("PREC")
    else:
        assert True == record.guess_PREC()
        [out] = record.cfg.get_config_fields("PREC")
        assert out['tag']['f_set'] == "3" 


@pytest.mark.parametrize("tc_type, sing_index, is_str, is_arr, final_FTVL",[
        ("INT", 0, False, False, None),
        pytest.mark.skip(
            ("INT", 0, False, True, "FINISH"),
            reason="feature pending"),
        ("LREAL", 0, False, True, "DOUBLE"),
        ("STRING", 0, True, False, "CHAR"),
])
def test_BaseRecordPackage_guess_FTVL(example_singular_tmc_chains,
            tc_type, sing_index, is_str, is_arr, final_FTVL):
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_arr
    record.chain.last.is_str = is_str
    record.generate_naive_config()
    result = record.guess_FTVL()
    print(record.cfg.config)
    if final_FTVL is None:
        assert False == result
        with pytest.raises(ValueError):
            [out] = record.cfg.get_config_fields("FTVL")
    else:
        assert True == result
        [out] = record.cfg.get_config_fields("FTVL")
        assert out['tag']['f_set'] == final_FTVL


@pytest.mark.parametrize("tc_type, sing_index, is_str, is_arr, final_NELM",[
        ("INT", 0, False, False, None),
        ("INT", 0, False, True, 3),
        ("LREAL", 0, False, True, 9),
        ("STRING", 0, True, False, 12),
])
def test_BaseRecordPackage_guess_NELM(example_singular_tmc_chains,
            tc_type, sing_index, is_str, is_arr, final_NELM):
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_arr
    record.chain.last.is_str = is_str
    record.chain.last.iterable_length = final_NELM
    record.generate_naive_config()
    result = record.guess_NELM()
    print(record.cfg.config)
    if final_NELM is None:
        assert False == result
        with pytest.raises(ValueError):
            [out] = record.cfg.get_config_fields("NELM")
    else:
        assert True == result
        [out] = record.cfg.get_config_fields("NELM")
        assert out['tag']['f_set'] == final_NELM
        

@pytest.mark.parametrize("tc_type, sing_index, is_str, is_arr, final_NELM",[
        ("INT", 0, False, False, None),
        ("INT", 0, False, True, 3),
        ("LREAL", 0, False, True, 9),
        ("STRING", 0, True, False, 12),
])
def test_BaseRecordPackage_add_quotes(example_singular_tmc_chains,
            tc_type, sing_index, is_str, is_arr, final_NELM):
    record = BaseRecordPackage(example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_arr
    record.chain.last.is_str = is_str
    record.chain.last.iterable_length = final_NELM
    for element, idx in zip(record.chain.chain,range(len(record.chain.chain))):
        element.name = chr(97+idx)
    record.generate_naive_config()
    record.guess_all()
    for ln in record.cfg.config:
        print(ln)
    #print(record.cfg.config)
    record.add_quotes()
    #assert False
# PvPackage tests

@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_instantiation(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    #print(tmc.all_Symbols)
    #print(tmc.all_DataTypes)
    #print(tmc.all_SubItems)
    element_path = [
        tmc.all_Symbols['MAIN.test_iterator'],
        tmc.all_SubItems['iterator']['value']
    ]
    
    # ensure that you can instantiate w/o errors
    try:
        pv_pack = PvPackage(
            target_path = element_path,
            pragma = element_path[-1].config_by_pv[0],
            proto_name = '',
            proto_file_name = '',
        )
    except:
        pytest.fail()

    # ensure that the pragmas properly crossed over
    #print(tmc.all_SubItems['iterator']['value'].config_by_pv)
    assert pv_pack.pv_complete == "TEST:MAIN:ITERATOR:VALUE"
    assert {'title':'pv', 'tag':'VALUE'} in pv_pack.pragma
    

@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_from_element_path(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]

    pv_packs = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )

    assert len(pv_packs) == 2

    assert pv_packs[0].guessing_applied == False
    assert pv_packs[1].guessing_applied == False

    assert pv_packs[0].pv_partial == "TEST:MAIN:NEW_VAR_OUT"
    assert pv_packs[1].pv_partial == "TEST:MAIN:NEW_VAR_IN"

    assert pv_packs[0].pv_complete == "TEST:MAIN:NEW_VAR_OUT"
    assert pv_packs[1].pv_complete == "TEST:MAIN:NEW_VAR_IN"

    assert pv_packs[0].proto_name == "SetNEW_VAR"
    assert pv_packs[1].proto_name == "GetNEW_VAR"


@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_make_config(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, pv_in = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )
    new = pv_out.make_config(title="test_line", setting="test", field=False)
    assert {'title': 'test_line', 'tag': 'test'} == new 

    new = pv_out.make_config(title="FLD", setting="test 9", field=True)
    assert {
        'title': 'field',
        'tag': {'f_name': "FLD", 'f_set': 'test 9'}
    } == new 


@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_missing_pragma_lines(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, pv_in = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )
    ''' 
    for x in pv_out.pragma:
        print(x)
    '''
    missing = pv_out.missing_pragma_lines()
    
    assert odict([('field',['title']),('DTYP',['tag','f_name'])]) in missing
    assert odict([('field',['title']),('INP',['tag','f_name'])]) in missing
    
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'DTYP', 'f_set': ''}}
    )
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'INP', 'f_set': ''}}
    )
    
    assert [] == pv_out.missing_pragma_lines()


@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_is_config_complete(generic_tmc_path):
    '''Test a single version for pragma completeness. This only tests for the
    existance of these fields, it does NOT test if they are valid.
    '''
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, pv_in = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )
    '''
    for x in pv_out.pragma:
        print(x)
    '''

    assert False == pv_out.is_config_complete
    
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'DTYP', 'f_set': ''}}
    )
    pv_out.pragma.append(
        {'title': 'field', 'tag': {'f_name': 'INP', 'f_set': ''}}
    )
    
    assert True == pv_out.is_config_complete


@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_term_exists(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, _ = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )

    # confirm that the 'pv' field exists, rule 0
    assert pv_out.term_exists(pv_out.req_fields[0]) == True
    # confirm that the 'INP field does not exist, rule 6
    assert pv_out.term_exists(pv_out.req_fields[6]) == False


# PvPackage field guessing tests

@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPacakge_guess(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]
    pv_out, _ = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
    )


@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_guess():
    ''
    assert pv_packs[0].fields == {
        "ZNAM":"SINGLE",
        "ONAM":"MULTI",
        "SCAN":"1 second"
    }
    assert pv_packs[1].fields == {
        "ZNAM":"SINGLE",
        "ONAM":"MULTI",
        "SCAN":"1 second"
    }


@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_create_record(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]

    pv_packs = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
        use_proto = True,
    )

    print(element_path)
    record0 = pv_packs[0].create_record()
    assert record0.pv == "TEST:MAIN:NEW_VAR_OUT"
    assert record0.rec_type == "bo"
    assert record0.fields == {
        "ZNAM":"SINGLE",
        "ONAM":"MULTI",
        "SCAN":"1 second"
    }
    assert record0.comment


@pytest.mark.skip(reason="PvPackage pending deprecation")
def test_PvPackage_create_proto(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    element_path = [
        tmc.all_Symbols['MAIN.NEW_VAR'],
    ]

    pv_packs = PvPackage.from_element_path(
        target_path = element_path,
        base_proto_name = 'NEW_VAR',
        proto_file_name = '',
        use_proto = True,
    )

    proto0 = pv_packs[0].create_proto()
    '''
    assert proto0.name
    assert proto0.out_field
    assert proto0.in_field
    assert proto0.init
    '''

