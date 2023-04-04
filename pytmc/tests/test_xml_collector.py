import logging
import types

import pytest

from pytmc import parser, pragmas
from pytmc.record import (MAX_ARCHIVE_ELEMENTS, BinaryRecordPackage,
                          EnumRecordPackage, FloatRecordPackage,
                          IntegerRecordPackage, RecordPackage,
                          StringRecordPackage, WaveformRecordPackage)

from . import conftest

logger = logging.getLogger(__name__)


def make_mock_twincatitem(
    name, data_type, *, pragma=None, array_info=None, ads_port=851
):
    """
    Create a mock TwincatItem for testing purposes

    May require monkey-patching `walk` to create chains.
    """

    class _Property:
        name = "pytmc"
        value = str(pragma)

    class _Properties:
        Property = [_Property]

    class MockItem:
        module = types.SimpleNamespace(ads_port=ads_port)

        if pragma is not None:
            Properties = [_Properties]

    MockItem.name = name
    MockItem.array_info = array_info
    MockItem.data_type = data_type

    def walk(condition=None):
        # By default, just the item itself:
        yield [MockItem]

    MockItem.walk = walk

    if array_info is not None:

        class ArrayInfo:
            bounds = array_info
            elements = array_info[1] - array_info[0]

        MockItem.array_info = ArrayInfo
    return MockItem


def make_mock_type(
    name,
    is_array=False,
    is_enum=False,
    is_string=False,
    is_complex_type=False,
    enum_dict=None,
    length=1,
):
    if name.startswith("STRING"):
        is_string = True

    def walk(condition=None):
        for a in []:
            yield 0

    return types.SimpleNamespace(
        name=name,
        is_array=is_array,
        is_enum=is_enum,
        is_string=is_string,
        is_complex_type=is_complex_type,
        walk=walk,
        enum_dict=enum_dict or {},
        length=length,
    )


@pytest.fixture(scope="module")
def chain():
    tmc = parser.parse(conftest.TMC_ROOT / "xtes_sxr_plc.tmc")
    symbols = list(pragmas.find_pytmc_symbols(tmc))
    return list(pragmas.chains_from_symbol(symbols[1]))[0]


@pytest.mark.parametrize(
    "tc_type, is_array, final_type",
    [
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
    ],
)
def test_record_package_from_chain(chain, tc_type, is_array, final_type, monkeypatch):
    chain.data_type = make_mock_type(tc_type, is_array=is_array)
    record = RecordPackage.from_chain(851, chain=chain)
    assert isinstance(record, final_type)


@pytest.mark.parametrize(
    "tc_type, io, is_array, final_DTYP",
    [
        ("BOOL", "i", False, "asynInt32"),
        ("BOOL", "io", False, "asynInt32"),
        ("BOOL", "i", True, "asynInt8ArrayIn"),
        ("BOOL", "io", True, "asynInt8ArrayOut"),
        ("INT", "i", False, "asynInt32"),
        ("INT", "io", False, "asynInt32"),
        ("INT", "i", True, "asynInt16ArrayIn"),
        ("INT", "io", True, "asynInt16ArrayOut"),
        ("DINT", "i", False, "asynInt32"),
        ("DINT", "io", False, "asynInt32"),
        ("DINT", "i", True, "asynInt32ArrayIn"),
        ("DINT", "io", True, "asynInt32ArrayOut"),
        ("REAL", "i", False, "asynFloat64"),
        ("REAL", "io", False, "asynFloat64"),
        ("REAL", "i", True, "asynFloat32ArrayIn"),
        ("REAL", "io", True, "asynFloat32ArrayOut"),
        ("LREAL", "i", False, "asynFloat64"),
        ("LREAL", "io", False, "asynFloat64"),
        ("LREAL", "i", True, "asynFloat64ArrayIn"),
        ("LREAL", "io", True, "asynFloat64ArrayOut"),
        ("ENUM", "i", False, "asynInt32"),
        ("ENUM", "io", False, "asynInt32"),
        ("ENUM", "i", True, "asynInt16ArrayIn"),
        ("ENUM", "io", True, "asynInt16ArrayOut"),
        ("STRING", "i", False, "asynInt8ArrayIn"),
        ("STRING", "io", False, "asynInt8ArrayOut"),
    ],
)
def test_dtype(chain, tc_type, io, is_array, final_DTYP):
    chain.data_type = make_mock_type(tc_type, is_array=is_array, length=3)
    chain.config["io"] = io
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    # If we are checking an input type check the first record
    if record.io_direction == "input":
        assert record.records[0].fields["DTYP"] == final_DTYP
    # Otherwise check the output records
    else:
        assert record.records[1].fields["DTYP"] == final_DTYP


scan_test_params = [  # default update rates:
    ("BOOL", 0, "", "OUT", "@asyn($(PORT),0,1)ADSPORT=851/a.b.c="),
    ("BOOL", 2, "", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    ("BYTE", 0, "", "OUT", "@asyn($(PORT),0,1)ADSPORT=851/a.b.c="),
    ("BYTE", 2, "", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    (
        "SINT",
        0,
        "",
        "OUT",
        "@asyn($(PORT),0,1)ADSPORT=851/a.b.c=",
    ),
    (
        "SINT",
        2,
        "",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?",
    ),
    ("USINT", 0, "", "OUT", "@asyn($(PORT),0,1)ADSPORT=851/a.b.c="),
    ("USINT", 2, "", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    ("WORD", 0, "", "OUT", "@asyn($(PORT),0,1)ADSPORT=851/a.b.c="),
    ("WORD", 2, "", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    (
        "INT",
        0,
        "",
        "OUT",
        "@asyn($(PORT),0,1)ADSPORT=851/a.b.c=",
    ),
    (
        "INT",
        2,
        "",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?",
    ),
    ("UINT", 0, "", "OUT", "@asyn($(PORT),0,1)ADSPORT=851/a.b.c="),
    ("UINT", 2, "", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    ("DWORD", 0, "", "OUT", "@asyn($(PORT),0,1)ADSPORT=851/a.b.c="),
    ("DWORD", 2, "", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    (
        "DINT",
        0,
        "",
        "OUT",
        "@asyn($(PORT),0,1)ADSPORT=851/a.b.c=",
    ),
    (
        "DINT",
        2,
        "",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?",
    ),
    ("UDINT", 0, "", "OUT", "@asyn($(PORT),0,1)ADSPORT=851/a.b.c="),
    ("UDINT", 2, "", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    (
        "LREAL",
        0,
        "",
        "OUT",
        "@asyn($(PORT),0,1)ADSPORT=851/a.b.c=",
    ),
    (
        "LREAL",
        2,
        "",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?",
    ),
    (
        "STRING",
        2,
        "",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?",
    ),
    (
        "STRING",
        6,
        "",
        "OUT",
        "@asyn($(PORT),0,1)ADSPORT=851/a.b.c=",
    ),
    # poll rates
    ("BOOL", 2, "1hz poll", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    ("BOOL", 2, "2hz poll", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=2/a.b.c?"),
    (
        "BOOL",
        2,
        "0.5hz poll",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=0.5/a.b.c?",
    ),
    (
        "BOOL",
        2,
        "0.02hz poll",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=0.02/a.b.c?",
    ),
    (
        "BOOL",
        2,
        "0.1hz poll",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=0.1/a.b.c?",
    ),
    (
        "BOOL",
        2,
        "50s poll",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=0.02/a.b.c?",
    ),
    (
        "BOOL",
        2,
        "10s poll",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=0.1/a.b.c?",
    ),
    ("BOOL", 2, "2s poll", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=0.5/a.b.c?"),
    ("BOOL", 2, "1s poll", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=1/a.b.c?"),
    ("BOOL", 2, "0.5s poll", "INP", "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=2/a.b.c?"),
    pytest.param(
        "BOOL",
        2,
        "0.1s poll",
        "INP",
        "@asyn($(PORT),0,1)ADSPORT=851/POLL_RATE=10/a.b.c?",
        marks=pytest.mark.xfail(reason="Invalid poll rate"),
    ),
    # notify rates
    ("BOOL", 2, "1hz notify", "INP", "@asyn($(PORT),0,1)ADSPORT=851/TS_MS=1000/a.b.c?"),
    ("BOOL", 2, "2hz notify", "INP", "@asyn($(PORT),0,1)ADSPORT=851/TS_MS=500/a.b.c?"),
    ("BOOL", 2, "0.1s notify", "INP", "@asyn($(PORT),0,1)ADSPORT=851/TS_MS=100/a.b.c?"),
]


@pytest.mark.parametrize(
    "tc_type, sing_index, update, field_type, final_INP_OUT", scan_test_params
)
def test_input_output_scan(
    chain, dbd_file, tc_type, sing_index, update, field_type, final_INP_OUT
):
    chain.data_type = make_mock_type(tc_type, is_array=False)
    chain.config["io"] = "io"
    chain.config["update"] = update
    chain.tcname = "a.b.c"
    chain.pvname = "pvname"
    record = RecordPackage.from_chain(chain=chain, ads_port=851)

    # chain must be broken into singular
    if tc_type == "STRING":
        if field_type == "OUT":
            assert record.records[1].fields.get("INP") == final_INP_OUT
        else:
            assert record.records[0].fields.get("INP") == final_INP_OUT
    else:
        if field_type == "OUT":
            assert record.records[1].fields.get("INP") is None
            assert record.records[1].fields.get("OUT") == final_INP_OUT
        if field_type == "INP":
            assert record.records[0].fields.get("OUT") is None
            assert record.records[0].fields.get("INP") == final_INP_OUT

    conftest.lint_record(dbd_file, record)

    # Verify SCAN settings (replaces test_BaseRecordPackage_guess_SCAN)
    assert record.records[0].fields.get("SCAN") == "I/O Intr"
    assert record.records[1].fields.get("SCAN") is None


@pytest.mark.parametrize(
    "tc_type, sing_index, final_ZNAM, final_ONAM, ret",
    [
        ("BOOL", 0, "FALSE", "TRUE", True),
        ("STRING", 0, None, None, False),
    ],
)
def test_bool_naming(chain, tc_type, sing_index, final_ZNAM, final_ONAM, ret):
    chain.data_type = make_mock_type(tc_type)
    chain.config["io"] = "io"
    record = RecordPackage.from_chain(chain=chain, ads_port=851)

    for rec in record.records:
        assert rec.fields.get("ZNAM") == final_ZNAM
        assert rec.fields.get("ONAM") == final_ONAM


@pytest.mark.parametrize(
    "tc_type, sing_index, final_PREC, ret",
    [
        ("LREAL", 0, "3", True),
        ("STRING", 0, None, False),
    ],
)
def test_BaseRecordPackage_guess_PREC(chain, tc_type, sing_index, final_PREC, ret):
    chain.data_type = make_mock_type(tc_type)
    chain.config["io"] = "io"
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    for rec in record.records:
        assert rec.fields.get("PREC") == final_PREC


@pytest.mark.parametrize(
    "tc_type, io, is_str, is_arr, final_FTVL",
    [
        ("INT", "o", False, False, None),
        pytest.param(
            "INT",
            "o",
            False,
            True,
            "FINISH",
            marks=pytest.mark.skip(reason="feature pending"),
        ),
        ("BOOL", "i", False, False, None),
        ("BOOL", "i", False, True, "CHAR"),
        ("BOOL", "o", False, True, "CHAR"),
        ("BOOL", "io", False, True, "CHAR"),
        ("INT", "i", False, False, None),
        ("INT", "i", False, True, "SHORT"),
        ("INT", "o", False, True, "SHORT"),
        ("INT", "io", False, True, "SHORT"),
        ("DINT", "i", False, False, None),
        ("DINT", "i", False, True, "LONG"),
        ("DINT", "o", False, True, "LONG"),
        ("DINT", "io", False, True, "LONG"),
        ("ENUM", "i", False, False, None),
        ("ENUM", "i", False, True, "SHORT"),
        ("ENUM", "o", False, True, "SHORT"),
        ("ENUM", "io", False, True, "SHORT"),
        ("REAL", "i", False, False, None),
        ("REAL", "i", False, True, "FLOAT"),
        ("REAL", "o", False, True, "FLOAT"),
        ("REAL", "io", False, True, "FLOAT"),
        ("LREAL", "i", False, False, None),
        ("LREAL", "i", False, True, "DOUBLE"),
        ("LREAL", "o", False, True, "DOUBLE"),
        ("LREAL", "io", False, True, "DOUBLE"),
        ("STRING", "i", True, False, "CHAR"),
        ("STRING", "o", True, False, "CHAR"),
        ("STRING", "io", True, False, "CHAR"),
    ],
)
def test_BaseRecordPackage_guess_FTVL(
    chain, tc_type, io, is_str, is_arr, final_FTVL, dbd_file
):
    chain.data_type = make_mock_type(
        tc_type, is_array=is_arr, is_string=is_str, length=3
    )
    chain.config["io"] = io
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    for rec in record.records:
        assert rec.fields.get("FTVL") == final_FTVL

    conftest.lint_record(dbd_file, record)


@pytest.mark.parametrize(
    "tc_type, sing_index, is_str, is_arr, final_NELM",
    [
        ("INT", 0, False, False, None),
        ("INT", 0, False, True, 3),
        ("LREAL", 0, False, True, 9),
        ("STRING", 0, True, False, 81),
    ],
)
def test_BaseRecordPackage_guess_NELM(
    chain, tc_type, sing_index, is_str, is_arr, final_NELM
):
    chain.data_type = make_mock_type(
        tc_type, is_array=is_arr, is_string=is_str, length=final_NELM
    )
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    for rec in record.records:
        assert rec.fields.get("NELM") == final_NELM


def test_scalar():
    item = make_mock_twincatitem(
        name="Main.tcname", data_type=make_mock_type("DINT"), pragma="pv: PVNAME"
    )

    (record,) = list(pragmas.record_packages_from_symbol(item))
    assert record.pvname == "PVNAME"
    assert record.tcname == "Main.tcname"
    assert isinstance(record, IntegerRecordPackage)


def test_complex_array():
    array = make_mock_twincatitem(
        name="Main.array_base",
        data_type=make_mock_type("MY_DUT", is_complex_type=True),
        pragma="pv: ARRAY",
        array_info=(1, 4),
    )

    subitem1 = make_mock_twincatitem(
        name="subitem1", data_type=make_mock_type("INT"), pragma="pv: subitem1"
    )

    subitem2 = make_mock_twincatitem(
        name="subitem2", data_type=make_mock_type("REAL"), pragma="pv: subitem2\nio: i"
    )

    def walk(condition=None):
        # Two chains, one for each array + subitem
        yield [array, subitem1]
        yield [array, subitem2]

    array.walk = walk
    records = {
        record.pvname: record for record in pragmas.record_packages_from_symbol(array)
    }

    assert set(records) == {
        "ARRAY:01:subitem1",
        "ARRAY:02:subitem1",
        "ARRAY:03:subitem1",
        "ARRAY:04:subitem1",
        "ARRAY:01:subitem2",
        "ARRAY:02:subitem2",
        "ARRAY:03:subitem2",
        "ARRAY:04:subitem2",
    }

    assert isinstance(records["ARRAY:01:subitem1"], IntegerRecordPackage)
    assert isinstance(records["ARRAY:01:subitem2"], FloatRecordPackage)

    assert records["ARRAY:01:subitem1"].io_direction == "output"
    assert records["ARRAY:01:subitem2"].io_direction == "input"


@pytest.mark.parametrize(
    "dimensions, pragma, expected_records",
    [
        pytest.param(
            [0, 3],
            "",
            {
                "ARRAY:00:subitem1",
                "ARRAY:01:subitem1",
                "ARRAY:02:subitem1",
                "ARRAY:03:subitem1",
            },
            id="no-pragma",
        ),
        pytest.param(
            [0, 3], "array: 0..1", {"ARRAY:00:subitem1", "ARRAY:01:subitem1"}, id="0..1"
        ),
        pytest.param(
            [0, 3],
            "array: 0..1, 3",
            {"ARRAY:00:subitem1", "ARRAY:01:subitem1", "ARRAY:03:subitem1"},
            id="0..1,3",
        ),
        pytest.param(
            [0, 3], "array: ..1", {"ARRAY:00:subitem1", "ARRAY:01:subitem1"}, id="..1"
        ),
        pytest.param(
            [0, 3],
            "array: 1..",
            {"ARRAY:01:subitem1", "ARRAY:02:subitem1", "ARRAY:03:subitem1"},
            id="1..",
        ),
        pytest.param(
            [0, 100],
            "array: 0..1, 99..",
            {
                "ARRAY:0000:subitem1",
                "ARRAY:0001:subitem1",
                "ARRAY:0099:subitem1",
                "ARRAY:0100:subitem1",
            },
            id="0..1,99..",
        ),
        pytest.param(
            [0, 100],
            """
                     array: 0
                     pv: OTHER
                     array: 2..3
                     """,
            {
                "ARRAY:0000:subitem1",
                "OTHER:0002:subitem1",
                "OTHER:0003:subitem1",
            },
            id="separate_prefixes",
        ),
    ],
)
def test_complex_array_partial(dimensions, pragma, expected_records):
    array = make_mock_twincatitem(
        name="Main.array_base",
        data_type=make_mock_type("MY_DUT", is_complex_type=True),
        pragma="\n".join(("pv: ARRAY", pragma)),
        array_info=dimensions,
    )

    subitem1 = make_mock_twincatitem(
        name="subitem1", data_type=make_mock_type("INT"), pragma="pv: subitem1"
    )

    def walk(condition=None):
        yield [array, subitem1]

    array.walk = walk
    record_names = (
        record.pvname for record in pragmas.record_packages_from_symbol(array)
    )
    assert set(record_names) == expected_records


def test_enum_array():
    array = make_mock_twincatitem(
        name="Main.enum_array",
        data_type=make_mock_type(
            "MY_ENUM", is_enum=True, enum_dict={1: "ONE", 2: "TWO"}
        ),
        pragma="pv: ENUMS",
        array_info=(1, 4),
    )

    records = {
        record.pvname: record for record in pragmas.record_packages_from_symbol(array)
    }

    assert set(records) == {
        "ENUMS:01",
        "ENUMS:02",
        "ENUMS:03",
        "ENUMS:04",
    }

    print(records)
    enum01 = records["ENUMS:01"]
    assert isinstance(enum01, EnumRecordPackage)
    assert enum01.field_defaults["ZRVL"] == 1
    assert enum01.field_defaults["ZRST"] == "ONE"
    assert enum01.field_defaults["ONVL"] == 2
    assert enum01.field_defaults["ONST"] == "TWO"


def test_unroll_formatting():
    array = make_mock_twincatitem(
        name="Main.enum_array",
        data_type=make_mock_type(
            "MY_ENUM", is_enum=True, enum_dict={1: "ONE", 2: "TWO"}
        ),
        pragma="pv: ENUMS\nexpand: _EXPAND%d",
        array_info=(1, 4),
    )

    records = {
        record.pvname: record for record in pragmas.record_packages_from_symbol(array)
    }

    assert set(records) == {
        "ENUMS_EXPAND1",
        "ENUMS_EXPAND2",
        "ENUMS_EXPAND3",
        "ENUMS_EXPAND4",
    }


def test_pv_linking():
    item = make_mock_twincatitem(
        name="Main.tcname",
        data_type=make_mock_type("DINT"),
        pragma="pv: PVNAME; link: OTHER:RECORD",
    )

    (pkg,) = list(pragmas.record_packages_from_symbol(item))
    assert pkg.pvname == "PVNAME"
    assert pkg.tcname == "Main.tcname"
    assert isinstance(pkg, IntegerRecordPackage)
    rec = pkg.generate_output_record()
    assert rec.fields["OMSL"] == "closed_loop"
    assert rec.fields["DOL"] == "OTHER:RECORD CP MS"
    assert rec.fields["SCAN"] == ".5 second"


def test_pv_linking_string():
    item = make_mock_twincatitem(
        name="Main.tcname",
        data_type=make_mock_type("STRING", length=70),
        pragma="pv: PVNAME; link: OTHER:RECORD.VAL$",
    )

    (pkg,) = list(pragmas.record_packages_from_symbol(item))
    assert pkg.pvname == "PVNAME"
    assert pkg.tcname == "Main.tcname"
    assert isinstance(pkg, StringRecordPackage)

    in_rec, out_rec, lso_rec = pkg.records
    assert "OMSL" not in out_rec.fields
    assert "DOL" not in out_rec.fields

    lso_pvname = pkg.delimiter.join((out_rec.pvname, pkg.link_suffix))
    assert lso_rec.pvname == lso_pvname
    assert lso_rec.record_type == "lso"
    assert lso_rec.fields["OMSL"] == "closed_loop"
    assert lso_rec.fields["DOL"] == "OTHER:RECORD.VAL$ CP MS"
    assert lso_rec.fields["SCAN"] == ".5 second"
    assert lso_rec.fields["SIZV"] == 70


def test_pv_linking_struct():
    struct = make_mock_twincatitem(
        name="Main.my_dut",
        data_type=make_mock_type("MY_DUT", is_complex_type=True),
        pragma="pv: PREFIX; link: LINK:",
    )

    subitem1 = make_mock_twincatitem(
        name="subitem1",
        data_type=make_mock_type("INT"),
        pragma="pv: ABCD; link: **ABCD.STAT",
    )

    subitem2 = make_mock_twincatitem(
        name="subitem2",
        data_type=make_mock_type("INT"),
        pragma="pv: EFGH; link: OTHER_PV",
    )

    def walk(condition=None):
        yield [struct, subitem1]
        yield [struct, subitem2]

    struct.walk = walk

    pkg1, pkg2 = list(pragmas.record_packages_from_symbol(struct))
    rec = pkg1.generate_output_record()
    assert rec.fields["DOL"] == "PREFIX:ABCD.STAT CP MS"

    rec = pkg2.generate_output_record()
    assert rec.fields["DOL"] == "LINK:OTHER_PV CP MS"


def test_pv_linking_special():
    struct = make_mock_twincatitem(
        name="Main.array_base",
        data_type=make_mock_type("MY_DUT", is_complex_type=True),
        pragma="pv: PREFIX",
    )

    subitem1 = make_mock_twincatitem(
        name="subitem1",
        data_type=make_mock_type("INT"),
        pragma="pv: ABCD; link: **ABCD.STAT",
    )

    def walk(condition=None):
        yield [struct, subitem1]

    struct.walk = walk

    (pkg,) = list(pragmas.record_packages_from_symbol(struct))
    rec = pkg.generate_output_record()
    assert rec.fields["DOL"] == "PREFIX:ABCD.STAT CP MS"


@pytest.mark.parametrize(
    "elements, archive_settings",
    [
        pytest.param(MAX_ARCHIVE_ELEMENTS + 1, None, id="over_threshold"),
        pytest.param(
            MAX_ARCHIVE_ELEMENTS,
            {"frequency": 1, "seconds": 1, "method": "scan", "fields": {"VAL"}},
            id="under_threshold",
        ),
    ],
)
def test_waveform_archive(chain, dbd_file, elements, archive_settings):
    chain.data_type = make_mock_type("INT", is_array=True, length=elements)
    chain.config["io"] = "io"
    record = RecordPackage.from_chain(chain=chain, ads_port=851)
    assert record.archive_settings == archive_settings
    assert len(record.records) == 2
    for rec in record.records:
        print()
        print("Archive settings", record.archive_settings)
        print(rec.render())

        assert rec.fields.get("APST") == "On Change"
        assert rec.fields.get("MPST") == "On Change"

    conftest.lint_record(dbd_file, record)


@pytest.mark.parametrize(
    "dimensions, pragma, expected_records",
    [
        pytest.param(
            [0, 3],
            "",
            {
                "OUTER:INNER:00:item1",
                "OUTER:INNER:01:item1",
                "OUTER:INNER:02:item1",
                "OUTER:INNER:03:item1",
            },
            id="no-pragma",
        ),
        pytest.param(
            [0, 3],
            "my_dut2.array: 0..1",
            {
                "OUTER:INNER:00:item1",
                "OUTER:INNER:01:item1",
            },
            id="0..1",
        ),
        pytest.param(
            [0, 99],
            "my_dut2.array: 1..3,5,7,9",
            {
                "OUTER:INNER:001:item1",
                "OUTER:INNER:002:item1",
                "OUTER:INNER:003:item1",
                "OUTER:INNER:005:item1",
                "OUTER:INNER:007:item1",
                "OUTER:INNER:009:item1",
            },
            id="1..3,5,7,9",
        ),
    ],
)
def test_complex_sub_array_partial(dimensions, pragma, expected_records):
    outer = make_mock_twincatitem(
        name="Main.my_dut",
        data_type=make_mock_type("MY_DUT", is_complex_type=True),
        pragma="\n".join(("pv: OUTER", pragma)),
    )

    inner = make_mock_twincatitem(
        name="my_dut2",
        data_type=make_mock_type("MY_DUT2", is_complex_type=True),
        pragma="pv: INNER",
        array_info=dimensions,
    )

    subsubitem1 = make_mock_twincatitem(
        name="item1", data_type=make_mock_type("INT"), pragma="pv: item1"
    )

    def walk(condition=None):
        yield [outer, inner, subsubitem1]

    outer.walk = walk
    record_names = (
        record.pvname for record in pragmas.record_packages_from_symbol(outer)
    )
    assert set(record_names) == expected_records


@pytest.mark.parametrize(
    "dimensions, pragma, expected_records",
    [
        pytest.param(
            [0, 3],
            "",
            {
                "OUTER:INNER:00:item1_RBV",
                "OUTER:INNER:01:item1_RBV",
                "OUTER:INNER:02:item1_RBV",
                "OUTER:INNER:03:item1_RBV",
            },
            id="no-pragma",
        ),
        pytest.param(
            [0, 3],
            ("my_dut2.array: 0..1\n" "my_dut2.item1.io: io\n"),
            {
                "OUTER:INNER:00:item1",
                "OUTER:INNER:01:item1",
                "OUTER:INNER:00:item1_RBV",
                "OUTER:INNER:01:item1_RBV",
            },
            id="change_to_io",
        ),
    ],
)
def test_sub_io_change(dimensions, pragma, expected_records):
    outer = make_mock_twincatitem(
        name="Main.my_dut",
        data_type=make_mock_type("MY_DUT", is_complex_type=True),
        pragma="\n".join(("pv: OUTER", pragma)),
    )

    inner = make_mock_twincatitem(
        name="my_dut2",
        data_type=make_mock_type("MY_DUT2", is_complex_type=True),
        pragma="pv: INNER",
        array_info=dimensions,
    )

    subsubitem1 = make_mock_twincatitem(
        name="item1",
        data_type=make_mock_type("INT"),
        pragma="\n".join(("pv: item1", "io: i")),
    )

    def walk(condition=None):
        yield [outer, inner, subsubitem1]

    outer.walk = walk
    record_names = (
        record.pvname
        for pkg in pragmas.record_packages_from_symbol(outer)
        for record in pkg.records
    )
    assert set(record_names) == expected_records


@pytest.mark.parametrize(
    "data_type, pragma, expected_scale, expected_offset",
    [
        pytest.param(
            "FLOAT",
            "pv: PREFIX; scale: 2.0; offset: 1.0",
            "2.0",
            "1.0",
            id="float-scale-and-offset",
        ),
        pytest.param(
            "UDINT",
            "pv: PREFIX; scale: 3.0; offset: 0.1",
            "3.0",
            "0.1",
            id="int-scale-and-offset",
        ),
        pytest.param(
            "UDINT",
            "pv: PREFIX; scale: 3.0",
            "3.0",
            "0.0",
            id="int-no-offset",
        ),
        pytest.param(
            "UDINT",
            "pv: PREFIX; offset: 3.0",
            "1.0",
            "3.0",
            id="int-no-scale",
        ),
    ],
)
def test_scale_and_offset(data_type, pragma, expected_scale, expected_offset):
    item = make_mock_twincatitem(
        name="Main.obj",
        data_type=make_mock_type("UDINT", is_complex_type=False),
        pragma=pragma,
    )

    (pkg,) = list(pragmas.record_packages_from_symbol(item))
    for rec in pkg.records:
        assert rec.fields["LINR"] == "SLOPE"
        assert rec.fields["ESLO"] == expected_scale
        assert rec.fields["EOFF"] == expected_offset
        assert rec.record_type in {"ai", "ao"}
