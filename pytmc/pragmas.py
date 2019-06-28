"""
xml_collector.py

This file contains the objects for intaking TMC files and generating python
interpretations. Db Files can be produced from the interpretation
"""
import re
import logging
import warnings

from jinja2 import Environment, PackageLoader

from collections import ChainMap, OrderedDict

logger = logging.getLogger(__name__)


# Select special delimiter sequences and prepare them for re injection
_FLEX_TERM_REGEX = "|".join([r";", r";;", r"[\n\r]", r"$"])

# Break configuration str into list of lines paired w/ their delimiters
_LINE_FINDER = re.compile(r"(?P<line>.+?)(?P<delim>" + _FLEX_TERM_REGEX + ")")
_LINE_PARSER = re.compile(r"(?P<title>[\S]+):(?:[^\S]*)(?P<tag>.*)")
_FIELD_FINDER = re.compile(r"(?P<f_name>[\S]+)(?:[^\S]*)(?P<f_set>.*)")


def split_pytmc_pragma(pragma_text):
    """
    Return dictionaries for each line.
    Derived from raw_config

    Parameters
    ----------
    raw_config : str
        completely unformatted string from configuration. Defaults to
        raw_config.

    Returns
    -------
    list
        This list contains a dictionary for each line broken up into two
        keys: 'title' and 'tag'.
    """
    conf_lines = [m.groupdict() for m in _LINE_FINDER.finditer(pragma_text)]

    # create list of lines information only. Strip out delimiters, empty lines
    result_no_delims = [r["line"] for r in conf_lines
                        if r["line"].strip()]

    # Break lines into list of dictionaries w/ title/tag structure
    result = [_LINE_PARSER.search(m).groupdict() for m in result_no_delims]

    # Strip out extra whitespace in the tag
    for line in result:
        line['tag'] = line['tag'].strip()

        # Split out fields into {'f_name': '...', 'f_set': '...'}
        if line['title'] == 'field':
            line['tag'] = split_field(line['tag'])

    return result


def split_field(field_line):
    """
    When applied to field line's tag, break the string into its own dict

    Parameters
    ----------
    string : str
        This is the string to be broken into field name and field setting

    Returns
    -------
    dict
        Keys are 'f_name' for the field name and 'f_set' for the
        corresponding setting.
    """
    return _FIELD_FINDER.search(field_line).groupdict()


def separate_configs_by_pv(config_lines):
    pv, config = None, None

    for line in config_lines:
        if line['title'] == 'pv':
            if config is not None:
                yield pv, config

            pv = line['tag']
            config = []

        if config is not None:
            config.append(line)

    if config is not None:
        yield pv, config


class Configuration:
    _cfg_header = 'pv'

    def __init__(self, pragma_text):
        self.pragma_text = pragma_text
        self.config_lines = split_pytmc_pragma(pragma_text)
        self.configs = dict(separate_configs_by_pv(self.config_lines))
