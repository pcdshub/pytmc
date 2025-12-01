from collections import OrderedDict

from pytmc.linter import lint_db
from pytmc.record import EPICSRecord, sort_fields


def test_epics_record_render():
    kwargs = {
        "pvname": "Tst:pv",
        "record_type": "ai",
        "fields": {"ZNAM": "Out", "ONAM": "In"},
        "direction": "input",
    }

    ec = EPICSRecord(**kwargs)
    record = ec.render()
    print(record)  # For debug purposes
    assert kwargs["pvname"] in record
    assert kwargs["record_type"] in record
    for key, value in kwargs["fields"].items():
        assert key in record
        assert value in record


def test_epics_record_with_linter(dbd_file):
    kwargs = {
        "pvname": "Tst:pv",
        "record_type": "bi",
        "fields": {"ZNAM": '"Out"', "ONAM": '"In"', "DTYP": '"Raw Soft Channel"'},
        "direction": "input",
    }
    ec = EPICSRecord(**kwargs)
    record = ec.render()
    linted = lint_db(dbd=dbd_file, db=record)
    assert not (linted.errors)


def test_input_record_without_write_access():
    kwargs = {
        "pvname": "Tst:pv",
        "record_type": "ai",
        "direction": "input",
    }

    ec = EPICSRecord(**kwargs)
    record = ec.render()
    assert "ASG" in record
    assert "NO_WRITE" in record


def test_output_record_with_write_access():
    kwargs = {
        "pvname": "Tst:pv",
        "record_type": "ao",
        "direction": "output",
    }
    ec = EPICSRecord(**kwargs)
    record = ec.render()
    assert "ASG" not in record


def test_sort_fields():
    unsorted_entry = OrderedDict(
        [
            ("CALC", None),
            ("very_fake", None),
            ("ONVL", None),
            ("FTVL", None),
            ("not_real", None),
            ("NAME", None),
            ("SVSV", None),
            ("ONSV", None),
        ]
    )
    correct_entry = OrderedDict(
        [
            ("NAME", None),
            ("ONVL", None),
            ("FTVL", None),
            ("ONSV", None),
            ("SVSV", None),
            ("CALC", None),
            ("not_real", None),
            ("very_fake", None),
        ]
    )
    output = sort_fields(unsorted_entry)
    assert output == correct_entry


def test_epics_int64_record_render():
    # Input record
    input_kwargs = {
        "pvname": "Tst:pv64",
        "record_type": "int64in",
        "fields": {"DTYP": "asynInt64", "DESC": "Input 64-bit value"},
        "direction": "input",
    }
    ec_in = EPICSRecord(**input_kwargs)
    record_in = ec_in.render()
    print(record_in)  # For debug purposes
    assert input_kwargs["pvname"] in record_in
    assert "int64in" in record_in
    assert "asynInt64" in record_in
    assert "DESC" in record_in
    assert "Input 64-bit value" in record_in

    # Output record
    output_kwargs = {
        "pvname": "Tst:pv64",
        "record_type": "int64out",
        "fields": {"DTYP": "asynInt64", "DESC": "Output 64-bit value"},
        "direction": "output",
    }
    ec_out = EPICSRecord(**output_kwargs)
    record_out = ec_out.render()
    print(record_out)  # For debug purposes
    assert output_kwargs["pvname"] in record_out
    assert "int64out" in record_out
    assert "asynInt64" in record_out
    assert "DESC" in record_out
    assert "Output 64-bit value" in record_out


def test_epics_int64_record_with_linter(dbd64_file):
    kwargs = {
        "pvname": "Tst:pv64",
        "record_type": "int64in",
        "fields": {"DTYP": "asynInt64", "DESC": "Input 64-bit value"},
        "direction": "input",
    }
    ec = EPICSRecord(**kwargs)
    record = ec.render()
    linted = lint_db(dbd=dbd64_file, db=record)
    assert not linted.errors
