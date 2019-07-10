import pytest
import logging

from pytmc.pragmas import split_pytmc_pragma, separate_configs_by_pv

logger = logging.getLogger(__name__)


@pytest.fixture()
def leaf_bool_pragma_string():
    return """
                     pv: TEST:MAIN:NEW_VAR_OUT
                     type: bo
                     field: ZNAM	SINGLE
                     field: ONAM	MULTI
                     field:   SCAN	1 second
                     str: %d
                     io: o
                     init: True
                     pv: TEST:MAIN:NEW_VAR_IN
                     type:bi
                     field: ZNAM	SINGLE
                     field: ONAM	MULTI
                     field: SCAN	1 second
                     str: %d
                     io: i
    """


@pytest.fixture()
def leaf_bool_pragma_string_w_semicolon(leaf_bool_pragma_string):
    return leaf_bool_pragma_string + """
                     ensure: that ; semicolons: work;
    """


@pytest.fixture()
def leaf_bool_pragma_string_single_line():
    return """pv:pv_name"""


@pytest.fixture()
def light_leaf_bool_pragma_string():
    return """
                     pv: TEST:MAIN:NEW_VAR_OUT
                     io: o
                     pv: TEST:MAIN:NEW_VAR_IN
                     io: i
                     pv: TEST:MAIN:NEW_VAR_IO
                     io: io
                     pv: TEST:MAIN:NEW_VAR_SIMPLE
    """


@pytest.fixture(scope='function')
def branch_bool_pragma_string():
    return """
            pv: FIRST
            pv: SECOND
    """


@pytest.fixture(scope='function')
def branch_bool_pragma_string_empty(branch_bool_pragma_string):
    return branch_bool_pragma_string + """
            pv:
            pv:"""


@pytest.fixture(scope='function')
def branch_connection_pragma_string():
    return """
            pv: MIDDLE
            aux: nothing
    """


@pytest.fixture(scope='function')
def empty_pv_pragma_string():
    return """
            pv:
    """


@pytest.fixture(scope='function')
def branch_skip_pragma_string():
    return """
            skip:
    """


@pytest.mark.parametrize("model_set", [
    (0),
    (1),
])
def test_config_lines(leaf_bool_pragma_string_w_semicolon,
                      leaf_bool_pragma_string_single_line, model_set):
    if model_set == 0:
        string = leaf_bool_pragma_string_w_semicolon
        test = [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
            {'title': 'type', 'tag': 'bo'},
            {'title': 'field', 'tag': dict(f_name='ZNAM', f_set='SINGLE')},
            {'title': 'field', 'tag': dict(f_name='ONAM', f_set='MULTI')},
            {'title': 'field', 'tag': dict(f_name='SCAN', f_set='1 second')},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'o'},
            {'title': 'init', 'tag': 'True'},
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_IN'},
            {'title': 'type', 'tag': 'bi'},
            {'title': 'field', 'tag': dict(f_name='ZNAM', f_set='SINGLE')},
            {'title': 'field', 'tag': dict(f_name='ONAM', f_set='MULTI')},
            {'title': 'field', 'tag': dict(f_name='SCAN', f_set='1 second')},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'i'},
            {'title': 'ensure', 'tag': 'that'},
            {'title': 'semicolons', 'tag': 'work'},
        ]
    if model_set == 1:
        string = leaf_bool_pragma_string_single_line
        test = [{'title': "pv", 'tag': 'pv_name'}]

    assert split_pytmc_pragma(string) == test


def test_neaten_field(leaf_bool_pragma_string):
    config_lines = split_pytmc_pragma(leaf_bool_pragma_string)
    assert config_lines[2]['tag'] == {'f_name': 'ZNAM', 'f_set': 'SINGLE'}


def test_formatted_config_lines(leaf_bool_pragma_string):
    config_lines = split_pytmc_pragma(leaf_bool_pragma_string)
    assert config_lines == [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init', 'tag': 'True'},
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_IN'},
        {'title': 'type', 'tag': 'bi'},
        {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'i'},
    ]


def test_config_by_name(leaf_bool_pragma_string):
    config_lines = split_pytmc_pragma(leaf_bool_pragma_string)
    configs = dict(separate_configs_by_pv(config_lines))
    assert configs == {
        'TEST:MAIN:NEW_VAR_OUT': [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
            {'title': 'type', 'tag': 'bo'},
            {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
            {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
            {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'o'},
            {'title': 'init', 'tag': 'True'},
        ],
        'TEST:MAIN:NEW_VAR_IN': [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_IN'},
            {'title': 'type', 'tag': 'bi'},
            {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
            {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
            {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'i'},
        ]
    }


def test_config_names(leaf_bool_pragma_string):
    config_lines = split_pytmc_pragma(leaf_bool_pragma_string)
    configs = dict(separate_configs_by_pv(config_lines))
    assert set(configs) == {
        "TEST:MAIN:NEW_VAR_OUT",
        "TEST:MAIN:NEW_VAR_IN"
    }


def test_fix_to_config_name(leaf_bool_pragma_string):
    config_lines = split_pytmc_pragma(leaf_bool_pragma_string)
    configs = dict(separate_configs_by_pv(config_lines))
    assert configs['TEST:MAIN:NEW_VAR_OUT'] == [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init', 'tag': 'True'},
    ]


def test_get_config_lines(leaf_bool_pragma_string):
    config_lines = split_pytmc_pragma(leaf_bool_pragma_string)
    configs = dict(separate_configs_by_pv(config_lines))
    assert configs['TEST:MAIN:NEW_VAR_OUT'] == [
        {'tag': 'TEST:MAIN:NEW_VAR_OUT', 'title': 'pv'},
        {'tag': 'bo', 'title': 'type'},
        {'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}, 'title': 'field'},
        {'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}, 'title': 'field'},
        {'tag': {'f_name': 'SCAN', 'f_set': '1 second'}, 'title': 'field'},
        {'tag': '%d', 'title': 'str'},
        {'tag': 'o', 'title': 'io'},
        {'tag': 'True', 'title': 'init'},
    ]

    assert configs['TEST:MAIN:NEW_VAR_IN'] == [
         {'tag': 'TEST:MAIN:NEW_VAR_IN', 'title': 'pv'},
         {'tag': 'bi', 'title': 'type'},
         {'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}, 'title': 'field'},
         {'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}, 'title': 'field'},
         {'tag': {'f_name': 'SCAN', 'f_set': '1 second'}, 'title': 'field'},
         {'tag': '%d', 'title': 'str'},
         {'tag': 'i', 'title': 'io'},
    ]
