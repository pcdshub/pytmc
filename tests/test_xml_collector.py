import logging
import types

import pytest

from pytmc import parser, pragmas

from pytmc.record import (RecordPackage,
                          BinaryRecordPackage, IntegerRecordPackage,
                          EnumRecordPackage, FloatRecordPackage,
                          WaveformRecordPackage, StringRecordPackage)

from . import conftest

logger = logging.getLogger(__name__)


def make_mock_type(name, is_array=False, is_enum=False, is_string=False,
                   enum_dict=None, length=1):
    if name.startswith('STRING'):
        is_string = True

    return types.SimpleNamespace(
        name=name,
        is_array=is_array,
        is_enum=is_enum,
        is_string=is_string,
        walk=[],
        enum_dict=enum_dict or {},
        length=length
    )



@pytest.fixture(scope='module')
def chain():
    tmc = parser.parse(conftest.TMC_ROOT / 'xtes_sxr_plc.tmc')
    symbols = list(pragmas.find_pytmc_symbols(tmc))
    return list(pragmas.chains_from_symbol(symbols[1]))[0]


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
def test_record_package_from_chain(chain, tc_type, is_array, final_type,
                                   monkeypatch):
    chain.data_type = make_mock_type(tc_type, is_array=is_array)
    record = RecordPackage.from_chain(851, chain=chain)
    assert isinstance(record, final_type)


@pytest.mark.parametrize("tc_type, io, is_array, final_DTYP", [
    ("BOOL", 'i', False, 'asynInt32'),
    ("BOOL", 'io', False, 'asynInt32'),
    ("BOOL", 'i', True, 'asynInt8ArrayIn'),
    ("BOOL", 'io', True, 'asynInt8ArrayOut'),
    ("INT", 'i', False, 'asynInt32'),
    ("INT", 'io', False, 'asynInt32'),
    ("INT", 'i', True, 'asynInt16ArrayIn'),
    ("INT", 'io', True, 'asynInt16ArrayOut'),
    ("DINT", 'i', False, 'asynInt32'),
    ("DINT", 'io', False, 'asynInt32'),
    ("DINT", 'i', True, 'asynInt32ArrayIn'),
    ("DINT", 'io', True, 'asynInt32ArrayOut'),
    ("REAL", 'i', False, 'asynFloat64'),
    ("REAL", 'io', False, 'asynFloat64'),
    ("REAL", 'i', True, 'asynFloat32ArrayIn'),
    ("REAL", 'io', True, 'asynFloat32ArrayOut'),
    ("LREAL", 'i', False, 'asynFloat64'),
    ("LREAL", 'io', False, 'asynFloat64'),
    ("LREAL", 'i', True, 'asynFloat64ArrayIn'),
    ("LREAL", 'io', True, 'asynFloat64ArrayOut'),
    ("ENUM", 'i', False, 'asynInt32'),
    ("ENUM", 'io', False, 'asynInt32'),
    ("ENUM", 'i', True, 'asynInt16ArrayIn'),
    ("ENUM", 'io', True, 'asynInt16ArrayOut'),
    ("STRING", 'i', False, 'asynInt8ArrayIn'),
    ("STRING", 'io', False, 'asynInt8ArrayOut'),
])
def test_dtype(chain, tc_type, io, is_array, final_DTYP):
    chain.data_type = make_mock_type(tc_type, is_array=is_array, length=3)
    chain.config['io'] = io
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    # If we are checking an input type check the first record
    if record.io_direction == 'input':
        assert record.records[0].fields['DTYP'] == final_DTYP
    # Otherwise check the output records
    else:
        assert record.records[1].fields['DTYP'] == final_DTYP


@pytest.mark.parametrize("tc_type, sing_index, field_type, final_INP_OUT", [
    ("BOOL", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c='),
    ("BOOL", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?'),
    ("BYTE", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c='),
    ("BYTE", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?'),
    ("SINT", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c=',),
    ("SINT", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?',),
    ("USINT", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c='),
    ("USINT", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?'),
    ("WORD", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c='),
    ("WORD", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?'),
    ("INT", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c=',),
    ("INT", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?',),
    ("UINT", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c='),
    ("UINT", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?'),
    ("DWORD", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c='),
    ("DWORD", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?'),
    ("DINT", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c=',),
    ("DINT", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?',),
    ("UDINT", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c='),
    ("UDINT", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?'),
    ("LREAL", 0, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c=',),
    ("LREAL", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?',),
    ("STRING", 2, "INP", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c?',),
    ("STRING", 6, "OUT", '@asyn($(PORT),0,1)ADSPORT=851/a.b.c=',),
])
def test_input_output_scan(chain, dbd_file, tc_type, sing_index, field_type,
                           final_INP_OUT):
    chain.data_type = make_mock_type(tc_type, is_array=False)
    chain.config['io'] = 'io'
    chain.tcname = 'a.b.c'
    chain.pvname = 'pvname'
    record = RecordPackage.from_chain(chain=chain, ads_port=851)

    # chain must be broken into singular
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

    # Verify SCAN settings (replaces test_BaseRecordPackage_guess_SCAN)
    assert record.records[0].fields.get('SCAN') == 'I/O Intr'
    assert record.records[1].fields.get('SCAN') is None


@pytest.mark.parametrize("tc_type, sing_index, final_ZNAM, final_ONAM, ret", [
    ("BOOL", 0, 'Zero', 'One', True),
    ("STRING", 0, None, None, False),
])
def test_bool_naming(chain, tc_type, sing_index, final_ZNAM, final_ONAM, ret):
    chain.data_type = make_mock_type(tc_type)
    chain.config['io'] = 'io'
    record = RecordPackage.from_chain(chain=chain, ads_port=851)

    for rec in record.records:
        assert rec.fields.get('ZNAM') == final_ZNAM
        assert rec.fields.get('ONAM') == final_ONAM


@pytest.mark.parametrize("tc_type, sing_index, final_PREC, ret", [
    ("LREAL", 0, '3', True),
    ("STRING", 0, None, False),
])
def test_BaseRecordPackage_guess_PREC(chain, tc_type, sing_index, final_PREC,
                                      ret):
    chain.data_type = make_mock_type(tc_type)
    chain.config['io'] = 'io'
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    for rec in record.records:
        assert rec.fields.get('PREC') == final_PREC


@pytest.mark.parametrize("tc_type, io, is_str, is_arr, final_FTVL", [
    ("INT", 'o', False, False, None),
    pytest.param(
        "INT", 'o', False, True, 'FINISH',
        marks=pytest.mark.skip(reason="feature pending")),
    ("BOOL", 'i', False, False, None),
    ("BOOL", 'i', False, True, 'CHAR'),
    ("BOOL", 'o', False, True, 'CHAR'),
    ("BOOL", 'io', False, True, 'CHAR'),
    ("INT", 'i', False, False, None),
    ("INT", 'i', False, True, 'SHORT'),
    ("INT", 'o', False, True, 'SHORT'),
    ("INT", 'io', False, True, 'SHORT'),
    ("DINT", 'i', False, False, None),
    ("DINT", 'i', False, True, 'LONG'),
    ("DINT", 'o', False, True, 'LONG'),
    ("DINT", 'io', False, True, 'LONG'),
    ("ENUM", 'i', False, False, None),
    ("ENUM", 'i', False, True, 'SHORT'),
    ("ENUM", 'o', False, True, 'SHORT'),
    ("ENUM", 'io', False, True, 'SHORT'),
    ("REAL", 'i', False, False, None),
    ("REAL", 'i', False, True, 'FLOAT'),
    ("REAL", 'o', False, True, 'FLOAT'),
    ("REAL", 'io', False, True, 'FLOAT'),
    ("LREAL", 'i', False, False, None),
    ("LREAL", 'i', False, True, 'DOUBLE'),
    ("LREAL", 'o', False, True, 'DOUBLE'),
    ("LREAL", 'io', False, True, 'DOUBLE'),
    ("STRING", 'i', True, False, 'CHAR'),
    ("STRING", 'o', True, False, 'CHAR'),
    ("STRING", 'io', True, False, 'CHAR'),
])
def test_BaseRecordPackage_guess_FTVL(chain, tc_type, io, is_str, is_arr,
                                      final_FTVL, dbd_file):
    chain.data_type = make_mock_type(tc_type, is_array=is_arr,
                                     is_string=is_str, length=3)
    chain.config['io'] = io
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    for rec in record.records:
        assert rec.fields.get('FTVL') == final_FTVL

    conftest.lint_record(dbd_file, record)


@pytest.mark.parametrize("tc_type, sing_index, is_str, is_arr, final_NELM", [
    ("INT", 0, False, False, None),
    ("INT", 0, False, True, '3'),
    ("LREAL", 0, False, True, '9'),
    ("STRING", 0, True, False, '81'),
])
def test_BaseRecordPackage_guess_NELM(chain, tc_type, sing_index, is_str,
                                      is_arr, final_NELM):
    chain.data_type = make_mock_type(tc_type, is_array=is_arr,
                                     is_string=is_str,
                                     length=final_NELM)
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    for rec in record.records:
        assert rec.fields.get('NELM') == final_NELM
