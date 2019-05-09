from pytmc.record import EPICSRecord
from pytmc.epics import lint_db


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
