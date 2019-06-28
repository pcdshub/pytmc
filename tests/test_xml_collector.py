import logging
import textwrap
import types

import pytest

from pytmc import epics, parser, Configuration, pragmas

from pytmc.record import (RecordPackage, TwincatTypeRecordPackage,
                          BinaryRecordPackage, IntegerRecordPackage,
                          EnumRecordPackage, FloatRecordPackage,
                          WaveformRecordPackage, StringRecordPackage)

from . import conftest

logger = logging.getLogger(__name__)


@pytest.fixture(scope='function')
def chain():
    tmc = parser.parse(conftest.TMC_ROOT / 'xtes_sxr_plc.tmc')
    symbols = list(pragmas.find_pytmc_symbols(tmc))
    chain, configs = list(pragmas.chains_from_symbol(symbols[1]))[0]
    return pragmas.SingularChain(chain, configs)


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
    ("LREAL", True, WaveformRecordPackage),
    ("STRING", False, StringRecordPackage),
])
def test_record_package_from_chain(chain, tc_type, is_array, final_type):
    # tc_type is assignable because it isn't implemented in BaseElement
    # this field must be added because it is typically derived from the .tmc
    chain.last.is_array = is_array
    chain.last.type = tc_type
    record = RecordPackage.from_chain(851, chain=chain)
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
    chain.last.type = tc_type
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
    chain.last.type = tc_type
    record = BaseRecordPackage(851, chain)
    logger.debug((record.chain.last.pragma.config))
    record.generate_naive_config()
    logger.debug((record.cfg.config))
    for element, idx in zip(record.chain.chain, range(3)):
        element.name = chr(97+idx)
    record.cfg.add_config_line('io', io, overwrite=True)
    # If we are checking an input type check the first record
    if record.io_direction == 'input':
        assert record.records[0].fields['DTYP'] == final_DTYP
    # Otherwise check the output records
    else:
        assert record.records[1].fields['DTYP'] == final_DTYP

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
    chain.last.type = tc_type
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
    chain.last.type = tc_type
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
    chain.last.type = tc_type
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
    chain.last.type = tc_type
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
    chain.last.type = tc_type
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
    chain.last.type = tc_type
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
    record.chain.last.type = tc_type
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
