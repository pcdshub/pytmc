"""
xml_collector.py

This file contains the objects for intaking TMC files and generating python
interpretations. Db Files can be produced from the interpretation
"""
import itertools
import logging
import re

from . import parser
from .record import RecordPackage

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
    result_no_delims = [r["line"]
                        for r in conf_lines
                        if r["line"].strip()]

    # Break lines into list of dictionaries w/ title/tag structure
    result = [_LINE_PARSER.search(m).groupdict() for m in result_no_delims]

    for line in result:
        # Strip out extra whitespace in the tag and/or
        # split out fields into {'f_name': '...', 'f_set': '...'}
        tag = line['tag']
        line['tag'] = (split_field(tag.strip())
                       if line['title'] == 'field'
                       else tag.strip())

    return result


def split_field(string):
    """
    When applied to field line's tag, break the string into its own dict

    Parameters
    ----------
    string : str
        This is the string to be broken into field name and field setting

    Returns
    -------
    dict
        Keys are 'f_name' for the field name and 'f_set' for the corresponding
        setting.
    """
    return _FIELD_FINDER.search(string).groupdict()


def separate_configs_by_pv(config_lines):
    '''
    Take in a pre-parsed pragma such as::

        [{'title': 'pv', 'tag': 'a'},
         {'title': 'io', 'tag': 'io_for_a'},
         {'title': 'pv', 'tag': 'b'},
         {'title': 'io', 'tag': 'io_for_a'},
         ]

    Which was generated from::

        pv: a
        io: io_for_a
        pv: b
        io: io_for_b

    And yield the following::

        ('a', [{'title': 'io', 'tag': 'io_for_a'}])
        ('b', [{'title': 'io', 'tag': 'io_for_b'}])
    '''
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
    def __init__(self, pragma_text):
        self.pragma_text = pragma_text
        self.config_lines = split_pytmc_pragma(pragma_text)
        self.configs = dict(separate_configs_by_pv(self.config_lines))


def dictify_config(conf):
    '''
    Make a raw config list into an easier-to-use dictionary

    Example::
        [{'title': 'pv', 'tag': 'a'},
         {'title': 'io', 'tag': 'io_for_a'},
         {'title': 'field', 'tag': {'f_name': 'fieldname', 'f_set': 'value'}},
         ]

    Becomes::

        {'pv': 'a',
         'io': 'io_for_a',
         'field': {'fieldname': 'value'}}
    '''

    fields = {
        item['tag']['f_name']: item['tag']['f_set']
        for item in conf
        if item['title'] == 'field'
    }
    config = {item['title']: item['tag']
              for item in conf}
    if fields:
        config['field'] = fields
    return config


def all_configs(chain, *, pragma='pytmc'):
    '''
    Generate all possible configuration combinations
    '''
    result = []
    for item in chain:
        pragmas = get_pragma(item, name=pragma)
        if not pragmas:
            return []

        result.append([
            (item, dictify_config(config))
            for pvname, config in separate_configs_by_pv(
                split_pytmc_pragma('\n'.join(pragmas)))
        ])

    return list(itertools.product(*result))


def squash_configs(*configs):
    '''
    Take a list of configurations, and squash them into one dictionary

    The key 'pv' will be a list of all PV segments found.

    Later configurations override prior ones.
    '''
    squashed = {'pv': [], 'field': {}}
    for config in configs:
        pv_segment = config.pop('pv', None)
        if pv_segment:
            squashed['pv'].append(pv_segment)
        fields = config.pop('field', None)
        if fields:
            squashed['field'].update(fields)
        squashed.update(config)

    return squashed


class SingularChain:
    '''
    A chain of data types, all with pytmc pragmas, representing a single piece
    of data that should be accessible via EPICS/ADS
    '''
    def __init__(self, chain, configs):
        self.chain = list(chain)
        self.last = self.chain[-1]
        self.tcname = '.'.join(part.name for part in self.chain)

        self.configs = configs
        self.config = squash_configs(*configs)
        self.pvname = ':'.join(self.config['pv'])

    @property
    def data_type(self):
        return self.last.data_type

    def __repr__(self):
        return (f'<{self.__class__.__name__} pvname={self.pvname!r} '
                f'tcname={self.tcname!r} config={self.config} '
                f'data_type={self.data_type!r})')


def find_pytmc_symbols(tmc):
    'Find all symbols in a tmc file that contain pragmas'
    for symbol in tmc.find(parser.Symbol):
        if has_pragma(symbol):
            yield symbol


def get_pragma(item, *, name='pytmc'):
    'Get all pragmas with a certain tag'
    if hasattr(item, 'Properties'):
        properties = item.Properties[0]
        for prop in getattr(properties, 'Property', []):
            if prop.name == name:
                yield prop.value


def has_pragma(item, *, name='pytmc'):
    'Does `item` have a pragma titled `name`?'
    return any(True for _ in get_pragma(item, name=name))


def chains_from_symbol(symbol, *, pragma='pytmc'):
    'Build all SingularChain '
    for full_chain in symbol.walk(condition=has_pragma):
        for item_and_config in all_configs(full_chain):
            chain = [item for item, _ in item_and_config]
            configs = [config for _, config in item_and_config]
            yield SingularChain(chain=chain, configs=configs)


def record_packages_from_symbol(symbol, *, unroll=False):
    for chain in chains_from_symbol(symbol):
        data_type = chain.data_type
        array_info = getattr(chain.last, 'array_info', None)
        if unroll and (data_type.is_enum and array_info is not None):
            # TODO: proof-of-concept only unrolls enum when last in chain;
            # also, it's unclear as of yet how to support this on the IOC side
            pvname = chain.pvname
            tcname = chain.tcname
            for idx in range(*array_info.bounds):
                chain.tcname = f'{tcname}[{idx}]'
                chain.pvname = f'{pvname}_{idx}'
                yield RecordPackage.from_chain(symbol.module.ads_port,
                                               chain=chain)
        else:
            yield RecordPackage.from_chain(symbol.module.ads_port, chain=chain)
