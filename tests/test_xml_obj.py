import pytest
import logging

import xml.etree.ElementTree as ET

from pytmc import Configuration
from collections import defaultdict

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("model_set", [
    (0),
    (1),
])
def test_Configuration_config_lines(leaf_bool_pragma_string_w_semicolon,
                                    leaf_bool_pragma_string_single_line, model_set):
    if model_set is 0:
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
    if model_set is 1:
        string = leaf_bool_pragma_string_single_line
        test = [{'title': "pv", 'tag': 'pv_name'}]

    print(type(string))
    print(string)
    cfg = Configuration(string)
    assert cfg.config_lines == test


def test_Configuration_neaten_field(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    cfg_lines = cfg._config_lines()
    result = cfg._neaten_field(cfg_lines[2]['tag'])

    assert result == {'f_name': 'ZNAM', 'f_set': 'SINGLE'}


def test_Configuration_formatted_config_lines(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    assert cfg.config_lines == [
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


def test_Configuration_config_by_name(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg._config_by_name()
    assert result == [
        [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
            {'title': 'type', 'tag': 'bo'},
            {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
            {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
            {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'o'},
            {'title': 'init', 'tag': 'True'},
        ],
        [
            {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_IN'},
            {'title': 'type', 'tag': 'bi'},
            {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
            {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
            {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
            {'title': 'str', 'tag': '%d'},
            {'title': 'io', 'tag': 'i'},
        ]
    ]


def test_Configuration_select_config_by_name(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg._select_config_by_name('TEST:MAIN:NEW_VAR_OUT')
    assert result == [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init', 'tag': 'True'},
    ]


def test_Configuration_config_names(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    result = cfg.config_names()
    assert result == [
        "TEST:MAIN:NEW_VAR_OUT",
        "TEST:MAIN:NEW_VAR_IN"
    ]


def test_Configuration_fix_to_config_name(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    assert cfg.configs['TEST:MAIN:NEW_VAR_OUT'] == [
        {'title': 'pv', 'tag': 'TEST:MAIN:NEW_VAR_OUT'},
        {'title': 'type', 'tag': 'bo'},
        {'title': 'field', 'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}},
        {'title': 'field', 'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}},
        {'title': 'field', 'tag': {'f_name': 'SCAN', 'f_set': '1 second'}},
        {'title': 'str', 'tag': '%d'},
        {'title': 'io', 'tag': 'o'},
        {'title': 'init', 'tag': 'True'},
    ]


def test_Configuration_add_config_line(branch_bool_pragma_string):
    cfg = Configuration(branch_bool_pragma_string)
    cfg.add_config_line('pv', 'THIRD')
    assert cfg.config == [
        {'title': 'pv', 'tag': 'FIRST'},
        {'title': 'pv', 'tag': 'SECOND'},
        {'title': 'pv', 'tag': 'THIRD'},
    ]


def test_Configuration_add_config_field(branch_bool_pragma_string):
    cfg = Configuration(branch_bool_pragma_string)
    cfg.add_config_field('ABC', 'XYZ', 1)
    assert cfg.config == [
        {'title': 'pv', 'tag': 'FIRST'},
        {'title': 'field', 'tag': {'f_name': 'ABC', 'f_set': '"XYZ"'}},
        {'title': 'pv', 'tag': 'SECOND'},
    ]


def test_Configuration_get_config_lines(leaf_bool_pragma_string):
    cfg = Configuration(leaf_bool_pragma_string)
    assert cfg.configs['TEST:MAIN:NEW_VAR_OUT'] == [
        {'tag': 'TEST:MAIN:NEW_VAR_OUT', 'title': 'pv'},
        {'tag': 'bo', 'title': 'type'},
        {'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}, 'title': 'field'},
        {'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}, 'title': 'field'},
        {'tag': {'f_name': 'SCAN', 'f_set': '1 second'}, 'title': 'field'},
        {'tag': '%d', 'title': 'str'},
        {'tag': 'o', 'title': 'io'},
        {'tag': 'True', 'title': 'init'},
    ]

    assert cfg.configs['TEST:MAIN:NEW_VAR_IN'] == [
         {'tag': 'TEST:MAIN:NEW_VAR_IN', 'title': 'pv'},
         {'tag': 'bi', 'title': 'type'},
         {'tag': {'f_name': 'ZNAM', 'f_set': 'SINGLE'}, 'title': 'field'},
         {'tag': {'f_name': 'ONAM', 'f_set': 'MULTI'}, 'title': 'field'},
         {'tag': {'f_name': 'SCAN', 'f_set': '1 second'}, 'title': 'field'},
         {'tag': '%d', 'title': 'str'},
         {'tag': 'i', 'title': 'io'},
    ]
