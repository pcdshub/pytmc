import logging
import textwrap

import pytest

from pytmc import Symbol, DataType
from pytmc.xml_obj import BaseElement, Configuration

from pytmc import TmcFile
from pytmc.xml_collector import ElementCollector, TmcChain, BaseRecordPackage
from pytmc.xml_collector import ChainNotSingularError

from collections import defaultdict, OrderedDict as odict

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
        # rec.naive_config()
        # rec.guess_all()
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
        rec.guess_all()
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


def test_TmcFile_render(generic_tmc_path):
    tmc = TmcFile(None)
    brp1 = BaseRecordPackage(851)
    brp1.cfg.add_config_line('pv', 'example_pv')
    brp1.cfg.add_config_line('type', 'ao')
    brp1.cfg.add_config_field("DTYP", '"MyDTYP"')
    brp1.cfg.add_config_field("PINI", '"VX"')
    brp1.cfg.add_config_field("NELM", 3)
    brp1.cfg.add_config_field('ABC', '"test 0"')
    brp2 = BaseRecordPackage(851)
    brp2.cfg.add_config_line('pv', 'example_pv2')
    brp2.cfg.add_config_line('type', 'bi')
    brp2.cfg.add_config_field("DTYP", '"MyDTYP"')
    brp2.cfg.add_config_field("PINI", '"1"')
    brp2.cfg.add_config_field("NELM", 2)
    brp2.cfg.add_config_field('ABC', '"test k"')

    tmc.all_RecordPackages.append(brp1)
    tmc.all_RecordPackages.append(brp2)

    target_response = """\
    record(ao,"example_pv"){
      field(DTYP, "MyDTYP")
      field(PINI, "VX")
      field(NELM, 3)
      field(ABC, "test 0")
    }

    record(bi,"example_pv2"){
      field(DTYP, "MyDTYP")
      field(PINI, "1")
      field(NELM, 2)
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
    brp = BaseRecordPackage(851, test_chain)
    brp.generate_naive_config()
    assert brp.cfg.config[0:3] == [
        {'title': 'pv', 'tag': 'MIDDLE:FIRST:TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'aux', 'tag': 'nothing'},
        {'title': 'type', 'tag': 'bo'},
    ]


def test_BaseRecordPackage_apply_config_valid(sample_TmcChain):
    test_chain = sample_TmcChain.build_singular_chains()[0]
    brp = BaseRecordPackage(851, test_chain)
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
    brp = BaseRecordPackage(851)
    brp.cfg.add_config_line('pv', 'example_pv')
    brp.cfg.add_config_line('type', 'ao')
    brp.cfg.add_config_field('ABC', 'test 0')
    assert brp.cfg_as_dict() == {
        'pv': 'example_pv',
        'type': 'ao',
        'info': False,
        'field': {
            'ABC': 'test 0'
        }
    }


def test_BaseRecordPackage_render_record():
    brp = BaseRecordPackage(851)
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
      field(NELM, 3)
      field(ABC, "test 0")
    }\
    """
    target_response = textwrap.dedent(target_response).strip()
    assert target_response == brp.render_record()


@pytest.mark.skip(reason="Feature pending")
def test_BaseRecordPackage_ID_type():
    brp = BaseRecordPackage(851)
    brp.cfg.add_config_line('pv', 'example_pv')
    brp.cfg.add_config_line('type', 'ao')
    brp.cfg.add_config_field("PINI", "1")
    assert brp.ID_type() == 'standard'

    brp = BaseRecordPackage(851)
    brp.cfg.add_config_line('pv', 'example_pv')
    brp.cfg.add_config_line('type', 'motor')
    brp.cfg.add_config_field("PINI", "1")
    assert brp.ID_type() == 'motor'


def test_BaseRecordPackage_guess_PINI():
    brp = BaseRecordPackage(851)
    assert brp.guess_PINI() is True
    print(brp.cfg.config)
    [pini] = brp.cfg.get_config_fields('PINI')
    assert pini['tag']['f_set'] == '"1"'


def test_BaseRecordPackage_guess_TSE():
    brp = BaseRecordPackage(851)
    assert brp.guess_TSE() is True
    [tse] = brp.cfg.get_config_fields('TSE')
    assert tse['tag']['f_set'] == '-2'


@pytest.mark.parametrize("tc_type, io, is_array, final_type", [
    ("BOOL", "i", False, 'bi'),
    ("BOOL", "o", False, 'bo'),
    ("BOOL", "io", False, 'bo'),
    ("BOOL", "i", True, 'waveform'),
    ("BOOL", "o", True, 'waveform'),
    ("BOOL", "io", True, 'waveform'),
    ("INT", "i", False, 'ai'),
    ("INT", "o", False, 'ao'),
    ("INT", "io", False, 'ao'),
    ("INT", "i", True, 'waveform'),
    ("INT", "o", True, 'waveform'),
    ("INT", "io", True, 'waveform'),
    ("DINT", "i", False, 'ai'),
    ("DINT", "o", False, 'ao'),
    ("DINT", "io", False, 'ao'),
    ("DINT", "i", True, 'waveform'),
    ("DINT", "o", True, 'waveform'),
    ("DINT", "io", True, 'waveform'),
    ("ENUM", "i", False, 'ai'),
    ("ENUM", "o", False, 'ao'),
    ("ENUM", "io", False, 'ao'),
    ("ENUM", "i", True, 'waveform'),
    ("ENUM", "o", True, 'waveform'),
    ("ENUM", "io", True, 'waveform'),
    ("REAL", "i", False, 'ai'),
    ("REAL", "o", False, 'ao'),
    ("REAL", "io", False, 'ao'),
    ("REAL", "i", True, 'waveform'),
    ("REAL", "o", True, 'waveform'),
    ("REAL", "io", True, 'waveform'),
    ("LREAL", "i", False, 'ai'),
    ("LREAL", "o", False, 'ao'),
    ("LREAL", "io", False, 'ao'),
    ("LREAL", "i", True, 'waveform'),
    ("LREAL", "o", True, 'waveform'),
    ("LREAL", "io", True, 'waveform'),
    ("STRING", "i", False, 'waveform'),
    ("STRING", "o", False, 'waveform'),
    ("STRING", "io", False, 'waveform'),
    #("INT", 2, 'ai'),
    #("INT", 0, 'ao'),
    #("INT", 4, 'ao'),
    #("LREAL", 2, 'ai'),
    #("LREAL", 0, 'ao'),
    #("LREAL", 4, 'ao'),
    #("STRING", 2, 'waveform'),
    #("STRING", 0, 'waveform'),
    #("STRING", 4, 'waveform'),
])
def test_BaseRecordPackage_guess_type(example_singular_tmc_chains,
                                      tc_type, io, is_array, final_type):
    # chain must be broken into singular
    # for x in example_singular_tmc_chains:
    #     z = BaseRecordPackage(x)
    #     print(z.cfg.config)
    #     z.generate_naive_config()
    #     print(z.cfg.config)
    # assert False
    record = BaseRecordPackage(851, example_singular_tmc_chains[0])
    logger.debug(str(record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_array
    record.generate_naive_config()
    record.cfg.add_config_line('io', io, overwrite=True)

    assert record.guess_type() is True
    [field] = record.cfg.get_config_lines('type')
    assert field['tag'] == final_type


@pytest.mark.parametrize("tc_type, sing_index, final_io", [
    ("BOOL", 6, 'io'),
    ("INT", 6, 'io'),
    ("LREAL", 6, 'io'),
    ("STRING", 6, 'io'),
])
def test_BaseRecordPackage_guess_io(example_singular_tmc_chains,
                                    tc_type, sing_index, final_io):
    # chain must be broken into singular
    record = BaseRecordPackage(851, example_singular_tmc_chains[sing_index])
    logger.debug(str(record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    assert record.guess_io() is True
    print(record.cfg.config)
    [field] = record.cfg.get_config_lines('io')
    assert field['tag'] == final_io


@pytest.mark.parametrize("tc_type, io, is_array, final_DTYP", [
    # BOOl
    ("BOOL", 'i', False, '"asynInt32"'),
    ("BOOL", 'o', False, '"asynInt32"'),
    ("BOOL", 'io', False, '"asynInt32"'),
    ("BOOL", 'i', True, '"asynInt8ArrayIn"'),
    ("BOOL", 'o', True, '"asynInt8ArrayOut"'),
    ("BOOL", 'io', True, '"asynInt8ArrayOut"'),
    # INT
    ("INT", 'i', False, '"asynInt32"'),
    ("INT", 'o', False, '"asynInt32"'),
    ("INT", 'io', False, '"asynInt32"'),
    ("INT", 'i', True, '"asynInt16ArrayIn"'),
    ("INT", 'o', True, '"asynInt16ArrayOut"'),
    ("INT", 'io', True, '"asynInt16ArrayOut"'),
    # DINT
    ("DINT", 'i', False, '"asynInt32"'),
    ("DINT", 'o', False, '"asynInt32"'),
    ("DINT", 'io', False, '"asynInt32"'),
    ("DINT", 'i', True, '"asynInt32ArrayIn"'),
    ("DINT", 'o', True, '"asynInt32ArrayOut"'),
    ("DINT", 'io', True, '"asynInt32ArrayOut"'),
    # REAL
    ("REAL", 'i', False, '"asynFloat64"'),
    ("REAL", 'o', False, '"asynFloat64"'),
    ("REAL", 'io', False, '"asynFloat64"'),
    ("REAL", 'i', True, '"asynFloat32ArrayIn"'),
    ("REAL", 'o', True, '"asynFloat32ArrayOut"'),
    ("REAL", 'io', True, '"asynFloat32ArrayOut"'),
    # LREAL
    ("LREAL", 'i', False, '"asynFloat64"'),
    ("LREAL", 'o', False, '"asynFloat64"'),
    ("LREAL", 'io', False, '"asynFloat64"'),
    ("LREAL", 'i', True, '"asynFloat64ArrayIn"'),
    ("LREAL", 'o', True, '"asynFloat64ArrayOut"'),
    ("LREAL", 'io', True, '"asynFloat64ArrayOut"'),
    # ENUM
    ("ENUM", 'i', False, '"asynInt32"'),
    ("ENUM", 'o', False, '"asynInt32"'),
    ("ENUM", 'io', False, '"asynInt32"'),
    ("ENUM", 'i', True, '"asynInt16ArrayIn"'),
    ("ENUM", 'o', True, '"asynInt16ArrayOut"'),
    ("ENUM", 'io', True, '"asynInt16ArrayOut"'),
    # String
    ("STRING", 'i', False, '"asynInt8ArrayIn"'),
    ("STRING", 'o', False, '"asynInt8ArrayOut"'),
    ("STRING", 'io', False, '"asynInt8ArrayOut"'),
])
def test_BaseRecordPackage_guess_DTYP(example_singular_tmc_chains,
                                      tc_type, io, is_array, final_DTYP):
    # chain must be broken into singular
    record = BaseRecordPackage(851, example_singular_tmc_chains[0])
    logger.debug((record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_array
    record.generate_naive_config()
    record.cfg.add_config_line('io', io, overwrite=True)
    assert record.guess_DTYP() is True
    logger.debug((record.cfg.config))
    [field] = record.cfg.get_config_fields('DTYP')
    assert field['tag']['f_set'] == final_DTYP


@pytest.mark.parametrize("tc_type, sing_index, field_type, final_INP_OUT", [
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
    record = BaseRecordPackage(851, example_singular_tmc_chains[sing_index])
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    if tc_type == "STRING":
        record.chain.last.is_str = True
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    record.generate_naive_config()
    record.guess_io()
    assert record.guess_INP_OUT() is True
    print(record.cfg.config)

    [field] = record.cfg.get_config_fields(field_type)
    if field_type == "OUT":
        assert record.cfg.get_config_fields('INP') == []
    if field_type == "INP":
        assert record.cfg.get_config_fields('OUT') == []

    assert field['tag']['f_set'] == final_INP_OUT


@pytest.mark.parametrize("tc_type, sing_index, final_SCAN", [
    ("BOOL", 0, '"Passive"'),
    ("BOOL", 2, '"I/O Intr"'),
    ("BOOL", 6, '"Passive"'),
    ("INT", 0, '"Passive"'),
    ("INT", 2, '".5 second"'),
    ("INT", 6, '"Passive"'),
    ("LREAL", 0, '"Passive"'),
    ("LREAL", 2, '".5 second"'),
    ("LREAL", 6, '"Passive"'),
    ("STRING", 0, '"Passive"'),
    ("STRING", 2, '".5 second"'),
    ("STRING", 6, '"Passive"'),
])
def test_BaseRecordPackage_guess_SCAN(example_singular_tmc_chains,
                                      tc_type, sing_index, final_SCAN):
    record = BaseRecordPackage(851, example_singular_tmc_chains[sing_index])
    logger.debug((record.chain.last.pragma.config))
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    record.guess_io()
    assert record.guess_SCAN() is True
    logger.debug(str(record.cfg.config))
    [field] = record.cfg.get_config_fields('SCAN')
    assert field['tag']['f_set'] == final_SCAN


@pytest.mark.parametrize("tc_type, sing_index, final_ZNAM, final_ONAM, ret", [
    ("BOOL", 0, 'Zero', "One", True),
    ("STRING", 0, None, None, False),
])
def test_BaseRecordPackage_guess_OZ_NAM(example_singular_tmc_chains,
                                        tc_type, sing_index, final_ZNAM, final_ONAM, ret):
    record = BaseRecordPackage(851, example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    assert ret == record.guess_ONAM()
    assert ret == record.guess_ZNAM()
    o = record.cfg.get_config_fields('ONAM')
    z = record.cfg.get_config_fields('ZNAM')
    logger.debug(str(record.cfg.config))
    if final_ONAM is not None:
        assert o[0]['tag']['f_set'] == final_ONAM
    else:
        assert len(o) == 0
    if final_ZNAM is not None:
        assert z[0]['tag']['f_set'] == final_ZNAM
    else:
        assert len(z) == 0


@pytest.mark.parametrize("tc_type, sing_index, final_PREC, ret", [
    ("LREAL", 0, '"3"', True),
    ("STRING", 0, None, False),
])
def test_BaseRecordPackage_guess_PREC(example_singular_tmc_chains,
                                      tc_type, sing_index, final_PREC, ret):
    record = BaseRecordPackage(851, example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    record.generate_naive_config()
    print(record.cfg.config)
    record.guess_type()
    if final_PREC is None:
        assert record.guess_PREC() is False
        with pytest.raises(ValueError):
            [out] = record.cfg.get_config_fields("PREC")
    else:
        assert record.guess_PREC() is True
        [out] = record.cfg.get_config_fields("PREC")
        assert out['tag']['f_set'] == '"3"'


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
                                      tc_type, io, is_str, is_arr, final_FTVL):
    record = BaseRecordPackage(851, example_singular_tmc_chains[0])
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_arr
    record.chain.last.is_str = is_str
    record.generate_naive_config()
    record.cfg.add_config_line('io', io, overwrite=True)
    result = record.guess_FTVL()
    print(record.cfg.config)
    if final_FTVL is None:
        assert result is False
        with pytest.raises(ValueError):
            [out] = record.cfg.get_config_fields("FTVL")
    else:
        assert result is True
        [out] = record.cfg.get_config_fields("FTVL")
        assert out['tag']['f_set'] == final_FTVL


@pytest.mark.parametrize("tc_type, sing_index, is_str, is_arr, final_NELM", [
    ("INT", 0, False, False, None),
    ("INT", 0, False, True, 3),
    ("LREAL", 0, False, True, 9),
    ("STRING", 0, True, False, 12),
])
def test_BaseRecordPackage_guess_NELM(example_singular_tmc_chains,
                                      tc_type, sing_index, is_str, is_arr, final_NELM):
    record = BaseRecordPackage(851, example_singular_tmc_chains[sing_index])
    record.chain.last.tc_type = tc_type
    record.chain.last.is_array = is_arr
    record.chain.last.is_str = is_str
    record.chain.last.iterable_length = final_NELM
    record.generate_naive_config()
    result = record.guess_NELM()
    print(record.cfg.config)
    if final_NELM is None:
        assert result is False
        with pytest.raises(ValueError):
            [out] = record.cfg.get_config_fields("NELM")
    else:
        assert result is True
        [out] = record.cfg.get_config_fields("NELM")
        assert out['tag']['f_set'] == final_NELM


@pytest.mark.parametrize(
    "tc_type, sing_index, is_str, is_arr, final_NELM, spot_check, result", [
        ("INT", 6, False, False, None, "DTYP", '"asynInt32"'),
        ("INT", 2, False, False, None, "SCAN", '".5 second"'),
        ("LREAL", 2, False, False, None, "PREC", '"3"'),
        ("INT", 0, False, True, 3, "NELM", 3),
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
