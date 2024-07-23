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
