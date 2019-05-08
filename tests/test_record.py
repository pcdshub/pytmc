from pytmc.record import EPICSRecord


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
