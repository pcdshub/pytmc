import pytest

import pytmc
import pytmc.record
import pytmc.pragmas

from .test_xml_collector import make_mock_twincatitem, make_mock_type


def get_record_package(data_type, io, pragma):
    pragma = '; '.join(f'{key}: {value}' for key, value in pragma.items())
    symbol = make_mock_twincatitem(name='a',
                                   data_type=data_type,
                                   pragma=f'pv: PVNAME; io: {io}; {pragma}',
                                   )
    return list(pytmc.pragmas.record_packages_from_symbol(symbol))[0]


@pytest.mark.parametrize(
    'data_type, io, pragma, expected',
    [pytest.param(make_mock_type('INT'), 'io', dict(archive='2s'),
                  ['\t'.join(('PVNAME_RBV.VAL', '2', 'scan')),
                   '\t'.join(('PVNAME.VAL', '2', 'scan'))
                   ],
                  id='2s_io_default',
                  ),
     pytest.param(make_mock_type('INT'), 'i', dict(archive='1s'),
                  ['\t'.join(('PVNAME_RBV.VAL', '1', 'scan')),
                   ],
                  id='1s_i_default'),
     pytest.param(make_mock_type('INT'), 'i', dict(archive='1s monitor'),
                  ['\t'.join(('PVNAME_RBV.VAL', '1', 'monitor')),
                   ],
                  id='1s_i_monitor'),
     pytest.param(make_mock_type('INT'), 'i', dict(archive='1s scan'),
                  ['\t'.join(('PVNAME_RBV.VAL', '1', 'scan')),
                   ],
                  id='1s_i_scan'),
     pytest.param(make_mock_type('INT'), 'i', dict(archive='1s test'), [],
                  id='bad_pragma', marks=pytest.mark.xfail),
     pytest.param(make_mock_type('INT', length=100, is_array=True), 'i',
                  dict(archive='1s scan'),
                  ['\t'.join(('PVNAME_RBV.VAL', '1', 'scan')),
                   ],
                  id='small_array_100'),
     pytest.param(make_mock_type('INT',
                                 length=pytmc.record.MAX_ARCHIVE_ELEMENTS + 1,
                                 is_array=True),
                  'i', dict(archive='1s scan'), [],
                  id='large_array_1025'),
     ]
)
def test_archive(data_type, io, pragma, expected):
    record_package = get_record_package(data_type, io, pragma)
    print(record_package)
    archive_settings = list(pytmc.record.generate_archive_settings([record_package]))
    assert archive_settings == expected
    # pkg = pytmc.record.StringRecordPackage(851, )
