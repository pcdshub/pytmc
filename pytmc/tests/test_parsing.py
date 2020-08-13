import pytest
from .conftest import TEST_PATH

from pytmc.parser import get_pou_call_blocks, variables_from_declaration, parse


@pytest.mark.parametrize(
    'decl, expected',
    [
        pytest.param(
            '''
               PROGRAM Main
               VAR
                  M1: FB_DriveVirtual;
                  M1Link: FB_NcAxis;
                  bLimitFwdM1 AT %I*: BOOL;
                  bLimitBwdM1 AT %I*: BOOL;
               END_VAR
            ''',
            {'M1':  {'spec': '', 'type': 'FB_DriveVirtual'},
             'M1Link':  {'spec': '', 'type': 'FB_NcAxis'},
             'bLimitFwdM1': {'spec': '%I*', 'type': 'BOOL'},
             'bLimitBwdM1': {'spec': '%I*', 'type': 'BOOL'},
             },
            id='prog1'
        ),
        pytest.param(
            '''
               PROGRAM Main
               VAR
                  M1, M2: FB_DriveVirtual;
                  M1Link: FB_NcAxis;
                  bLimitFwdM1 AT %I*: BOOL;
                  bLimitBwdM1, Foobar AT %I*: BOOL;
               END_VAR
            ''',
            {'M1':  {'spec': '', 'type': 'FB_DriveVirtual'},
             'M2':  {'spec': '', 'type': 'FB_DriveVirtual'},
             'M1Link':  {'spec': '', 'type': 'FB_NcAxis'},
             'bLimitFwdM1': {'spec': '%I*', 'type': 'BOOL'},
             'bLimitBwdM1': {'spec': '%I*', 'type': 'BOOL'},
             'Foobar': {'spec': '%I*', 'type': 'BOOL'},
             },
            id='prog1_with_commas'
        ),
        pytest.param(
            '''
               PROGRAM Main
               VAR
                   engine      AT %QX0.0: BOOL;
                   deviceUp    AT %QX0.1: BOOL;
                   deviceDown  AT %QX0.2: BOOL;
                   timerUp:               TON;
                   timerDown:             TON;
                   steps:                 BYTE;
                   count:                 UINT := 0;
                   devSpeed:              TIME := t#10ms;
                   devTimer:              TP;
                   switch:                BOOL;
               END_VAR
            ''',
            {'engine': {'spec': '%QX0.0', 'type': 'BOOL'},
             'deviceUp': {'spec': '%QX0.1', 'type': 'BOOL'},
             'deviceDown': {'spec': '%QX0.2', 'type': 'BOOL'},
             'timerUp': {'spec': '', 'type': 'TON'},
             'timerDown': {'spec': '', 'type': 'TON'},
             'steps': {'spec': '', 'type': 'BYTE'},
             'count': {'spec': '', 'type': 'UINT', 'value': '0'},
             'devSpeed': {'spec': '', 'type': 'TIME', 'value': 't#10ms'},
             'devTimer': {'spec': '', 'type': 'TP'},
             'switch': {'spec': '', 'type': 'BOOL'},
             },
            id='berkoff_xtreme_vars'
        ),
        pytest.param(
            '''
            PROGRAM Main
            VAR
                arr1 at %I*: ARRAY [1..5] OF INT := 1,2,3,4,5;
            END_VAR
            ''',
            {'arr1': {'spec': '%I*', 'type': 'ARRAY [1..5] OF INT', 'value': '1,2,3,4,5'},
             },
            id='int_array'
        ),
        pytest.param(
            '''
            PROGRAM Main
            VAR
                TYPE STRUCT1:
                STRUCT
                    p1:int;
                    p2:int;
                    p3:dword;
                END_STRUCT
                END_TYPE
                arr1 : ARRAY[1..3] OF STRUCT1:= [(p1:=1,p2:=10,p3:=4723), (p1:=2,p2:=0,p3:=299), (p1:=14,p2:=5,p3:=112)];
            END_VAR
            ''',
            {'arr1': {'spec': '',
                      'type': 'ARRAY[1..3] OF STRUCT1',
                      'value': '[(p1:=1,p2:=10,p3:=4723), (p1:=2,p2:=0,p3:=299), (p1:=14,p2:=5,p3:=112)]'},
             },
            id='structs',
        ),
        pytest.param(
            '''
            PROGRAM Main
            VAR
                TYPE STRUCT1 :
                STRUCT
                    p1:int;
                    p2:int;
                    p3:dword;
                END_STRUCT
                END_TYPE
                arr1 : ARRAY[1..3] OF STRUCT1:= [(p1:=1,p2:=10,p3:=4723),
                (p1:=2,p2:=0,p3:=299),
                (p1:=14,p2:=5,p3:=112)];
            END_VAR
            ''',
            {'arr1': {'spec': '',
                      'type': 'ARRAY[1..3] OF STRUCT1',
                      'value': '[(p1:=1,p2:=10,p3:=4723), (p1:=2,p2:=0,p3:=299), (p1:=14,p2:=5,p3:=112)]'},
             },
            id='multiline_structs',
            marks=pytest.mark.xfail,
        ),
     ]
)
def test_variables_from_declaration(decl, expected):
    assert variables_from_declaration(decl) == expected


def test_call_blocks():
    decl = '''
        PROGRAM Main
        VAR
                M1: FB_DriveVirtual;
                M1Link: FB_NcAxis;
                bLimitFwdM1 AT %I*: BOOL;
                bLimitBwdM1 AT %I*: BOOL;

        END_VAR
    '''

    impl = '''
        M1Link(En := TRUE);
        M1(En := TRUE,
           bEnable := TRUE,
           bLimitFwd := bLimitFwdM1,
           bLimitBwd := bLimitBwdM1,
           Axis := M1Link.axis);

        M1(En := FALSE);
    '''

    assert get_pou_call_blocks(decl, impl) == {
        'M1': {'En': 'FALSE',
               'bEnable': 'TRUE',
               'bLimitFwd': 'bLimitFwdM1',
               'bLimitBwd': 'bLimitBwdM1',
               'Axis': 'M1Link.axis'},
        'M1Link': {'En': 'TRUE'}
    }


def test_route_parsing():
    # located in: C:\twincat\3.1\StaticRoutes.xml
    routes = parse(TEST_PATH / 'static_routes.xml')
    remote_connections = routes.RemoteConnections[0]
    assert remote_connections.by_name == {
        'LAMP-VACUUM': {
            'Name': 'LAMP-VACUUM',
            'Address': '172.21.37.140',
            'NetId': '5.21.50.18.1.1',
            'Type': 'TCP_IP'
        },
        'AMO-BASE': {
            'Name': 'AMO-BASE',
            'Address': '172.21.37.114',
            'NetId': '5.17.65.196.1.1',
            'Type': 'TCP_IP'
        },
    }

    assert remote_connections.by_address == {
        '172.21.37.114': {'Address': '172.21.37.114',
                          'Name': 'AMO-BASE',
                          'NetId': '5.17.65.196.1.1',
                          'Type': 'TCP_IP'},
        '172.21.37.140': {'Address': '172.21.37.140',
                          'Name': 'LAMP-VACUUM',
                          'NetId': '5.21.50.18.1.1',
                          'Type': 'TCP_IP'}
        }

    assert remote_connections.by_ams_id == {
        '5.17.65.196.1.1': {
            'Address': '172.21.37.114',
            'Name': 'AMO-BASE',
            'NetId': '5.17.65.196.1.1',
            'Type': 'TCP_IP'
        },
        '5.21.50.18.1.1': {
            'Address': '172.21.37.140',
            'Name': 'LAMP-VACUUM',
            'NetId': '5.21.50.18.1.1',
            'Type': 'TCP_IP'
        },
    }
