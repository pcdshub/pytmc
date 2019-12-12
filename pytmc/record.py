"""
Record generation and templating
"""
import logging

from jinja2 import Environment, PackageLoader

from typing import Optional

from collections import ChainMap, OrderedDict

from .default_settings.unified_ordered_field_list import unified_lookup_list

logger = logging.getLogger(__name__)


class EPICSRecord:
    """Representation of a single EPICS Record"""

    def __init__(self, pvname, record_type, direction, fields=None,
                 template=None, autosave=None):
        self.pvname = pvname
        self.record_type = record_type
        self.direction = direction
        self.fields = OrderedDict(fields) if fields is not None else {}
        self.template = template or 'asyn_standard_record.jinja2'
        self.autosave = dict(autosave) if autosave else {}

        # Load jinja templates
        self.jinja_env = Environment(
            loader=PackageLoader("pytmc", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.record_template = self.jinja_env.get_template(
            self.template
        )

    def update_autosave_from_pragma(self, config):
        """
        Update autosave settings from a pragma configuration

        To apply to either input or output records, pragma keys
        `autosave_pass0` or `autosave_pass1` can be used.

        To only apply to input records, pragma keys `autosave_input_pass0`
        `autosave_input_pass1` can be used.

        To only apply to output records, pragma keys `autosave_output_pass0`
        `autosave_output_pass1` can be used.

        Parameters
        ----------
        config : dict
            The pragma configuration dictionary
        """
        for pass_ in [0, 1]:
            for config_key in [f'autosave_pass{pass_}',
                               f'autosave_{self.direction}_pass{pass_}']:
                if config_key in config:
                    record_key = f'pass{pass_}'
                    fields = set(config[config_key].split(' '))
                    self.autosave[record_key] = fields

    def render(self, sort: bool = True):
        """Render the provided template"""
        for field, value in list(self.fields.items()):
            self.fields[field] = str(value).strip('"')

        if sort:
            self.fields = sort_fields(self.fields)

        return self.record_template.render(record=self)

    def __repr__(self):
        return (f"EPICSRecord({self.pvname!r}, "
                f"record_type={self.record_type!r})")


class RecordPackage:
    """
    Base class to be inherited by all other RecordPackages

    The subclass must implement the :attr:`.records` property which returns the
    :class:`.EPICSRecord` objects which will be rendered from the package.
    Optionally, ``RecordPackage`` can have a ``configure`` method which does
    the necessary setup before the record can be configured.
    """
    _required_keys = {}
    _required_fields = {}

    def __init__(self, ads_port, chain=None, origin=None):
        """
        All subclasses should use super on their init method.
        """
        self.tcname = chain.tcname
        self.chain = chain
        self.ads_port = ads_port

        # Due to a twincat pragma limitation, EPICS macro prefix '$' cannot be
        # used or escaped.  Allow the configuration to specify an alternate
        # character in the pragma, defaulting to '@'.
        try:
            macro_character = self.chain.config.get('macro_character', '@')
            self.pvname = chain.pvname.replace(macro_character, '$')
        except AttributeError:
            if self.chain.config is None:
                self.pvname = None
            else:
                raise

    @property
    def valid(self):
        """
        Returns
        -------
        bool
            Returns true if this record is fully specified and valid.
        """
        if self.pvname is None or not self.chain.valid:
            return False
        has_required_keys = all(self.chain.config.get(key)
                                for key in self._required_keys)

        fields = self.chain.config.get('field', {})
        has_required_fields = all(fields.get(key)
                                  for key in self._required_fields)
        return has_required_keys and has_required_fields

    @property
    def records(self):
        """Generated :class:`.EPICSRecord` objects"""
        raise NotImplementedError()

    def render(self):
        """
        Returns
        -------
        string
            Jinja rendered entry for the RecordPackage
        """
        if not self.valid:
            logger.error('Unable to render record: %s', self)
            return
        return '\n\n'.join([record.render().strip()
                            for record in self.records])

    @staticmethod
    def from_chain(*args, chain, **kwargs):
        """Select the proper subclass of ``TwincatRecordPackage`` from chain"""
        data_type = chain.data_type
        if not chain.valid:
            spec=RecordPackage
        elif data_type.is_enum:
            spec = EnumRecordPackage
        elif data_type.is_array or chain.last.array_info:
            spec = WaveformRecordPackage
        elif data_type.is_string:
            spec = StringRecordPackage
        else:
            try:
                spec = data_types[data_type.name]
            except KeyError:
                raise ValueError(
                    f'Unsupported data type {data_type.name} in chain: '
                    f'{chain.tcname} record: {chain.pvname}'
                ) from None
        return spec(*args, chain=chain, **kwargs)


class TwincatTypeRecordPackage(RecordPackage):
    """
    The common parent for all RecordPackages for basic Twincat types

    This main purpose of this class is to handle the parsing of the pragma
    chains that will be shared among all variable types. This includes setting
    the appropriate asyn port together and handling the "io" directionality. If
    you have a :class:`.TmcChain` but are not certain which class is
    appropriate use the :meth:`.from_chain` class constructor and the correct
    subclass will be chosen based on the given variable information.

    In order to subclass:

    1. :attr:`.input_rtyp` and :attr:`.output_rtyp` need to be provided. These
       are the EPICS RTYPs that are necessary for input and output variables.
    2. If there are default values for fields, these can be provided in the
       :attr:`.field_defaults`. Setting this on a subclass will only override
       fields in parent classes that are redundant. In other words,
       ``default_fields`` are inherited if not explicitly overwritten. Also
       note that these defaults are applied to both the input and output
       records.
    3. :attr:`.dtyp` needs to be set to the appropriate value for the Twincat
       type.
    4. The :meth:`.generate_input_record` and :meth:`.generate_output_record`
       functions can be subclasses if further customisation is needed. This is
       not required.
    """
    field_defaults = {'PINI': 1, 'TSE': -2}
    autosave_defaults = {
        'input': dict(pass0={},
                      pass1={}),
        'output': dict(pass0={'VAL'},
                       pass1={}),
    }

    dtyp = NotImplemented
    input_rtyp = NotImplemented
    output_rtyp = NotImplemented

    def __init_subclass__(cls, **kwargs):
        """Magic to have field_defaults be the combination of hierarchy"""
        super().__init_subclass__(**kwargs)
        # Create an empty set of defaults if not provided
        if not hasattr(cls, 'field_defaults'):
            cls.field_defaults = {}
        # Walk backwards through class hierarchy
        for parent in reversed(cls.mro()):
            # When we find a class with field_defaults append our own
            if hasattr(parent, 'field_defaults'):
                cls.field_defaults = dict(ChainMap(cls.field_defaults,
                                                   parent.field_defaults))
                break

    @property
    def io_direction(self):
        """
        Determine the direction based on the `io` config lines

        Returns
        -------
        direction : str
            {'input', 'output'}

        Raises
        ------
        ValueError
            If unable to determine IO direction
        """
        from .pragmas import normalize_io
        io = self.chain.config.get('io', 'io')
        try:
            return normalize_io(io)
        except ValueError:
            logger.warning('Invalid i/o direction for %s: %r', self.pvname, io)
            return 'input'

    @property
    def _asyn_port_spec(self):
        """Asyn port specification without io direction"""
        return f'@asyn($(PORT),0,1)ADSPORT={self.ads_port}/{self.tcname}'

    def generate_input_record(self):
        """
        Generate the record to read values into to the IOC

        Returns
        -------
        record: :class:`.EpicsRecord`
            Description of input record
        """
        # Base record with defaults
        if self.pvname and not self.pvname.endswith('RBV'):
            pvname = self.pvname + '_RBV'
        else:
            pvname = self.pvname

        record = EPICSRecord(pvname,
                             self.input_rtyp,
                             'input',
                             fields=self.field_defaults,
                             autosave=self.autosave_defaults.get('input')
                             )

        # Add our port
        record.fields['INP'] = self._asyn_port_spec + '?'
        record.fields['DTYP'] = self.dtyp
        record.fields['SCAN'] = 'I/O Intr'

        # Update with given pragmas
        record.fields.update(self.chain.config.get('field', {}))
        record.update_autosave_from_pragma(self.chain.config)
        return record

    def generate_output_record(self):
        """
        Generate the record to write values back to the PLC

        This will only be called if the ``io_direction`` is set to ``"output"``

        Returns
        -------
        record: :class:`.EpicsRecord`
            Description of output record
        """
        # Base record with defaults
        record = EPICSRecord(self.pvname,
                             self.output_rtyp,
                             'output',
                             fields=self.field_defaults,
                             autosave=self.autosave_defaults.get('output')
                             )
        # Add our port
        record.fields['DTYP'] = self.dtyp
        record.fields['OUT'] = self._asyn_port_spec + '='

        # Remove timestamp source and process-on-init for output records:
        record.fields.pop('TSE', None)
        record.fields.pop('PINI', None)

        # Update with given pragmas
        record.fields.update(self.chain.config.get('field', {}))
        record.update_autosave_from_pragma(self.chain.config)
        return record

    @property
    def records(self):
        """All records that will be created in the package"""
        records = [self.generate_input_record()]
        if self.io_direction == 'output':
            records.append(self.generate_output_record())
        return records


class BinaryRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for a binary Twincat Variable"""
    input_rtyp = 'bi'
    output_rtyp = 'bo'
    dtyp = 'asynInt32'
    field_defaults = {'ZNAM': 'Zero', 'ONAM': 'One'}


class IntegerRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for an integer Twincat Variable"""
    input_rtyp = 'longin'
    output_rtyp = 'longout'
    dtyp = 'asynInt32'


class FloatRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for a floating point Twincat Variable"""
    input_rtyp = 'ai'
    output_rtyp = 'ao'
    dtyp = 'asynFloat64'
    field_defaults = {'PREC': '3'}
    autosave_defaults = {
        'input': dict(pass0={'PREC'},
                      pass1={}),
        'output': dict(pass0={'VAL', 'PREC'},
                       pass1={}),
    }


class EnumRecordPackage(TwincatTypeRecordPackage):
    """Create a set of record for a ENUM Twincat Variable"""
    input_rtyp = 'mbbi'
    output_rtyp = 'mbbo'
    dtyp = 'asynInt32'

    mbb_fields = [
        ('ZRVL', 'ZRST'),
        ('ONVL', 'ONST'),
        ('TWVL', 'TWST'),
        ('THVL', 'THST'),
        ('FRVL', 'FRST'),
        ('FVVL', 'FVST'),
        ('SXVL', 'SXST'),
        ('SVVL', 'SVST'),
        ('EIVL', 'EIST'),
        ('NIVL', 'NIST'),
        ('TEVL', 'TEST'),
        ('ELVL', 'ELST'),
        ('TVVL', 'TVST'),
        ('TTVL', 'TTST'),
        ('FTVL', 'FTST'),
        ('FFVL', 'FFST'),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data_type = self.chain.data_type

        self.field_defaults = dict(self.field_defaults)
        for (val_field, string_field), (val, string) in zip(
                self.mbb_fields,
                sorted(data_type.enum_dict.items())):
            self.field_defaults.setdefault(val_field, val)
            self.field_defaults.setdefault(string_field, string)


class WaveformRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for a Twincat Array"""
    input_rtyp = 'waveform'
    output_rtyp = 'waveform'

    @property
    def ftvl(self):
        """Field type of value"""
        ftvl = {'BOOL': 'CHAR',
                'INT': 'SHORT',
                'ENUM': 'SHORT',
                'DINT': 'LONG',
                'REAL': 'FLOAT',
                'LREAL': 'DOUBLE'}
        return ftvl[self.chain.data_type.name]

    @property
    def nelm(self):
        """Number of elements in record"""
        if self.chain.data_type.is_array:
            return self.chain.data_type.length
        return self.chain.array_info.elements

    @property
    def dtyp(self):
        """
        Add field specifying DTYP without specifying array direction

        The following is taken from the EPICS wiki: "This field specifies the
        device type for the record. Each record type has its own set of device
        support routines which are specified in devSup.ASCII. If a record type
        does not have any associated device support, DTYP and DSET are
        meaningless."
        """

        # Assumes ArrayIn/ArrayOut will be appended
        data_types = {'BOOL': 'asynInt8',
                      'BYTE': 'asynInt8',
                      'SINT': 'asynInt8',
                      'USINT': 'asynInt8',

                      'WORD': 'asynInt16',
                      'INT': 'asynInt16',
                      'UINT': 'asynInt16',

                      'DWORD': 'asynInt32',
                      'DINT': 'asynInt32',
                      'UDINT': 'asynInt32',
                      'ENUM': 'asynInt16',  # -> Int32?

                      'REAL': 'asynFloat32',
                      'LREAL': 'asynFloat64'}

        return data_types[self.chain.data_type.name]

    def generate_input_record(self):
        record = super().generate_input_record()
        record.fields['DTYP'] += 'ArrayIn'
        record.fields['FTVL'] = self.ftvl
        record.fields['NELM'] = self.nelm
        return record

    def generate_output_record(self):
        record = super().generate_output_record()
        record.fields['DTYP'] += 'ArrayOut'
        record.fields['FTVL'] = self.ftvl
        record.fields['NELM'] = self.nelm
        # Waveform records only have INP fields!
        record.fields['INP'] = record.fields.pop('OUT')
        return record


class StringRecordPackage(TwincatTypeRecordPackage):
    """RecordPackage for broadcasting string values"""
    input_rtyp = 'waveform'
    output_rtyp = 'waveform'
    dtyp = 'asynInt8'
    field_defaults = {'FTVL': 'CHAR'}

    @property
    def nelm(self):
        """Number of elements in record"""
        return self.chain.data_type.length or '81'

    def generate_input_record(self):
        record = super().generate_input_record()
        record.fields['DTYP'] += 'ArrayIn'
        record.fields['NELM'] = self.nelm
        return record

    def generate_output_record(self):
        record = super().generate_output_record()
        # Waveform records only have INP fields!
        record.fields['DTYP'] += 'ArrayOut'
        record.fields['INP'] = record.fields.pop('OUT')
        record.fields['NELM'] = self.nelm
        return record


data_types = {
    'BOOL': BinaryRecordPackage,
    'BYTE': IntegerRecordPackage,
    'SINT': IntegerRecordPackage,
    'USINT': IntegerRecordPackage,

    'WORD': IntegerRecordPackage,
    'INT': IntegerRecordPackage,
    'UINT': IntegerRecordPackage,

    'DWORD': IntegerRecordPackage,
    'DINT': IntegerRecordPackage,
    'UDINT': IntegerRecordPackage,
    'ENUM': EnumRecordPackage,

    'REAL': FloatRecordPackage,
    'LREAL': FloatRecordPackage,

    'STRING': StringRecordPackage,
}


def sort_fields(unsorted: OrderedDict, sort_lookup: Optional[dict] = None,
                last: Optional[bool] = True) -> OrderedDict:
    """
    Sort the ordered dict according to the sort_scheme given at instantiation.
    Does NOT sort in place.

    Parameters
    ----------

    unsorted
        An OrderedDict in need of sorting.

    sort_lookup
        Requires a Dictionary, reverse lookup table for identifying sorting
        order. If left as None,
        :py:obj:`.default_settings.unified_ordered_field_list.unified_list`
        is used.

    last
        If True, place the alphabetized entries at the end, otherwise, place
        them at the start.

    """
    if sort_lookup is None:
        sort_lookup = unified_lookup_list

    instructed_unsorted = OrderedDict()
    naive_unsorted = OrderedDict()

    # Separate items identified by the sort_sceme into instructed_unsorted
    for x in unsorted:
        if x in sort_lookup:
            instructed_unsorted[x] = unsorted[x]
        else:
            naive_unsorted[x] = unsorted[x]

    # Separately sort instructed and, naively sorted entries
    instructed_sorted = sorted(
        instructed_unsorted.items(),
        key=lambda key: sort_lookup[key[0]])
    naive_sorted = sorted(
        naive_unsorted.items()
    )

    # Merge both Odicts in the order given by 'last'
    combined_sorted = OrderedDict()
    if last:
        combined_sorted.update(instructed_sorted)
        combined_sorted.update(naive_sorted)
    else:
        combined_sorted.update(naive_sorted)
        combined_sorted.update(instructed_sorted)
    return combined_sorted
