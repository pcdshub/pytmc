from collections import OrderedDict

from pytmc.record import EPICSRecord, sort_fields
from pytmc.linter import lint_db


def test_epics_record_render():
    kwargs = {'pvname': 'Tst:pv',
              'record_type': 'ai',
              'fields': {'ZNAM': 'Out',
                         'ONAM': 'In'}}

    ec = EPICSRecord(**kwargs)
    record = ec.render()
    print(record)  # For debug purposes
    assert kwargs['pvname'] in record
    assert kwargs['record_type'] in record
    for key, value in kwargs['fields'].items():
        assert key in record
        assert value in record


def test_epics_record_with_linter(dbd_file):
    kwargs = {'pvname': 'Tst:pv',
              'record_type': 'bi',
              'fields': {'ZNAM': '"Out"',
                         'ONAM': '"In"',
                         'DTYP': '"Raw Soft Channel"'}}
    ec = EPICSRecord(**kwargs)
    record = ec.render()
    linted = lint_db(dbd=dbd_file, db=record)
    assert not (linted.errors)

def test_sort_fields():
    unsorted_entry = OrderedDict([
        ('CALC', None),
        ('very_fake',None),
        ('ONVL', None),
        ('FTVL', None),
        ('not_real',None),
        ('NAME', None),
        ('SVSV', None),
        ('ONSV', None),
    ])
    correct_entry = OrderedDict([
        ('NAME', None),
        ('ONVL', None),
        ('FTVL', None),
        ('ONSV', None),
        ('SVSV', None),
        ('CALC', None),
        ('not_real',None),
        ('very_fake',None),
    ])
    output = sort_fields(unsorted_entry)
    assert output == correct_entry
