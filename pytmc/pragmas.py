"""
This file contains the objects for taking in pytmc-parsed TMC files and
generating Python-level configuration information.
"""
import copy
import itertools
import logging
import math
import re
from collections.abc import Generator
from typing import Union

from . import parser
from .record import RecordPackage

logger = logging.getLogger(__name__)


# Break configuration str into list of lines paired w/ their delimiters
_LINE_FINDER = re.compile(r"(?P<line>.+?)(?P<delim>(?:[;\n\r]+|$))")
_LINE_PARSER = re.compile(r"(?P<title>[\S]+):(?:[^\S]*)(?P<tag>.*)")
_FIELD_FINDER = re.compile(r"(?P<f_name>[\S]+)(?:[^\S]*)(?P<f_set>.*)")

# Valid options for 'io' in pragma:
IO_OUTPUT = ('output', 'io', 'o', 'rw')
IO_INPUT = ('input', 'i', 'ro')
KNOWN_BAD_TYPES = ('ALIAS', 'DATE', 'DATE_AND_TIME', 'DT', 'TIME',
                   'TIME_OF_DAY', 'TOD')

_UPDATE_RE = re.compile(
    # Rate portion (e.g., 1 s, 1s, 1Hz, 1 Hz)
    r'^(?P<rate>\d*\.\d+|\d+)\s*(?P<hz_or_sec>hz|s)'
    # Poll or notify (or default)
    r'(\s+(?P<method>poll|notify))?$',
    flags=re.IGNORECASE
)

UPDATE_RATE_DEFAULT = {'frequency': 1, 'seconds': 1, 'method': 'poll'}
VALID_POLL_RATES_HZ = (1./50,  # 0.02Hz - 1 update every 50 seconds
                       1./10,  # 0.1 Hz - 1 update every 10 seconds
                       1./2,   # 0.5 Hz - 1 update every 2 seconds
                       1,      # 1.0 Hz - 1 update every 1 second (default)
                       2)      # 2.0 Hz - 2 updates every 1 second


_ARCHIVE_RE = re.compile(
    # Rate portion (e.g., 1 s, 1s, 1Hz, 1 Hz)
    r'^(?P<rate>\d*\.\d+|\d+)\s*(?P<hz_or_sec>hz|s)'
    # Poll or notify (or default)
    r'(\s+(?P<method>scan|monitor))?$',
    flags=re.IGNORECASE
)
ARCHIVE_DEFAULT = {'frequency': 1, 'seconds': 1, 'method': 'scan'}

# Special, reserved keys:
SUBITEM = '_subitem_'
PRAGMA = '_pragma_'
DISALLOWED_SUBITEMS = {'pv', SUBITEM, PRAGMA, 'field', 'link'}

# Default for array index expansion:
EXPAND_DEFAULT = ':%.2d'


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
    conf_lines = [m.groupdict()['line']
                  for m in _LINE_FINDER.finditer(pragma_text)]

    # create list of lines information only. Strip out delimiters, empty lines
    result_no_delims = [_LINE_PARSER.search(line)
                        for line in conf_lines
                        if line.strip()]

    # Break lines into list of dictionaries w/ title/tag structure
    if None in result_no_delims:
        invalid_lines = '\n'.join(
            f'--> | {line}' if _LINE_PARSER.search(line) is None
            else f'    | {line}'
            for line in conf_lines
        )
        raise ValueError(f'Found invalid pragma line(s):\n{invalid_lines}')

    def line_to_dict(match):
        """
        Strip out extra whitespace in the tag and/or split out fields into
        {'f_name': '...', 'f_set': '...'}
        """
        groupdict = match.groupdict()
        tag = groupdict['tag']
        groupdict['tag'] = (
            split_field(tag.strip())
            if groupdict['title'] == 'field' else tag.strip()
        )
        return groupdict

    return [line_to_dict(m) for m in result_no_delims]


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


def get_array_suffix(config, array_index, *, default=EXPAND_DEFAULT):
    '''
    Return array index suffix based on the expand settings in the config.
    '''
    return config.get('expand', default) % array_index


def dictify_config(raw_conf, array_index=None):
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

    title_tag_pairs = [(item['title'], item['tag']) for item in raw_conf]

    fields = {
        tag['f_name']: tag['f_set']
        for title, tag in title_tag_pairs
        if title == 'field'
    }

    config = {
        title: tag
        for title, tag in title_tag_pairs
        if '.' not in title  # Handle subitem entries specially
    }

    if fields:
        config['field'] = fields

    if array_index is not None:
        config['pv'] += get_array_suffix(config, array_index)

    def add_subitem(d, key, value):
        """Add a subitem `key: value` to dictionary `d`."""
        if '.' in key:
            # The first a.b.c.pragma indicate the sub-(sub-) item for 'pragma':
            child, remainder = key.split('.', 1)
            if child not in d:
                d[child] = {PRAGMA: []}
            return add_subitem(d[child], remainder, value)

        if key in DISALLOWED_SUBITEMS:
            raise ValueError(f'Unsupported pragma key in subitem: {key}')
        # The final key is a pytmc-supported pragma:
        d[PRAGMA].append((key, value))

    for title, tag in title_tag_pairs:
        if '.' in title:
            if SUBITEM not in config:
                config[SUBITEM] = {}
            add_subitem(config[SUBITEM], title, tag)

    return config


def _merge_subitems(target: dict, source: dict):
    """
    In-place merge `source` into `target`.

    Sub-item dictionaries, held at the top-level key ``_subitem_``, are nested
    dictionaries containing sub-item names or the special key ``_pragma_``,
    which can modify the pragma at the given level.

    For example::

        {'_subitem_': {'member1': {'_pragma_': [('key', '1')], ... }}}

    This top-level _subitem_ pragma dictionary contains a pragma ``key: 1``
    for the ".member1" member.  ``member1``, if structured, may also have
    keys in its dictionary named after its members.
    """
    if PRAGMA not in target:
        target[PRAGMA] = []

    for key, value in source.items():
        if key == PRAGMA:
            target[PRAGMA].extend(value)
        else:
            if key not in target:
                target[key] = {}
            _merge_subitems(target[key], value)


def _expand_configurations_from_chain(chain, *, pragma: str = 'pytmc',
                                      allow_no_pragma=False):
    """
    Wrapped by ``expand_configurations_from_chain``, usable for callers that
    don't want the full product of all configurations.
    """

    def handle_scalar(item, pvname, config):
        """Handler for scalar simple or structured items."""
        yield item, config

    def handle_array_complex(item, pvname, config):
        """Handler for arrays of structured items (or enums)."""
        low, high = item.array_info.bounds
        expand_digits = math.floor(math.log10(high)) + 2
        array_element_pragma = config.get('array', '')
        for idx in parse_array_settings(array_element_pragma, (low, high)):
            # shallow-copy; only touching the top level "pv" key
            idx_config = copy.copy(config)
            idx_config['pv'] += get_array_suffix(
                config, idx, default=f':%.{expand_digits}d')
            yield parser._ArrayItemProxy(item, idx), idx_config

    def get_all_options(subitems, handler, pragmas):
        split_pragma = split_pytmc_pragma('\n'.join(pragmas))
        for pvname, separated_cfg in separate_configs_by_pv(split_pragma):
            config = dictify_config(separated_cfg)

            # config will have the SUBITEM key, applicable to its level
            # in the hierarchy. If it exists, merge it with our current set.
            if SUBITEM in config:
                _merge_subitems(subitems, config[SUBITEM])

            for key, value in subitems.get(PRAGMA, []):
                config[key] = value

            yield from handler(item, pvname, config)

    # `subitems` keeps track of forward references with pragmas of members
    # and sub-members (and so on)
    subitems = {}

    for item in chain:
        subitems = subitems.get(item.name, {})
        pragmas = list(pragma for pragma in get_pragma(item, name=pragma)
                       if pragma is not None)
        if not pragmas:
            if allow_no_pragma:
                pragmas = [None]
                yield [(item, None)]
                continue

            # If any pragma in the chain is unset, escape early
            return []

        if item.array_info and (item.data_type.is_complex_type or
                                item.data_type.is_enum):
            options = get_all_options(subitems, handle_array_complex, pragmas)
        else:
            options = get_all_options(subitems, handle_scalar, pragmas)

        yield list(options)


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
    result = _expand_configurations_from_chain(
        chain, pragma=pragma, allow_no_pragma=allow_no_pragma
    )
    if not result:
        return []

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

    has_link = any('link' in config for config in configs
                   if config is not None)
    if has_link:
        squashed['link'] = []

    for config in configs:
        if config is None:
            squashed['pv'].append(None)
            continue
        # Shallow copy so that we don't modify the original
        config = dict(config)

        # Remove the PV portion - as it should be listified
        squashed['pv'].append(config.pop('pv', None))

        if has_link:
            squashed['link'].append(config.pop('link', None))

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
    io : str
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


def _parse_rate(rate, hz_or_sec):
    '''
    Parse rate into frequency and seconds

    Parameters
    ----------
    rate : str
        The pragma-specified rate.

    hz_or_sec : str
        {'hz', 's'}

    Returns
    -------
    dict
        With keys {'seconds', 'frequency'}
    '''

    try:
        rate = float(rate)
    except Exception:
        raise ValueError(f'Invalid rate: {rate}')

    if hz_or_sec == 'hz':
        freq, seconds = rate, 1.0 / rate
    elif hz_or_sec == 's':
        freq, seconds = 1.0 / rate, rate
    else:
        raise ValueError(f'Invalid hz_or_sec: {hz_or_sec}')

    return dict(
        frequency=int(freq) if int(freq) == freq else freq,
        seconds=int(seconds) if int(seconds) == seconds else seconds,
    )


def parse_update_rate(update, default=UPDATE_RATE_DEFAULT):
    '''
    Parse an 'update' specifier in a pragma

    Parameters
    ----------
    update : str
        The update rate specifier from the pragma.

    Returns
    -------
    dict
        With keys {'seconds', 'frequency', 'method'}
        Where 'method' is one of: {'poll', 'notify'}

    Raises
    ------
    ValueError
        If an invalid pragma is supplied
    '''
    update = update.lower().strip()
    res = dict(default)
    if update:
        match = _UPDATE_RE.match(update)
        if not match:
            raise ValueError(f'Invalid update specifier: {update}')

        # Method
        d = match.groupdict()
        method = d.get('method') or default['method']
        if method not in {'poll', 'notify'}:
            raise ValueError(f'Invalid update method: {method}')
        res['method'] = method

        # Rate + frequency/seconds
        res.update(_parse_rate(d['rate'], d['hz_or_sec']))

        if method == 'poll' and res['frequency'] not in VALID_POLL_RATES_HZ:
            raise ValueError(
                f"Invalid poll rate {res['frequency']}.  "
                f"Valid frequencies in Hz are: {VALID_POLL_RATES_HZ}"
            )

    return res


def parse_archive_settings(archive, default=ARCHIVE_DEFAULT):
    '''
    Parse an 'archive' specifier in a pragma

    Parameters
    ----------
    archive : str
        The archive specifier from the pragma.

    Returns
    -------
    dict
        With keys {'seconds', 'frequency', 'method'}
        Where 'method' is one of: {'scan', 'monitor'}

    Raises
    ------
    ValueError
        If an invalid pragma is supplied
    '''
    archive = archive.lower().strip()
    if archive in ('no', ):
        return None

    res = dict(default)
    if archive:
        match = _ARCHIVE_RE.match(archive)
        if not match:
            raise ValueError(f'Invalid archive specifier: {archive}')

        # Method
        d = match.groupdict()
        method = d.get('method') or default['method']
        if method not in {'scan', 'monitor'}:
            raise ValueError(f'Invalid archive method: {method}')

        res['method'] = method
        # Rate + frequency/seconds
        res.update(_parse_rate(d['rate'], d['hz_or_sec']))

    return res


def parse_array_settings(pragma, dimensions):
    '''
    Parse an 'array' specifier in a pragma, yielding array elements.

    Parameters
    ----------
    pragma : str
        The I/O specifier from the pragma.

    dimensions : 2-tuple
        Lower and upper-bound of the array corresponding to the pragma.

    Yields
    ------
    element : int
        Integer element of selected array indices.

    Raises
    ------
    ValueError
        If an invalid pragma is supplied
    '''
    pragma = pragma.strip()

    try:
        low, high = dimensions
    except Exception:
        raise ValueError(
            f'Invalid dimensions {dimensions!r} for array specifier in pragma '
            f'{pragma!r}'
        )

    if not pragma:
        yield from range(low, high + 1)
        return

    def _parse_element(elem):
        if '..' not in elem:
            return [int(elem)]

        # Split by .., such that this will support:
        #   ..to, from.., from..to, from..to..step
        range_args = [int(idx) if idx else None
                      for idx in elem.split('..')]

        # Ensure we have start, stop, step
        range_args += [None] * (3 - len(range_args))
        elem_low, elem_high, elem_step = range_args

        elem_low = low if elem_low is None else elem_low
        # Add one to make the exclusive upper bound inclusive:
        elem_high = high + 1 if elem_high is None else elem_high + 1
        elem_step = 1 if elem_step is None else elem_step
        return range(elem_low, elem_high, elem_step)

    try:
        for elem in pragma.split(','):
            for idx in _parse_element(elem):
                if not low <= idx <= high:
                    raise ValueError(
                        f'Array pragma index out of bounds: '
                        f'{low} < {elem} < {high}'
                    )
                yield idx
    except Exception as ex:
        raise ValueError(
            f'Invalid array pragma: {pragma} ({ex})'
        )


# Helpers which normalize various pragma values.
_normalizers = {
    'io': (normalize_io, 'io'),
    'update': (parse_update_rate, '1s poll'),
    'archive': (parse_archive_settings, '1s scan'),
}


def normalize_config(config):
    '''
    Parse and normalize pragma values into Python representations

    The following keys will be interpreted: ``io``, ``archive``, ``update``

    Parameters
    ----------
    config : dict
        The configuration

    Returns
    -------
    dict
        A shallow-copy of ``config`` with parsed and normalized values
    '''
    ret = dict(config)
    for key, (parser_func, default) in _normalizers.items():
        ret[key] = parser_func(ret.get(key, default))
    return ret


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

        self.valid = True

        for config in item_to_config:
            # Detect Nones signifying an incomplete pragma
            if item_to_config[config] is None:
                self.valid = False

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


def get_pragma(item: Union[parser.SubItem, type[parser.Symbol]], *,
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
        f'plcAttribute_{name}'
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


def always_true(*a, **kwargs):
    return True


def chains_from_symbol(symbol, *, pragma: str = 'pytmc',
                       allow_no_pragma=False):
    'Build all SingularChain instances from a Symbol'
    if allow_no_pragma:
        condition = always_true
    else:
        condition = has_pragma
    for full_chain in symbol.walk(condition=condition):
        configs = itertools.product(
            *_expand_configurations_from_chain(full_chain,
                                               allow_no_pragma=allow_no_pragma)
        )
        for item_and_config in configs:
            yield SingularChain(dict(item_and_config))


def record_packages_from_symbol(symbol, *, pragma: str = 'pytmc',
                                yield_exceptions=False,
                                allow_no_pragma=False):
    'Create all record packages from a given Symbol'
    try:
        ads_port = symbol.module.ads_port
        for chain in chains_from_symbol(symbol, pragma=pragma,
                                        allow_no_pragma=allow_no_pragma):
            try:
                yield RecordPackage.from_chain(ads_port, chain=chain)
            except Exception as ex:
                if yield_exceptions:
                    yield type(ex)(f"Symbol {symbol.name} "
                                   f"chain: {chain.tcname}: {ex}")
                else:
                    raise
    except Exception as ex:
        if yield_exceptions:
            yield type(ex)(f"Symbol {symbol.name} failure: {ex}")
        else:
            raise


def _attach_pragma(item, name, value):
    """Attach a pragma to a TwincatItem using `_make_fake_item`."""
    if not hasattr(item, 'Properties'):
        properties = parser._make_fake_item('Properties', parent=item)
        properties.Property = []
        item.Properties = [properties]

    properties = item.Properties[0]
    prop = parser._make_fake_item('Property', parent=properties, text=value,
                                  item_name=name)
    properties.Property.append(prop)
    return prop


class _FakeSymbol(parser.Symbol):
    @property
    def data_type(self):
        return self._data_type

    @property
    def qualified_type_name(self):
        return self._data_type.qualified_type

    @property
    def type_name(self):
        return self._data_type.name

    @property
    def BitSize(self):
        return self._data_type.BitSize


def make_fake_symbol_from_data_type(
        data_type, symbol_pragma_text, *, name='$(SYMBOL)',
        pragma_name: str = 'pytmc',
        data_area_index=0, tmc=None,
        create_data_area_if_needed=True):
    """
    Create a :class:`_FakeSymbol` from the given data type.

    Parameters
    ----------
    data_type : pytmc.parser.DataType
        The TMC data type.

    symbol_pragma_text : str
        The pragma text to attach.

    name : str, optional
        The symbol name.

    pragma_name : str, optional
        The pragma name to use (defaults to "pytmc").

    data_area_index : int, optional
        The data area to pretend the symbol exists in.
    """
    if tmc is None:
        # If defined in a .tmc file, this is the obvious choice.
        tmc = data_type.tmc
        if tmc is None:
            # Fallback to the first .tmc we find.  This really should be an
            # error condition, but given that we're making fake symbols anyway
            # it _probably_ doesn't matter.
            project = data_type.find_ancestor(parser.TcSmProject)
            for plc in project.plcs:
                tmc = plc.tmc
                if tmc is not None:
                    break

    if tmc is None:
        raise ValueError('Unable to find a tmc to insert the symbol')

    # TODO: does data area make a difference?
    data_areas = list(tmc.find(parser.DataArea))
    if not data_areas:
        if not create_data_area_if_needed:
            raise ValueError('No data area found to create symbol')
        data_area = tmc.create_data_area()
    else:
        data_area = data_areas[data_area_index]

    sym = parser._make_fake_item('_FakeSymbol', parent=data_area,
                                 item_name=name)
    sym._data_type = data_type
    sym.BitOffs = parser._make_fake_item('BitOffs', parent=sym, text='0')
    _attach_pragma(sym, pragma_name, symbol_pragma_text)
    return sym
