"""
Record generation and templating
"""
import logging
from collections import ChainMap, OrderedDict
from typing import Dict, List, Optional, Set

import jinja2

import pytmc

from .default_settings.unified_ordered_field_list import unified_lookup_list

logger = logging.getLogger(__name__)

# NOTE: Some PLCs may fill a buffer on a per-cycle basis. At 1KHz, 1000 is the
# magic number that would be used.  This threshold reflects the fact that we do
# not want to include those PVs in the archiver:
MAX_ARCHIVE_ELEMENTS = 999

# This field length maximum is based on the .DESC field length in epics-base:
MAX_DESC_FIELD_LENGTH = 40

_default_jinja_env = jinja2.Environment(
    loader=jinja2.PackageLoader("pytmc", "templates"),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _truncate_middle(string, max_length):
    '''
    Truncate a string to a maximum length, replacing the skipped middle section
    with an ellipsis.

    Parameters
    ----------
    string : str
        The string to optionally truncate
    max_length : int
        The maximum length
    '''
    # Based on https://www.xormedia.com/string-truncate-middle-with-ellipsis/
    if len(string) <= max_length:
        return string

    # half of the size, minus the 3 dots
    n2 = max_length // 2 - 3
    n1 = max_length - n2 - 3
    return '...'.join((string[:n1], string[-n2:]))


def _update_description(record, default):
    """
    Update the description field for the given record.

    * If not provided, fall back to the given `default`.
    * Ensure the description fits, given the maximum length restrictions.

    Parameters
    ----------
    record : EPICSRecord
        The record to update.

    default : str
        The default description.
    """
    fields = record.fields
    desc = fields.setdefault('DESC', default)
    if len(desc) <= MAX_DESC_FIELD_LENGTH:
        return

    # Stash the full description:
    record.long_description = desc

    # And truncate the one available to EPICS:
    fields['DESC'] = _truncate_middle(desc, MAX_DESC_FIELD_LENGTH)


class EPICSRecord:
    """Representation of a single EPICS Record"""

    def __init__(self, pvname, record_type, direction, fields=None,
                 template=None, autosave=None, aliases=None,
                 archive_settings=None, package=None):
        self.pvname = pvname
        self.record_type = record_type
        self.direction = direction
        self.fields = OrderedDict(fields) if fields is not None else {}
        self.aliases = list(aliases) if aliases is not None else []
        self.template = template or 'asyn_standard_record.jinja2'
        self.autosave = dict(autosave) if autosave else {}
        self.package = package
        self.archive_settings = (dict(archive_settings)
                                 if archive_settings else {})

        if 'fields' not in self.archive_settings:
            self.archive_settings = {}

        self.record_template = _default_jinja_env.get_template(self.template)

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

    def update_pini_for_autosave(self):
        """
        Set PINI=1 if VAL is autosaved at pass1.

        This is a bandaid fix for unexplained behavior where the
        autosave pass1 does not send values to the PLC unless
        PINI=1.

        This is intended to be called for output records.
        """
        if 'VAL' in self.autosave['pass1']:
            self.fields['PINI'] = 1

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
    archive_fields = []

    def __init__(self, ads_port, chain=None, origin=None):
        """
        All subclasses should use super on their init method.
        """
        self.ads_port = ads_port
        self.aliases = []
        self.archive_settings = None
        self.chain = chain
        self.pvname = None
        self.tcname = chain.tcname
        self.linked_to_pv = None
        self.macro_character = '@'
        self.delimiter = ':'
        self.config = pytmc.pragmas.normalize_config(self.chain.config)
        self.long_description = None

        self._parse_config(self.config)

    def __repr__(self):
        items = {
            attr: getattr(self, attr, None)
            for attr in ('tcname', 'pvname', 'long_description',
                         'linked_to_pv')
        }
        info = ', '.join(f'{k}={v!r}' for k, v in items.items()
                         if v)
        return f"{self.__class__.__name__}({info})"

    def _parse_config(self, config):
        'Parse the chain configuration'
        if config is None:
            return

        self.macro_character = config.get('macro_character', '@')

        self._configure_pvname()
        self._configure_link()
        self._configure_archive_settings(
            archive_settings=config['archive'],
            archive_fields=config.get('archive_fields', '')
        )
        self._configure_aliases(pv=config['pv'],
                                macro_character=self.macro_character,
                                alias_setting=config.get('alias', ''))

        return config

    def _configure_link(self):
        'Link this record to a pre-existing EPICS record via a CA (CP) link'
        self.linked_to_pv = self.config.get('link') or None

    def _configure_pvname(self):
        'Configure the pvname, based on the given macro character'
        # Due to a twincat pragma limitation, EPICS macro prefix '$' cannot be
        # used or escaped.  Allow the configuration to specify an alternate
        # character in the pragma, defaulting to '@'.
        self.pvname = self.chain.pvname.replace(self.macro_character, '$')

    def _configure_aliases(self, pv, macro_character, alias_setting):
        'Configure aliases from the configuration (aliases attribute)'
        # The base for the alias does not include the final pvname:
        alias_base = self.delimiter.join(
            pv_segment for pv_segment in pv[:-1]
            if pv_segment
        )

        # Split user-specified aliases for the record:
        self.aliases = [
            self.delimiter.join(
                (alias_base, alias)).replace(self.macro_character, '$')
            for alias in alias_setting.split(' ')
            if alias.strip()
        ]

    def _configure_archive_settings(self, archive_settings, archive_fields):
        'Parse archive settings pragma key (archive_settings attribute)'
        self.archive_settings = archive_settings
        if archive_settings:
            # Fields are those from the pragma (key: archive_fields) plus
            # those set by default on the RecordPackage class
            fields = set(archive_fields.split(' ')
                         if archive_fields else [])
            archive_settings['fields'] = fields.union(set(self.archive_fields))

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
        has_required_keys = all(self.config.get(key)
                                for key in self._required_keys)

        fields = self.config.get('field', {})
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
            spec = RecordPackage
        elif data_type.is_enum:
            spec = EnumRecordPackage
        elif data_type.is_array or chain.last.array_info:
            spec = WaveformRecordPackage
        elif data_type.is_string:
            spec = StringRecordPackage
        else:
            try:
                spec = DATA_TYPES[data_type.name]
            except KeyError:
                raise ValueError(
                    f'Unsupported data type {data_type.name} in chain: '
                    f'{chain.tcname} record: {chain.pvname}'
                ) from None
            if spec is IntegerRecordPackage:
                if "scale" in chain.config or "offset" in chain.config:
                    # longin/longout do not support scaling. Special-case and
                    # cast to a FloatRecordPackage.
                    spec = FloatRecordPackage

        return spec(*args, chain=chain, **kwargs)


AutosaveDefaults = Dict[str, Dict[str, Set[str]]]


def make_autosave_defaults(
    input_pass0: Optional[List[str]] = None,
    input_pass1: Optional[List[str]] = None,
    output_pass0: Optional[List[str]] = None,
    output_pass1: Optional[List[str]] = None,
    exclude_defaults: bool = False,
) -> AutosaveDefaults:
    """
    Create autosave defaults for a given record type.

    Parameters
    ----------
    input_pass0 : List[str]
        Fields to save on the input record for pass 0 (pre-iocInit)
    input_pass1 : List[str]
        Fields to save on the input record for pass 1 (post-iocInit)
    output_pass0 : List[str]
        Fields to save on the output record for pass 0 (pre-iocInit)
    output_pass1 : List[str]
        Fields to save on the output record for pass 1 (post-iocInit)
    exclude_defaults : bool, optional
        Exclude the defaults normally used for all records.

    Returns
    -------
    dict
        Dictionary of defaults with keys "input" and "output", under which
        are keys "pass0" and "pass1".
    """

    if not exclude_defaults:
        default_input_pass0 = {
            "DISS",  # Disable Alarm Sevrty
            "UDFS",  # Undefined Alarm Sevrty
        }
        default_output_pass0 = {
            "VAL",  # The value
            "DISS",  # Disable Alarm Sevrty
            "UDFS",  # Undefined Alarm Sevrty
        }
    else:
        default_input_pass0 = set()
        default_output_pass0 = set()

    return dict(
        input=dict(
            pass0=set(input_pass0 or []) | default_input_pass0,
            pass1=set(input_pass1 or []),
        ),
        output=dict(
            pass0=set(output_pass0 or []) | default_output_pass0,
            pass1=set(output_pass1 or []),
        ),
    )


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
    autosave_defaults = make_autosave_defaults()

    dtyp = NotImplemented
    input_rtyp = NotImplemented
    output_rtyp = NotImplemented
    input_only_fields = {'SVAL'}
    output_only_fields = {'DOL', 'IVOA', 'IVOV', 'OMSL'}
    archive_fields = ['VAL']

    # Is an auxiliary record required to support existing record linking?
    link_requires_record = False

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
        """
        return self.config['io']

    @property
    def _asyn_port_spec(self):
        'Asyn port specification without io direction, with room for options'
        return (f'@asyn($(PORT),0,1)'
                f'ADSPORT={self.ads_port}/{{options}}{self.tcname}'
                )

    @property
    def asyn_update_options(self):
        'Input record update options (TS_MS or POLL_RATE)'
        update = self.config['update']
        if update['method'] == 'poll':
            freq = update['frequency']
            if int(freq) == float(freq):
                return f'POLL_RATE={int(freq)}/'
            return f'POLL_RATE={freq:.2f}'.rstrip('0') + '/'

        milliseconds = int(1000 * update['seconds'])
        return f'TS_MS={milliseconds}/'

    @property
    def asyn_input_port_spec(self):
        """Asyn input port specification (for INP field)"""
        return (
            self._asyn_port_spec.format(options=self.asyn_update_options) + '?'
        )

    @property
    def asyn_output_port_spec(self):
        """Asyn output port specification (for OUT field)"""
        return self._asyn_port_spec.format(options='') + '='

    def generate_input_record(self):
        """
        Generate the record to read values into to the IOC

        Returns
        -------
        record: :class:`.EpicsRecord`
            Description of input record
        """
        # Base record with defaults
        def add_rbv(pvname):
            if pvname and not pvname.endswith('RBV'):
                return pvname + '_RBV'
            return pvname

        pvname = add_rbv(self.pvname)
        aliases = [add_rbv(alias) for alias in self.aliases]

        record = EPICSRecord(pvname,
                             self.input_rtyp,
                             'input',
                             fields=self.field_defaults,
                             autosave=self.autosave_defaults.get('input'),
                             aliases=aliases,
                             archive_settings=self.archive_settings,
                             package=self,
                             )

        # Add our port
        record.fields['INP'] = self.asyn_input_port_spec
        record.fields['DTYP'] = self.dtyp

        # Update with given pragma fields - ignoring output-only fields:
        user_fields = self.config.get('field', {})
        record.fields.update(
            {field: value for field, value in user_fields.items()
             if field not in self.output_only_fields
             }
        )

        # Set a default description to the tcname
        _update_description(record, self.chain.tcname)

        # Records must always be I/O Intr, regardless of the pragma:
        record.fields['SCAN'] = 'I/O Intr'

        record.update_autosave_from_pragma(self.config)

        return record

    def _get_omsl_fields(self):
        """Get output mode select fields for the output record."""
        if not self.linked_to_pv or self.linked_to_pv[-1] is None:
            return {}

        last_link = self.linked_to_pv[-1]
        if last_link.startswith('*'):
            # NOTE: A special, undocumented syntax for a lack of a better
            # idea/more time:  need to allow pytmc to get access to a PV name
            # it generates
            # Consider this temporary API, only to be used in
            # lcls-twincat-general for now.
            pv_parts = list(self.config['pv'])
            linked_to_pv = self.delimiter.join(
                pv_parts[:-1] + [last_link.lstrip('*')]
            )
        else:
            linked_to_pv = ''.join(
                part for part in self.linked_to_pv
                if part is not None
            )

        linked_to_pv = linked_to_pv.replace(self.macro_character, '$')
        return {
            'OMSL': 'closed_loop',
            'DOL': linked_to_pv + ' CP MS',
            'SCAN': self.config.get('link_scan', '.5 second'),
        }

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
                             autosave=self.autosave_defaults.get('output'),
                             aliases=self.aliases,
                             archive_settings=self.archive_settings,
                             package=self,
                             )

        # Add our port
        record.fields['DTYP'] = self.dtyp
        record.fields['OUT'] = self.asyn_output_port_spec

        # Remove timestamp source and process-on-init for output records:
        record.fields.pop('TSE', None)
        record.fields.pop('PINI', None)

        # Add on OMSL fields, if this is linked to an existing record.
        # Some links (such as strings) may require auxiliary records, so
        # don't repurpose the output record in that case.
        if not self.link_requires_record:
            record.fields.update(self._get_omsl_fields())

        # Update with given pragma fields - ignoring input-only fields:
        user_fields = self.config.get('field', {})
        record.fields.update(
            {field: value for field, value in user_fields.items()
             if field not in self.input_only_fields
             }
        )

        # Set a default description to the tcname
        _update_description(record, self.chain.tcname)

        record.update_autosave_from_pragma(self.config)
        record.update_pini_for_autosave()
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
    field_defaults = {'ZNAM': 'FALSE', 'ONAM': 'TRUE'}
    output_only_fields = {'DOL', 'HIGH', 'IVOA', 'IVOV', 'OMSL', 'ORBV',
                          'OUT', 'RBV', 'RPVT', 'WDPT'}
    input_only_fields = {'SVAL'}

    autosave_defaults = make_autosave_defaults(
        input_pass0=[
            "ZSV",  # Zero Error Severity
            "OSV",  # One Error Severity
            "SIMS",  # Simulation Mode Severity
        ],
        output_pass0=[
            "ZSV",  # Zero Error Severity
            "OSV",  # One Error Severity
            "COSV",  # Change of State Sevr
            "SIMS",  # Simulation Mode Severity
        ],
    )


class IntegerRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for an integer Twincat Variable"""
    input_rtyp = 'longin'
    output_rtyp = 'longout'
    output_only_fields = {'DOL', 'DRVH', 'DRVL', 'IVOA', 'IVOV', 'OMSL'}
    input_only_fields = {'AFTC', 'AFVL', 'SVAL'}
    dtyp = 'asynInt32'

    autosave_defaults = make_autosave_defaults(
        input_pass0=[
            "HHSV",  # Hihi Severity
            "HSV",  # High Severity
            "LLSV",  # Lolo Severity
            "LSV",  # Low Severity
            "SIMS",  # Simulation Mode Severity
        ],
        output_pass0=[
            "HHSV",  # Hihi Severity
            "HSV",  # High Severity
            "LLSV",  # Lolo Severity
            "LSV",  # Low Severity
            "SIMS",  # Simulation Mode Severity
        ],
    )


class FloatRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for a floating point Twincat Variable"""
    input_rtyp = 'ai'
    output_rtyp = 'ao'
    dtyp = 'asynFloat64'
    field_defaults = {'PREC': '3'}
    output_only_fields = {'DOL', 'DRVH', 'DRVL', 'IVOA', 'IVOV', 'OIF',
                          'OMOD', 'OMSL', 'ORBV', 'OROC', 'OVAL', 'PVAL',
                          'RBV'}
    input_only_fields = {'AFTC', 'AFVL', 'SMOO', 'SVAL'}

    autosave_defaults = make_autosave_defaults(
        input_pass0=[
            "HHSV",  # Hihi Severity
            "HSV",  # High Severity
            "LLSV",  # Lolo Severity
            "LSV",  # Low Severity
            "PREC",  # precision
            "SIMS",  # Simulation Mode Severity
        ],
        output_pass0=[
            "HHSV",  # Hihi Severity
            "HSV",  # High Severity
            "LLSV",  # Lolo Severity
            "LSV",  # Low Severity
            "PREC",  # precision
            "SIMS",  # Simulation Mode Severity
            "VAL",  # the value
        ],
    )

    def get_scale_offset(self):
        """Get the scale and offset for the analog record(s)."""
        scale = self.config.get("scale", None)
        offset = self.config.get("offset", None)
        if scale is None and offset is None:
            return None, None

        scale = "1.0" if scale is None else scale
        offset = offset or "0.0"
        return scale, offset

    def generate_input_record(self):
        record = super().generate_input_record()
        scale, offset = self.get_scale_offset()
        if scale is not None:
            # If LINR==SLOPE, VAL = RVAL * ESLO + EOFF
            record.fields["LINR"] = "SLOPE"
            record.fields["ESLO"] = scale
            record.fields["EOFF"] = offset
        return record

    def generate_output_record(self):
        record = super().generate_output_record()
        scale, offset = self.get_scale_offset()
        if scale is not None:
            # If LINR==SLOPE, then RVAL = (VAL - EOFF) / ESLO
            record.fields["LINR"] = "SLOPE"
            record.fields["ESLO"] = scale
            record.fields["EOFF"] = offset
        return record


class EnumRecordPackage(TwincatTypeRecordPackage):
    """Create a set of record for a ENUM Twincat Variable"""
    input_rtyp = 'mbbi'
    output_rtyp = 'mbbo'
    dtyp = 'asynInt32'
    output_only_fields = {'DOL', 'IVOA', 'IVOV', 'OMSL', 'ORBV', 'RBV'}
    input_only_fields = {'AFTC', 'AFVL', 'SVAL'}
    autosave_defaults = make_autosave_defaults(
        input_pass0=[
            "ZRSV",  # State Zero Severity
            "ONSV",  # State One Severity
            "TWSV",  # State Two Severity
            "THSV",  # State Three Severity
            "FRSV",  # State Four Severity
            "FVSV",  # State Five Severity
            "SXSV",  # State Six Severity
            "SVSV",  # State Seven Severity
            "EISV",  # State Eight Severity
            "NISV",  # State Nine Severity
            "TESV",  # State Ten Severity
            "ELSV",  # State Eleven Severity
            "TVSV",  # State Twelve Severity
            "TTSV",  # State Thirteen Sevr
            "FTSV",  # State Fourteen Sevr
            "FFSV",  # State Fifteen Severity
            "UNSV",  # Unknown State Severity
            "SIMS",  # Simulation Mode Severity
        ],
        output_pass0=[
            "ZRSV",  # State Zero Severity
            "ONSV",  # State One Severity
            "TWSV",  # State Two Severity
            "THSV",  # State Three Severity
            "FRSV",  # State Four Severity
            "FVSV",  # State Five Severity
            "SXSV",  # State Six Severity
            "SVSV",  # State Seven Severity
            "EISV",  # State Eight Severity
            "NISV",  # State Nine Severity
            "TESV",  # State Ten Severity
            "ELSV",  # State Eleven Severity
            "TVSV",  # State Twelve Severity
            "TTSV",  # State Thirteen Sevr
            "FTSV",  # State Fourteen Sevr
            "FFSV",  # State Fifteen Sevr
            "UNSV",  # Unknown State Sevr
            "COSV",  # Change of State Sevr
            "SIMS",  # Simulation Mode Severity
        ],
    )

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
    field_defaults = {
        'APST': 'On Change',
        'MPST': 'On Change',
    }
    autosave_defaults = make_autosave_defaults(
        input_pass0=[
            "SIMS",  # Simulation Mode Severity
        ],
        output_pass0=[
            "SIMS",  # Simulation Mode Severity
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.nelm > MAX_ARCHIVE_ELEMENTS:
            self.archive_settings = None

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
    field_defaults = {
        'FTVL': 'CHAR',
        'APST': 'On Change',
        'MPST': 'On Change',
    }
    autosave_defaults = make_autosave_defaults(
        input_pass0=[
            "SIMS",  # Simulation Mode Severity
        ],
        output_pass0=[
            "SIMS",  # Simulation Mode Severity
        ],
    )
    # The LSO record that gets generated when a "link" is used to write
    # string data into the PLC from another EPICS PV:
    autosave_defaults_for_link = make_autosave_defaults(
        input_pass0=[
            "SIMS",  # Simulation Mode Severity
        ],
        output_pass0=[
            "SIMS",  # Simulation Mode Severity
        ],
    )

    # Links to string PVs require auxiliary 'lso' record.
    link_requires_record = True
    link_suffix = "LSO"

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

    def generate_link_record(self):
        """An auxiliary 'lso' link record to pass string PVs to the PLC."""
        record = EPICSRecord(
            self.delimiter.join((self.pvname, self.link_suffix)),
            record_type="lso",
            direction="output",
            package=self,
            autosave=self.autosave_defaults_for_link["output"],
        )
        record.fields.pop('TSE', None)
        record.fields.pop('PINI', None)
        record.fields["SIZV"] = self.nelm

        # Add our port
        record.fields.update(
            self._get_omsl_fields()
        )
        record.fields['OUT'] = f"{self.pvname} PP MS"
        _update_description(record, f"Aux link record for {self.chain.tcname}")
        return record

    @property
    def records(self):
        """All records that will be created in the package"""
        records = [self.generate_input_record()]
        link_fields = self._get_omsl_fields()
        if self.io_direction == 'output' or link_fields:
            records.append(self.generate_output_record())
            if link_fields and self.link_requires_record:
                records.append(self.generate_link_record())

        return records


DATA_TYPES = {
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


def generate_archive_settings(packages):
    '''
    Generate an archive settings given a list of record packages

    Parameters
    ----------
    packages : list of record packages

    Yields
    ------
    str
        One line from the archiver settings file
    '''
    for package in packages:
        archive_settings = package.archive_settings
        if archive_settings:
            # for record in package.records:
            for record in package.records:
                for field in sorted(archive_settings['fields']):
                    period = archive_settings['seconds']
                    update_rate = package.config['update']['seconds']
                    if period < update_rate:
                        period = update_rate
                    method = archive_settings['method']
                    yield f'{record.pvname}.{field}\t{period}\t{method}'
