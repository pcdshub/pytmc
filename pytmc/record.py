"""
Record generation and templating
"""
import logging

from jinja2 import Environment, PackageLoader

from collections import ChainMap, OrderedDict

logger = logging.getLogger(__name__)


class EPICSRecord:
    """Representation of a single EPICS Record"""
    def __init__(self, pvname, record_type, fields=None, template=None):
        self.pvname = pvname
        self.record_type = record_type
        self.fields = OrderedDict(fields) if fields is not None else {}
        self.template = template or 'asyn_standard_record.jinja2'

        # Load jinja templates
        self.jinja_env = Environment(
            loader=PackageLoader("pytmc", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.record_template = self.jinja_env.get_template(
            self.template
        )

    def render(self):
        """Render the provided template"""
        for field, value in list(self.fields.items()):
            self.fields[field] = str(value).strip('"')

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
        self.pvname = chain.pvname
        self.tcname = chain.tcname
        self.chain = chain
        self.ads_port = ads_port

    @property
    def valid(self):
        """
        Returns
        -------
        bool
            Returns true if this record is fully specified and valid.
        """
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
        if data_type.is_array or chain.last.array_info:
            spec = WaveformRecordPackage
        elif data_type.is_string:
            spec = StringRecordPackage
        elif data_type.is_enum:
            spec = EnumRecordPackage
        else:
            spec = data_types[data_type.name]
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
                return

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
        io = self.chain.config.get('io', 'i')
        if 'o' in io:
            return 'output'
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
                             fields=self.field_defaults)

        # Add our port
        record.fields['INP'] = self._asyn_port_spec + '?'
        record.fields['DTYP'] = self.dtyp
        record.fields['SCAN'] = 'I/O Intr'

        # Update with given pragmas
        record.fields.update(self.chain.config.get('field', {}))
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
                             fields=self.field_defaults)
        # Add our port
        record.fields['DTYP'] = self.dtyp
        record.fields['OUT'] = self._asyn_port_spec + '='

        # Remove timestamp source and process-on-init for output records:
        record.fields.pop('TSE', None)
        record.fields.pop('PINI', None)

        # Update with given pragmas
        record.fields.update(self.chain.config.get('field', {}))
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
    field_defaults = {'FTVL': 'CHAR', 'NELM': '81'}

    def generate_input_record(self):
        record = super().generate_input_record()
        record.fields['DTYP'] += 'ArrayIn'
        return record

    def generate_output_record(self):
        record = super().generate_output_record()
        # Waveform records only have INP fields!
        record.fields['DTYP'] += 'ArrayOut'
        record.fields['INP'] = record.fields.pop('OUT')
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
