import logging
import textwrap

import pytest

from pytmc import Symbol, DataType, epics
from pytmc.xml_obj import BaseElement, Configuration

from pytmc import TmcFile
from pytmc.xml_collector import (ElementCollector, TmcChain, BaseRecordPackage,
                                 ChainNotSingularError,
                                 TwincatTypeRecordPackage,
                                 BinaryRecordPackage,
                                 IntegerRecordPackage,
                                 EnumRecordPackage,
                                 FloatRecordPackage,
                                 WaveformRecordPackage,
                                 StringRecordPackage)

from collections import defaultdict, OrderedDict as odict

from . import conftest

logger = logging.getLogger(__name__)

# ElementCollector tests


def test_ElementCollector_instantiation(generic_tmc_root):
    try:
        col = ElementCollector()
    except Exception:
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
    except Exception:
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

    assert tmc.all_Symbols['MAIN.dtype_samples_enum'].is_enum
    assert tmc.all_SubItems['DUT_CONTAINER']['dtype_enum'].is_enum


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


def test_TmcFile_resolve_enums(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    tmc.isolate_Symbols()
    tmc.isolate_DataTypes()
    assert not tmc.all_Symbols['MAIN.dtype_samples_enum'].is_enum
    assert not tmc.all_SubItems['DUT_CONTAINER']['dtype_enum'].is_enum
    tmc.resolve_enums()
    assert tmc.all_Symbols['MAIN.dtype_samples_enum'].is_enum
    assert tmc.all_SubItems['DUT_CONTAINER']['dtype_enum'].is_enum


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


def test_TmcFile_create_packages(example_singular_tmc_chains):
    tmc = TmcFile(None)
    check_list = []
    # build artificial tmcChains and generate fake names
    for idx, tc_type in zip([0, 2, 4, 6], ["BOOL", "INT", "LREAL", "STRING"]):
        cn = example_singular_tmc_chains[idx]
        for element, ix in zip(cn.chain, range(len(cn.chain))):
            element.name = chr(97+ix)

        cn.last.tc_type = tc_type

        tmc.all_TmcChains.append(cn)

        # create the check_set
        rec = BaseRecordPackage(851, cn)
        logger.debug(str(rec.chain.last.pragma.config))
        check_list.append(rec)

    tmc.create_chains()
    logger.debug("all_TmcChains: ")
    for x in tmc.all_TmcChains:
        logger.debug(x)
    tmc.isolate_chains()
    logger.debug("all_singular_TmcChains: ")
    for x in tmc.all_singular_TmcChains:
        logger.debug(x)
    tmc.create_packages()
    logger.debug("all_RecordPackages: ")
    for x in tmc.all_RecordPackages:
        logger.debug(x.chain.name_list)

    assert len(tmc.all_RecordPackages) == 4
    for check, rec in zip(check_list, tmc.all_RecordPackages):
        assert check.cfg.config == rec.cfg.config
        assert check.chain.chain == rec.chain.chain


def test_TmcFile_configure_packages(example_singular_tmc_chains):
    tmc = TmcFile(None)
    check_list = []
    # build artificial tmcChains and generate fake names
    for idx, tc_type in zip([0, 2, 4, 6], ["BOOL", "INT", "LREAL", "STRING"]):
        cn = example_singular_tmc_chains[idx]
        for element, ix in zip(cn.chain, range(len(cn.chain))):
            element.name = chr(97+ix)

        cn.last.tc_type = tc_type

        tmc.all_TmcChains.append(cn)

        # create the check_set
        rec = BaseRecordPackage(None, cn)
        rec.generate_naive_config()
        logger.debug(str(rec.chain.last.pragma.config))
        check_list.append(rec)

    tmc.create_chains()
    tmc.isolate_chains()
    tmc.create_packages()
    tmc.configure_packages()

    assert len(tmc.all_RecordPackages) == 4
    for check, rec in zip(check_list, tmc.all_RecordPackages):
        assert check.cfg.config == rec.cfg.config
        assert check.chain.chain == rec.chain.chain


def test_TmcFile_fullbuild(string_tmc_path):
    tmc = TmcFile(string_tmc_path)
    tmc.create_chains()
    tmc.isolate_chains()
    tmc.create_packages()
    tmc.configure_packages()
    z = tmc.render()
    print(z)

# How do we support custom record building?
@pytest.mark.xfail
def test_TmcFile_render(generic_tmc_path):
    tmc = TmcFile(None)
    brp1 = BaseRecordPackage(851)
    brp1.cfg.add_config_line('pv', 'example_pv')
    brp1.cfg.add_config_line('type', 'ao')
    brp1.cfg.add_config_field("DTYP", '"MyDTYP"')
    brp1.cfg.add_config_field("PINI", '"VX"')
    brp1.cfg.add_config_field("NELM", '"3"')
    brp1.cfg.add_config_field('ABC', '"test 0"')
    brp2 = BaseRecordPackage(851)
    brp2.cfg.add_config_line('pv', 'example_pv2')
    brp2.cfg.add_config_line('type', 'bi')
    brp2.cfg.add_config_field("DTYP", '"MyDTYP"')
    brp2.cfg.add_config_field("PINI", '"1"')
    brp2.cfg.add_config_field("NELM", '"2"')
    brp2.cfg.add_config_field('ABC', '"test k"')

    tmc.all_RecordPackages.append(brp1)
    tmc.all_RecordPackages.append(brp2)

    target_response = """\
    record(ao,"example_pv"){
      field(DTYP, "MyDTYP")
      field(PINI, "VX")
      field(NELM, "3")
      field(ABC, "test 0")
    }

    record(bi,"example_pv2"){
      field(DTYP, "MyDTYP")
      field(PINI, "1")
      field(NELM, "2")
      field(ABC, "test k")
    }

    """
    target_response = textwrap.dedent(target_response)
    assert target_response == tmc.render()


def test_TmcFile_ads_port(tmc_filename):
    tmc = TmcFile(tmc_filename)
    assert tmc.ads_port == 851


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
    assert chain.is_singular() is False

    for element in chain.chain:
        element.pragma.fix_to_config_name(element.pragma.config_names()[0])

    # for element in chain.chain:
        # print(element.pragma.config)

    assert chain.is_singular() is True


def test_TmcChain_recursive_permute():
    l = [['a'], ['b', 'c', 'd'], ['e', 'f']]
    chain = TmcChain(None)
    result = chain._recursive_permute(l)
    for s in result:
        print(s)
    assert result == [
        [['a'], ['b'], ['e']],
        [['a'], ['c'], ['e']],
        [['a'], ['d'], ['e']],
        [['a'], ['b'], ['f']],
        [['a'], ['c'], ['f']],
        [['a'], ['d'], ['f']],
    ]


@pytest.mark.parametrize("use_base_pragma, answer_set", [
    (False, 0),
    (True, 1),
])
def test_TmcChain_build_singular_chains(
        use_base_pragma, generic_tmc_path, answer_set, leaf_bool_pragma_string,
        branch_bool_pragma_string, branch_connection_pragma_string):
    stem = BaseElement(element=None)
    if use_base_pragma:
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
    for x in response_set:
        logger.debug(str(x.forkmap()))
        assert x.is_singular()

    for x in response_set:
        for y in response_set:
            if x is y:
                continue
            if x == y:
                assert False

    if answer_set is 0:
        assert response_set == []

    if answer_set is 1:
        assert len(response_set) == 4
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
        {'title': 'pv', 'tag': 'MIDDLE:FIRST:TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'aux', 'tag': 'nothing'},
        {'title': 'type', 'tag': 'bo'},
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
    test_chain.last.tc_type = 'BOOL'
    brp = BaseRecordPackage(851, test_chain)
    brp.generate_naive_config()
    assert brp.cfg.config[0:3] == [
        {'title': 'pv', 'tag': 'MIDDLE:FIRST:TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'aux', 'tag': 'nothing'},
        {'title': 'type', 'tag': 'bo'},
    ]


def test_BaseRecordPackage_apply_config_valid(sample_TmcChain):
    test_chain = sample_TmcChain.build_singular_chains()[0]
    brp = TwincatTypeRecordPackage(851, test_chain)
    brp.generate_naive_config()
    for x in brp.cfg.config:
        print(x)

    brp.validation_list = [
        {'path': [], 'target':3},
    ]
    assert brp.apply_config_validation() == [
        {'path': [], 'target':3},
    ]

    brp.validation_list = [
        {'path': ['tag', 'f_name'], 'target':'SCAN'},
        {'path': ['title'], 'target':'pv'},
    ]
    assert len(brp.apply_config_validation()) == 0


def test_BaseRecordPackage_cfg_as_dict():
    brp = TwincatTypeRecordPackage(851)
    brp.cfg.add_config_line('pv', 'example_pv')
    brp.cfg.add_config_line('type', 'ao')
    brp.cfg.add_config_field('ABC', 'test 0')
    assert brp.cfg_as_dict() == {
        'pv': 'example_pv',
        'type': 'ao',
        'field': {
            'ABC': '"test 0"'
        }
    }


# How do we support custom record building!
@pytest.mark.xfail
def test_BaseRecordPackage_render_record():
    brp = TwincatTypeRecordPackage(851)
    brp.cfg.add_config_line('pv', 'example_pv')
    brp.cfg.add_config_line('type', 'ao')
    brp.cfg.add_config_field('DTYP', '"MyDTYP"')
    brp.cfg.add_config_field("PINI", '"1"')
    brp.cfg.add_config_field("NELM", 3)
    brp.cfg.add_config_field('ABC', '"test 0"')
    target_response = """\
    record(ao,"example_pv"){
      field(DTYP, "MyDTYP")
      field(PINI, "1")
      field(NELM, "3")
      field(ABC, "test 0")
    }\
    """
    target_response = textwrap.dedent(target_response).strip()
    assert target_response == brp.render_record()


def test_BaseRecordPackage_PINI():
    brp = TwincatTypeRecordPackage(851)
    assert brp.field_defaults['PINI'] == 1


def test_BaseRecordPackage_guess_TSE():
    brp = TwincatTypeRecordPackage(851)
    assert brp.field_defaults['TSE'] == -2


@pytest.mark.parametrize("tc_type, is_array, final_type", [
    ("BOOL", False, BinaryRecordPackage),
    ("BOOL", True, WaveformRecordPackage),
    ("INT", False, IntegerRecordPackage),
    ("INT", True, WaveformRecordPackage),
    ("DINT", False, IntegerRecordPackage),
    ("DINT", True, WaveformRecordPackage),
    ("ENUM", False, EnumRecordPackage),
    ("ENUM", True, WaveformRecordPackage),
    ("REAL", False, FloatRecordPackage),
    ("REAL", True, WaveformRecordPackage),
    ("LREAL", False, FloatRecordPackage),
    ("LREAL",  True, WaveformRecordPackage),
    ("STRING", False, StringRecordPackage),
])
def test_BaseRecordPackage_guess_type(example_singular_tmc_chains,
                                      tc_type, is_array, final_type):
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    chain = example_singular_tmc_chains[0]
    chain.last.is_array = is_array
    chain.last.tc_type = tc_type
    record = BaseRecordPackage(851, chain)
    logger.debug(str(record.chain.last.pragma.config))
    record.generate_naive_config()
    assert isinstance(record, final_type)




# If no I/O is given in the pragma we no longer assume that this value is an io
# field!
@pytest.mark.xfail
@pytest.mark.parametrize("tc_type, sing_index, final_io", [
    ("BOOL", 6, 'io'),
    ("INT", 6, 'io'),
    ("LREAL", 6, 'io'),
    ("STRING", 6, 'io'),
])
def test_BaseRecordPackage_guess_io(example_singular_tmc_chains,
                                    tc_type, sing_index, final_io):
    # chain must be broken into singular
    chain = example_singular_tmc_chains[sing_index]
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    chain.last.tc_type = tc_type
    record = BaseRecordPackage(851, chain)
    logger.debug(str(record.chain.last.pragma.config))
    record.generate_naive_config()
    print(record.cfg.config)
    [field] = record.cfg.get_config_lines('io')
    assert field['tag'] == final_io
    assert record.io_direction == 'output'


@pytest.mark.parametrize("tc_type, io, is_array, final_DTYP", [
    # BOOl
    ("BOOL", 'i', False, '"asynInt32"'),
    ("BOOL", 'io', False, '"asynInt32"'),
    ("BOOL", 'i', True, '"asynInt8ArrayIn"'),
    ("BOOL", 'io', True, '"asynInt8ArrayOut"'),
    # INT
    ("INT", 'i', False, '"asynInt32"'),
    ("INT", 'io', False, '"asynInt32"'),
    ("INT", 'i', True, '"asynInt16ArrayIn"'),
    ("INT", 'io', True, '"asynInt16ArrayOut"'),
    # DINT
    ("DINT", 'i', False, '"asynInt32"'),
    ("DINT", 'io', False, '"asynInt32"'),
    ("DINT", 'i', True, '"asynInt32ArrayIn"'),
    ("DINT", 'io', True, '"asynInt32ArrayOut"'),
    # REAL
    ("REAL", 'i', False, '"asynFloat64"'),
    ("REAL", 'io', False, '"asynFloat64"'),
    ("REAL", 'i', True, '"asynFloat32ArrayIn"'),
    ("REAL", 'io', True, '"asynFloat32ArrayOut"'),
    # LREAL
    ("LREAL", 'i', False, '"asynFloat64"'),
    ("LREAL", 'io', False, '"asynFloat64"'),
    ("LREAL", 'i', True, '"asynFloat64ArrayIn"'),
    ("LREAL", 'io', True, '"asynFloat64ArrayOut"'),
    # ENUM
    ("ENUM", 'i', False, '"asynInt32"'),
    ("ENUM", 'io', False, '"asynInt32"'),
    ("ENUM", 'i', True, '"asynInt16ArrayIn"'),
    ("ENUM", 'io', True, '"asynInt16ArrayOut"'),
    # String
    ("STRING", 'i', False, '"asynOctetRead"'),
    ("STRING", 'io', False, '"asynOctetWrite"'),
])
def test_BaseRecordPackage_guess_DTYP(example_singular_tmc_chains,
                                      tc_type, io, is_array, final_DTYP):
    # chain must be broken into singular
    chain = example_singular_tmc_chains[0]
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    chain.last.is_array = is_array
    chain.last.iterable_length = 3
    chain.last.tc_type = tc_type
    record = BaseRecordPackage(851, chain)
    logger.debug((record.chain.last.pragma.config))
    record.generate_naive_config()
    logger.debug((record.cfg.config))
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    record.cfg.add_config_line('io', io, overwrite=True)
    # If we are checking an input type check the first record
    if record.io_direction == 'input':
        record.records[0].fields['DTYP'] == final_DTYP
    # Otherwise check the output records
    else:
        record.records[1].fields['DTYP'] == final_DTYP

@pytest.mark.parametrize("tc_type, sing_index, field_type, final_INP_OUT", [
    ("BOOL",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
    ("BOOL",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
    ("BYTE",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
    ("BYTE",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
    ("SINT",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="',),
    ("SINT",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"',),
    ("USINT",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
    ("USINT",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
    ("WORD",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
    ("WORD",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
    ("INT",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="',),
    ("INT",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"',),
    ("UINT",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
    ("UINT",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
    ("DWORD",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
    ("DWORD",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
    ("DINT",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="',),
    ("DINT",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"',),
    ("UDINT",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="'),
    ("UDINT",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"'),
    ("LREAL",  0, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="',),
    ("LREAL",  2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"',),
    ("STRING", 2, "INP", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c?"',),
    ("STRING", 6, "OUT", '"@asyn($(PORT),0,1)ADSPORT=851/a.b.c="',),
])
def test_BaseRecordPackage_guess_INP_OUT(example_singular_tmc_chains, dbd_file,
                                         tc_type, sing_index, field_type, final_INP_OUT):
    # chain must be broken into singular
    chain = example_singular_tmc_chains[0]
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    chain.last.tc_type = tc_type
    chain.last.is_array = False
    if tc_type == "STRING":
        chain.last.is_str = True

    record = BaseRecordPackage(851, chain)
    record.cfg.add_config_line('io', 'io', overwrite=True)
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    record.generate_naive_config()
    if tc_type == "STRING":
        if field_type == "OUT":
            assert record.records[1].fields.get("INP") == final_INP_OUT
        else:
            assert record.records[0].fields.get("INP") == final_INP_OUT
    else:
        if field_type == "OUT":
            assert record.records[1].fields.get('INP') is None
            assert record.records[1].fields.get('OUT') == final_INP_OUT
        if field_type == "INP":
            assert record.records[0].fields.get('OUT') is None
            assert record.records[0].fields.get('INP') == final_INP_OUT

    conftest.lint_record(dbd_file, record)


# All input records should have SCAN = Passive
@pytest.mark.parametrize("tc_type, sing_index", [
    ("BOOL", 0),
    ("BOOL", 2),
    ("BOOL", 6),
    ("INT", 0),
    ("INT", 2),
    ("INT", 6),
    ("LREAL", 0),
    ("LREAL", 2),
    ("LREAL", 6),
    ("STRING", 0),
    ("STRING", 2),
    ("STRING", 6),
])
def test_BaseRecordPackage_guess_SCAN(example_singular_tmc_chains,
                                      tc_type, sing_index):
    # chain must be broken into singular
    chain = example_singular_tmc_chains[0]
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    chain.last.tc_type = tc_type
    record = BaseRecordPackage(851, chain)
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    record.generate_naive_config()
    record.cfg.add_config_line('io', 'io', overwrite=True)
    logger.debug((record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    logger.debug(str(record.cfg.config))
    assert record.records[0].fields.get('SCAN') == '"I/O Intr"'
    assert record.records[1].fields.get('SCAN') is None


@pytest.mark.parametrize("tc_type, sing_index, final_ZNAM, final_ONAM, ret", [
    ("BOOL", 0, '"Zero"', '"One"', True),
    ("STRING", 0, None, None, False),
])
def test_BaseRecordPackage_guess_OZ_NAM(example_singular_tmc_chains,
                                        tc_type, sing_index, final_ZNAM, final_ONAM, ret):
    chain = example_singular_tmc_chains[sing_index]
    chain.last.tc_type = tc_type
    record = BaseRecordPackage(851, chain)
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    for rec in record.records:
        assert rec.fields.get('ZNAM') == final_ZNAM
        assert rec.fields.get('ONAM') == final_ONAM


@pytest.mark.parametrize("tc_type, sing_index, final_PREC, ret", [
    ("LREAL", 0, '"3"', True),
    ("STRING", 0, None, False),
])
def test_BaseRecordPackage_guess_PREC(example_singular_tmc_chains,
                                      tc_type, sing_index, final_PREC, ret):
    chain = example_singular_tmc_chains[sing_index]
    chain.last.tc_type = tc_type
    record = BaseRecordPackage(851, chain)
    record.generate_naive_config()
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    print(record.cfg.config)
    for rec in record.records:
        assert rec.fields.get('PREC') == final_PREC


@pytest.mark.parametrize("tc_type, io, is_str, is_arr, final_FTVL", [
    ("INT", 'o', False, False, None),
    pytest.param(
        "INT", 'o', False, True, '"FINISH"',
        marks=pytest.mark.skip(reason="feature pending")),
    ("BOOL", 'i', False, False, None),
    ("BOOL", 'i', False, True, '"CHAR"'),
    ("BOOL", 'o', False, True, '"CHAR"'),
    ("BOOL", 'io', False, True, '"CHAR"'),
    ("INT", 'i', False, False, None),
    ("INT", 'i', False, True, '"SHORT"'),
    ("INT", 'o', False, True, '"SHORT"'),
    ("INT", 'io', False, True, '"SHORT"'),
    ("DINT", 'i', False, False, None),
    ("DINT", 'i', False, True, '"LONG"'),
    ("DINT", 'o', False, True, '"LONG"'),
    ("DINT", 'io', False, True, '"LONG"'),
    ("ENUM", 'i', False, False, None),
    ("ENUM", 'i', False, True, '"SHORT"'),
    ("ENUM", 'o', False, True, '"SHORT"'),
    ("ENUM", 'io', False, True, '"SHORT"'),
    ("REAL", 'i', False, False, None),
    ("REAL", 'i', False, True, '"FLOAT"'),
    ("REAL", 'o', False, True, '"FLOAT"'),
    ("REAL", 'io', False, True, '"FLOAT"'),
    ("LREAL", 'i', False, False, None),
    ("LREAL", 'i', False, True, '"DOUBLE"'),
    ("LREAL", 'o', False, True, '"DOUBLE"'),
    ("LREAL", 'io', False, True, '"DOUBLE"'),
    ("STRING", 'i', True, False, '"CHAR"'),
    ("STRING", 'o', True, False, '"CHAR"'),
    ("STRING", 'io', True, False, '"CHAR"'),
])
def test_BaseRecordPackage_guess_FTVL(example_singular_tmc_chains,
                                      tc_type, io, is_str, is_arr, final_FTVL,
                                      dbd_file):
    chain = example_singular_tmc_chains[0]
    chain.last.tc_type = tc_type
    chain.last.is_array = is_arr
    chain.last.is_str = is_str
    chain.last.iterable_length = 3
    record = BaseRecordPackage(851, chain)
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    record.generate_naive_config()
    record.cfg.add_config_line('io', io, overwrite=True)
    for rec in record.records:
        assert rec.fields.get('FTVL') == final_FTVL

    conftest.lint_record(dbd_file, record)


@pytest.mark.parametrize("tc_type, sing_index, is_str, is_arr, final_NELM", [
    ("INT", 0, False, False, None),
    ("INT", 0, False, True, '"3"'),
    ("LREAL", 0, False, True, '"9"'),
    ("STRING", 0, True, False, '"81"'),
])
def test_BaseRecordPackage_guess_NELM(example_singular_tmc_chains,
                                      tc_type, sing_index, is_str, is_arr, final_NELM):
    chain = example_singular_tmc_chains[sing_index]
    chain.last.tc_type = tc_type
    chain.last.is_array = is_arr
    chain.last.is_str = is_str
    chain.last.iterable_length = final_NELM
    record = BaseRecordPackage(851, chain)
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    record.generate_naive_config()
    for rec in record.records:
        assert rec.fields.get('NELM') == final_NELM


# Guess all is no longer a valid method
@pytest.mark.xfail
@pytest.mark.parametrize(
    "tc_type, sing_index, is_str, is_arr, final_NELM, spot_check, result", [
        ("INT", 6, False, False, None, "DTYP", '"asynInt32"'),
        ("INT", 2, False, False, None, "SCAN", '".5 second"'),
        ("LREAL", 2, False, False, None, "PREC", '"3"'),
        ("INT", 0, False, True, 3, "NELM", '"3"'),
        ("LREAL", 0, False, True, 9, "FTVL", '"DOUBLE"'),
        ("STRING", 0, True, False, 12, "FTVL", '"CHAR"'),
    ])
def test_BaseRecordPackage_guess_all(example_singular_tmc_chains, tc_type,
                                     sing_index, is_str, is_arr, final_NELM, spot_check, result):
    record = BaseRecordPackage(851, example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_arr
    record.chain.last.is_str = is_str
    record.chain.last.iterable_length = final_NELM
    for element, idx in zip(record.chain.chain, range(len(record.chain.chain))):
        element.name = chr(97+idx)
    record.generate_naive_config()
    record.guess_all()
    for ln in record.cfg.config:
        print(ln)
    [out] = record.cfg.get_config_fields(spot_check)
    assert out['tag']['f_set'] == result
