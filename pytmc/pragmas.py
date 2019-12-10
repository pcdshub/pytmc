"""
This file contains the objects for taking in pytmc-parsed TMC files and
generating Python-level configuration information.
"""
import itertools
import logging
import math
import re
from typing import Generator, Type, Union

from . import parser
from .record import RecordPackage

logger = logging.getLogger(__name__)


# Select special delimiter sequences and prepare them for re injection
_FLEX_TERM_END = [r";", r";;", r"[\n\r]", r"$"]
_FLEX_TERM_REGEX = "|".join(_FLEX_TERM_END)

# Break configuration str into list of lines paired w/ their delimiters
_LINE_FINDER = re.compile(r"(?P<line>.+?)(?P<delim>" + _FLEX_TERM_REGEX + ")")
_LINE_PARSER = re.compile(r"(?P<title>[\S]+):(?:[^\S]*)(?P<tag>.*)")
_FIELD_FINDER = re.compile(r"(?P<f_name>[\S]+)(?:[^\S]*)(?P<f_set>.*)")

# Valid options for 'io' in pragma:
IO_OUTPUT = ('output', 'io', 'o', 'rw')
IO_INPUT = ('input', 'i', 'ro')
KNOWN_BAD_TYPES = ('ALIAS', 'DATE', 'DATE_AND_TIME', 'DT', 'TIME',
                   'TIME_OF_DAY', 'TOD')


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


def dictify_config(conf, array_index=None, expand_default=':%.2d'):
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

    if array_index is not None:
        config['pv'] += config.get('expand', expand_default) % array_index

    return config


def expand_configurations_from_chain(chain, *, pragma: str = 'pytmc',
                                      allow_no_pragma=False):
    '''
    Generate all possible configuration combinations

    For example, from a chain with two items::

        [item1, item2]

    The latter of which has a configuration that creates two PVs (specified by
    configuration dictionaries config1, config2), this function will return::

        [
            [(item1, config1), (item2, config1)],
            [(item1, config1), (item2, config2)],
        ]

    Special handling for arrays of complex types will unroll the array into
    individual elements.  That is, `arr : ARRAY [1..5] of ST_Structure` will be
    unrolled into `arr[1]` through `arr[5]`.

    Returns
    -------
    tuple
        Tuple of tuples. See description above.
    
    '''
    result = []

    def dictify_scalar(item):
        for pvname, config in separate_configs_by_pv(
                split_pytmc_pragma('\n'.join(pragmas))):
            yield (item, dictify_config(config))

    def dictify_complex_array(item):
        low, high = item.array_info.bounds
        expand_digits = math.floor(math.log10(high)) + 2
        expand_default = f':%.{expand_digits}d'
        for pvname, config in separate_configs_by_pv(
                split_pytmc_pragma('\n'.join(pragmas))):
            for idx in range(low, high):
                yield (parser._ArrayItemProxy(item, idx),
                       dictify_config(config, array_index=idx,
                                      expand_default=expand_default))

    for item in chain:
        pragmas = list(get_pragma(item, name=pragma))
        if not pragmas:
            if allow_no_pragma:
                pragmas = [None]
            else:
                # If any pragma in the chain is unset, escape early
                return []

        if allow_no_pragma:
            result.append((item, None))
        else:
            if item.array_info and (item.data_type.is_complex_type or
                                    item.data_type.is_enum):
                dictify_func = dictify_complex_array
            else:
                dictify_func = dictify_scalar
            
        
            result.append(list(dictify_func(item)))
    
    print("result:")
    print(result)
    for x in result:
        print(len(x))

    return list(itertools.product(*result))


def squash_configs(*configs):
    '''
    Take a list of configurations, and squash them into one dictionary

    The key 'pv' will be a list of all PV segments found.

    Later configurations override prior ones.

    Parameters
    ----------
    *configs : list of dict
        Configurations to squash. Original configs will not be modified.
    '''
    squashed = {'pv': [], 'field': {}}
    for config in configs:
        # Shallow copy so that we don't modify the original
        config = dict(config)

        # Remove the PV portion - as it should be listified
        squashed['pv'].append(config.pop('pv', None))

        # Update the fields as a dictionary
        fields = config.pop('field', None)
        if fields:
            squashed['field'].update(fields)

        squashed.update(config)

    return squashed


def normalize_io(io):
    '''
    Normalize an 'io' specifier in a pragma into either 'input' or 'output'

    Parameters
    ----------
    io : string
        The I/O specifier from the pragma

    Returns
    -------
    {'input', 'output'}

    Raises
    ------
    ValueError
        If an invalid specifier is given
    '''
    if io in IO_OUTPUT:
        return 'output'
    if io in IO_INPUT:
        return 'input'
    raise ValueError('Invalid I/O specifier')


class SingularChain:
    '''
    A chain of data types, all with pytmc pragmas, representing a single piece
    of data that should be accessible via EPICS/ADS

    Parameters
    ----------
    item_to_config : dict
        Keys would be ``TwincatItem`` s such as Symbol, and values would be
        dictionary configurations from parsed pytmc pragmas.

    Attributes
    ----------
    item_to_config : dict
    chain : list
        The chain of items (i.e., item_to_config keys)
    tcname : str
        The full TwinCAT name of the item
    pvname : str
        The user-specified PV name
    last : list
        The last item, which determines the overall data type
    data_type : DataType
        The data type of the last item
    config : dict
        The final configuration based on the full chain of configurations
    '''

    def __init__(self, item_to_config):
        self.item_to_config = item_to_config
        self.chain = list(self.item_to_config)
        self.last = self.chain[-1]
        self.data_type = self.chain[-1].data_type
        self.array_info = self.chain[-1].array_info
        self.tcname = '.'.join(part.name for part in self.chain)

        self.config = squash_configs(*list(item_to_config.values()))
        self.pvname = ':'.join(pv_segment for pv_segment in self.config['pv']
                               if pv_segment)

    def __repr__(self):
        return (f'<{self.__class__.__name__} pvname={self.pvname!r} '
                f'tcname={self.tcname!r} config={self.config} '
                f'data_type={self.data_type!r})')


def find_pytmc_symbols(tmc, allow_no_pragma=False):
    'Find all symbols in a tmc file that contain pragmas'
    for symbol in tmc.find(parser.Symbol):
        if has_pragma(symbol) or allow_no_pragma:
            if symbol.name.count('.') == 1:
                yield symbol


def get_pragma(item: Union[parser.SubItem, Type[parser.Symbol]], *,
               name: str = 'pytmc') -> Generator[str, None, None]:
    """
    Get all pragmas with a certain tag.

    Parameters
    ----------
    item : parser.SubItem, parser.Symbol, parser.Symbol subclass
        Representation of beckhoff variable or data structure

    name : str, optional
        Accept tmc entries where the <Name> field equals the passed string

    Yields
    ------
    str

    """
    name_list = [
        name,
        'plcAttribute_{}'.format(name)
    ]
    if hasattr(item, 'Properties'):
        properties = item.Properties[0]
        for prop in getattr(properties, 'Property', []):
            # Return true if any of the names searched for are found
            if any(indiv_name == prop.name for indiv_name in name_list):
                yield prop.value


def has_pragma(item, *, name: str = 'pytmc'):
    'Does `item` have a pragma titled `name`?'

    return any(True for pragma in get_pragma(item, name=name)
               if pragma is not None)


def chains_from_symbol(symbol, *, pragma: str = 'pytmc', 
                       allow_no_pragma=False):
    'Build all SingularChain instances from a Symbol'
    if allow_no_pragma:
        condition = lambda *args, **kwargs: True
    else:
        condition = has_pragma
    for full_chain in symbol.walk(condition=condition):
        for item_and_config in expand_configurations_from_chain(
                full_chain, allow_no_pragma=allow_no_pragma):
            yield SingularChain(dict(item_and_config))


def record_packages_from_symbol(symbol, *, pragma: str = 'pytmc',
                                yield_exceptions=False,
                                allow_no_pragma=False):
    'Create all record packages from a given Symbol'
    for chain in chains_from_symbol(symbol, pragma=pragma, 
                                    allow_no_pragma=allow_no_pragma):
        print(chain)
        try:
            yield RecordPackage.from_chain(symbol.module.ads_port, chain=chain)
        except Exception as ex:
            if yield_exceptions:
                yield ex
            else:
                raise
