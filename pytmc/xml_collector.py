"""
xml_collector.py

This file contains the objects for intaking TMC files and generating python
interpretations. Db Files can be produced from the interpretation
"""
from collections import ChainMap
import re
import logging
import warnings
import xml.etree.ElementTree as ET

from collections import defaultdict
from copy import deepcopy

from jinja2 import Environment, PackageLoader

from . import Symbol, DataType, SubItem, epics
from .xml_obj import Configuration
from .record import EPICSRecord

logger = logging.getLogger(__name__)


class ElementCollector(dict):
    '''
    Dictionary-like object for controlling sets of insntances
    :class:`~pytmc.Symbol`, :class:`~pytmc.DataType`, and
    :class:`~pytmc.SubItem`. Each entry's key is the name of the TwinCAT
    variable.  :func:`~pytmc.xml_collector.ElementCollector.add` automates this
    setup and should be used to add entries instead of normal dictionary
    insertion techniques.

    Subclassed from python's standard dictionary.
    '''

    def add(self, value):
        '''
        Include new item in the dictionary.

        Parameters
        ----------
        value : :class:`.Symbol`, :class:`.DataType`, :class:`.SubItem`.
            The instance to add to the ElementCollector
        '''
        name = value.name
        dict.__setitem__(self, name, value)

    @property
    def registered(self):
        '''
        Return subset of the dictionary including only items marked for pytmc's
        comsumption with pragmas.

        Returns
        -------
        dict
            TwinCAT variables for pytmc
        '''
        names = list(filter(
            lambda x: self[x].has_config,
            self,

        ))
        return {name: self[name] for name in names}


class TmcFile:
    '''
    Object for handling the reading comprehension comprehension of .tmc files.

    Attributes
    ----------
    all_Symbols : :class:`~pytmc.xml_collector.ElementCollector`
        Collection of all Symbols in the document. Must be initialized with
        :func:`~isolate_Symbols`.

    all_DataTypes : :class:`~pytmc.xml_collector.ElementCollector`
        Collection of all DataTypes in the document. Must be initialized with
        :func:`~isolate_DataTypes`.

    all_SubItems : :class:`~pytmc.xml_collector.ElementCollector`
        Collection of all SubItems in the document. Must be initialized with
        :func:`~isolate_SubItems`.

    all_TmcChains : list
        Collection of all TmcChains in the document. Must be initialized with
        :func:`~create_chains`. These chains are NOT SINGULAR.

    all_singular_TmcChains : list
        Collection of all singularized TmcChains in the document. Must be
        initialized with :func:`~isolate_chains`.
    '''

    def __init__(self, filename):
        self.filename = filename
        if self.filename is not None:
            self.tree = ET.parse(self.filename)
            self.root = self.tree.getroot()
        else:
            self.tree = None
            self.root = None

        self.all_Symbols = ElementCollector()
        self.all_DataTypes = ElementCollector()
        self.all_SubItems = defaultdict(ElementCollector)
        if self.filename is not None:
            self.isolate_all()

        self.all_TmcChains = []
        self.all_singular_TmcChains = []
        self.all_RecordPackages = []

        # Load jinja templates
        self.jinja_env = Environment(
            loader=PackageLoader("pytmc", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        self.file_template = self.jinja_env.get_template(
            "asyn_standard_file.jinja2"
        )

    @property
    def ads_port(self):
        """
        Return the ADS Port defined in the TMC file under ApplicationName

        Returns
        -------
        int:
            The ADS Port defined in the TMC file under ApplicationName
        """
        if not self.root:
            return None
        # Grab the ApplicationName from XML Tree
        element = self.root.find("./Modules/Module/Properties/"
                                 "Property/[Name='ApplicationName']")
        element_value = element.find('./Value').text
        # Parse the value for the port number and convert
        port = int(re.search(r'(\d+)', element_value).group())
        return port

    def isolate_Symbols(self):
        '''
        Populate :attr:`~all_Symbols` with a :class:`~pytmc.Symbol`
        representing each symbol in the .tmc file.
        '''
        data_area = self.root.find(
            "./Modules/Module/DataAreas/DataArea/[Name='PlcTask Internal']"
        )
        xml_symbols = data_area.findall('./Symbol')
        for xml_symbol in xml_symbols:
            sym = Symbol(xml_symbol)
            self.all_Symbols.add(sym)

    def isolate_DataTypes(self, process_subitems=True):
        '''
        Populate :attr:`~all_DataTypes` with a :class:`~pytmc.DataType`
        representing each DataType in the .tmc file.

        Parameters
        ----------
        process_subitems : bool
            If True, automatically process all subitems containted in the
            datatypes populating :attr:`~all_SubItems`.
        '''
        xml_data_types = self.root.findall(
            "./DataTypes/DataType"
        )
        for xml_data_type in xml_data_types:
            data = DataType(xml_data_type)
            self.all_DataTypes.add(data)
            if process_subitems:
                self.isolate_SubItems(data.name)

    def isolate_SubItems(self, parent=None):
        '''
        Populate :attr:`~all_SubItems` with a :class:`~pytmc.SubItem`
        representing each subitem in the .tmc file.

        Parameters
        ----------
        parent : :str
            Specify the name string of the datatype to search for subitems.
            Subitems are automatically linked to this parent datatype.
        '''
        if type(parent) == str:
            parent_obj = self.all_DataTypes[parent]
            xml_subitems = parent_obj.element.findall('./SubItem')
            for xml_subitem in xml_subitems:
                s_item = SubItem(
                    xml_subitem,
                    parent=parent_obj
                )
                self.all_SubItems[parent].add(s_item)

        if type(parent) == ET.Element:
            pass

    def resolve_enums(self):
        """
        Identify the SubItems and Datatypes that represent enum types.
        Requires isolate_Datatypes and isolate_Subitems to have been run first.
        """
        # resolve str
        for sym_name in self.all_Symbols:
            sym = self.all_Symbols[sym_name]
            sym_type_str = sym.tc_type
            try:
                if self.all_DataTypes[sym_type_str].is_enum:
                    sym.is_enum = True
            except KeyError:
                pass

        # resolve subitems
        for datatype_name in self.all_SubItems:
            for subitem_name in self.all_SubItems[datatype_name]:
                subitem = self.all_SubItems[datatype_name][subitem_name]
                subitem_type_str = subitem.tc_type
                try:
                    if self.all_DataTypes[subitem_type_str].is_enum:
                        subitem.is_enum = True
                except KeyError:
                    pass

    def isolate_all(self):
        '''
        Shortcut for running :func:`~isolate_Symbols` and
        :func:`~isolate_DataTypes`
        '''
        self.isolate_Symbols()
        self.isolate_DataTypes()
        self.resolve_enums()

    def explore_all(self):
        """
        Return a list of ALL paths to leaf-variables in the tmc file.

        Returns
        -------
        list
            For every instantiated variable in the TmcFile, return a list
            documenting the path to that variable. This path starts at the
            global level instantiation and tracks through successive levels of
            encapsulation to find the final value itself. For each value, this
            list contains a single row.
        """
        results = []
        for sym in self.all_Symbols:
            results.extend(self.recursive_explore([self.all_Symbols[sym]]))
        return results

    def recursive_explore(self, root_path):
        """
        Given a starting Symbol or SubItem, recursively explore the contents of
        the target and return a list for the path to each final leaf-item.

        Parameters
        ----------
        root_path : list
            This is a list leading to the initial item to explore from. The
            list is composed of :class:`~Symbol` and :class:`~SubItem`
            instances

        Returns
        -------
        list
            This list contains a list for each leaf-item detected. The
            individual lists are the paths through the tree to each leaf-item
            charted by :class:`~Symbol` and :class:`~SubItem`.
        """
        root = root_path[-1]
        response = []
        target_SubItems = []

        # If this is a user defined datatype
        DataType_str = root.tc_type
        if DataType_str in self.all_DataTypes:

            # Accumulate list of SubItems in this Subitem/Symbol
            target_DataType = self.all_DataTypes[DataType_str]
            target_SubItems.extend(
                self.recursive_list_SubItems(target_DataType)
            )

            # For each subitem in this object/datatype explore further
            for subitem in target_SubItems:
                new_paths = self.recursive_explore(root_path + [subitem])
                response.extend(new_paths)

            return response

        # If not a use defined datatype
        else:
            return [root_path]

    def recursive_list_SubItems(self, root_DataType):
        """
        For a given DataType, provide all of its SubItems including those
        derived from inherited DataTypes

        Parameters
        ----------
        root_DataType : :class:`~DataType`
            instance of the target datatype

        Returns
        -------
        list
            list of :class:`~SubItem` of contained subItems
        """
        response = []
        root_DataType_str = root_DataType.name

        # Recursively explore inherited DataTypes
        parent_DataType_str = self.all_DataTypes[root_DataType_str].tc_extends
        if parent_DataType_str is not None:
            parent_DataType = self.all_DataTypes[parent_DataType_str]
            response.extend(self.recursive_list_SubItems(parent_DataType))

        # Append all SubItems from THIS DataType
        SubItem_str_list = self.all_SubItems[root_DataType_str]
        response.extend(
            [self.all_SubItems[root_DataType_str][z] for z in SubItem_str_list]
        )

        return response

    def create_chains(self):
        """
        Add all new TmcChains to this object instance's all_TmcChains variable
        """
        full_list = self.explore_all()
        for row in full_list:
            self.all_TmcChains.append(TmcChain(row))

    def isolate_chains(self):
        """
        Populate the self.all_Singular_TmcChains with singularized versions of
        the the entries in self.all_TmcChains. Requires create_chains to have
        been run first.
        """
        for non_singular in self.all_TmcChains:
            new_singular_chains = non_singular.build_singular_chains()
            for chain in new_singular_chains:
                self.all_singular_TmcChains.append(chain)

    def create_packages(self):
        """
        Populate the the self.all_RecordPackages list with no-guessing-applied
        packages. requires self.all_singular_TmcChains to be populated.
        """
        for singular_chain in self.all_singular_TmcChains:
            try:
                # TODO: Look for a special pragma that will route the chain to
                # a record package not based on the data type. This will be
                # needed for customizing specific records and supporting our
                # own data types such as motor
                brp = TwincatTypeRecordPackage.from_chain(self.ads_port,
                                                          chain=singular_chain)
            except Exception:
                logger.exception("Error creating record from %s",
                                 singular_chain)
            else:
                self.all_RecordPackages.append(brp)

    def configure_packages(self):
        """
        Apply guessing methods to self.all_RecordPackages.
        """
        for pack in list(self.all_RecordPackages):
            try:
                pack.configure()
            except Exception:
                logger.debug("Error configuring %r", pack)
                self.all_RecordPackages.remove(pack)

    def validate_with_dbd(self, dbd_file, remove_invalid_fields=True,
                          **linter_options):
        '''
        Validate all to-be-generated record fields

        Parameters
        ----------
        dbd_file : str or DbdFile
            The dbd file with which to validate
        remove_invalid_fields : bool, optional
            Remove fields marked by the linter as invalid
        **linter_options : dict
            Options to pass to the linter

        Returns
        -------
        pytmc.epics.LinterResults
            Results from the linting process

        Raises
        ------
        DBSyntaxError
            If db/dbd processing fails

        See also
        --------
        pytmc.epics.lint_db
        '''
        results = epics.lint_db(dbd=dbd_file, db=self.render(),
                                **linter_options)
        if remove_invalid_fields:
            all_invalid_fields = [
                error['format_args']
                for error in results.errors
                if error['name'] == 'bad-field'
                and len(error['format_args']) == 2
            ]
            invalid_fields_by_record = defaultdict(set)
            for record_type, field_name in all_invalid_fields:
                invalid_fields_by_record[record_type].add(field_name)

            for pack in self.all_RecordPackages:
                for record in getattr(pack, 'records', []):
                    for field in invalid_fields_by_record.get(
                                                    record.record_type,
                                                    []):
                        pack.cfg.remove_config_field(field)
        return results

    def render(self):
        """
        Produce .db file as string
        """
        rec_list = []
        for pack in self.all_RecordPackages:
            record_str = pack.render_records()
            if record_str:
                rec_list.append(record_str)

        return self.file_template.render(records=rec_list)


class ChainNotSingularError(Exception):
    pass


class MissingConfigError(Exception):
    pass


class TmcChain:
    """
    Pointer to the tmc instances and track order. Leaf node is last.
    """

    def __init__(self, chain):
        self.chain = chain

    def forkmap(self):
        """
        Provide a description of the branching hierarchy for entries with
        multiple Configurations.

        Returns
        -------
        list
            This list contains a list for each element contained in the chain.
            This interior list documents all configuration names held by that
            element in the chain.
        """
        full_list = []
        for entry in self.chain:
            logger.debug(str(entry))
            if entry.pragma is None:
                full_list.append([])
            else:
                full_list.append(entry.pragma.config_names())
        return full_list

    def is_singular(self):
        """
        Determine whether this TmcChain has only a single configuration for
        each element

        Returns
        -------
        bool
            True if all elements in this chain are singular
        """
        no_violations = True
        for element in self.forkmap():
            if len(element) != 1:
                no_violations = False
                break

        return no_violations

    def __eq__(self, other):
        """
        Two chains are equal if all their elements share the same xml element
        targets (elements are ==) and their configurations are the same.
        """
        if type(self) != type(other):
            return False

        if len(self.chain) != len(other.chain):
            return False

        for self_element, other_element in zip(self.chain, other.chain):
            if self_element != other_element:
                return False

            if self_element.pragma != other_element.pragma:
                return False

        return True

    def _recursive_permute(self, master_list, so_far=None):
        """
        For a given list of lists, create all possible combinations of lists in
        which the interior list defines the acceptable values for that place in
        the list

        Parameters
        ----------
        master_list : list
            This list contains a list at each index. These internal lists
            specify the acceptable values at each location in the output lists

        so_far : list or None
            Only used for internal recursive work. This lists the the 'so_far'
            assembled chains. This list grows with each iteration, either in
            length or in the length of the contained lists
        Returns
        -------
        list
            This list contains a single list for each possible permutation.
        """
        if so_far is None:
            so_far = [[]]

        replicate_count = len(so_far)

        extras = []
        for i in range(len(master_list[0])-1):
            for chain in so_far:
                extras.append(deepcopy(chain))
        so_far.extend(extras)

        for term, term_index in zip(master_list[0],
                                    range(len(master_list[0]))):
            for i in range(replicate_count):
                index = term_index * replicate_count + i
                so_far[index].append([term])

        if len(master_list) > 1:
            return self._recursive_permute(master_list[1:], so_far)
        else:
            return so_far

    def build_singular_chains(self):
        """
        Generate list of all acceptable configurations.

        Returns
        -------
        list
            List of TmcChains. Each chain is bound to one of the possible paths
            given the configurations available at each step.
        """
        name_sequences = self._recursive_permute(self.forkmap())
        logging.debug(str(name_sequences))
        results = []
        append = True
        for seq in name_sequences:
            new_TmcChain = deepcopy(self)
            for config, select_name in zip(new_TmcChain.chain, seq):
                if config.pragma is not None:
                    config.pragma.fix_to_config_name(select_name[0])
                else:
                    append = False
            if append:
                results.append(new_TmcChain)
            else:
                append = True
        return results

    def naive_config(self, cc_symbol=":"):
        """
        On chains of singular configs, stack up configurations from lowest to
        highest to generate a guess-free configuration.

        Returns
        -------
        Configuration
            Returns the configuration built from the existing pragmas in the
            chain.
        """
        if not self.is_singular():
            raise ChainNotSingularError

        new_config = Configuration(config=[])
        for entry in self.chain:
            new_config.concat(entry.pragma, cc_symbol=cc_symbol)

        return new_config

    @property
    def last(self):
        """
        Return the last element in the chain.

        Returns
        -------
        BaseElement, Symbol, or SubItem
            The instance (of whetever class) that represents the target
            variable.
        """
        return self.chain[-1]

    @property
    def name_list(self):
        """
        Produce list of the names of the elements in the chain. This name list
        should be usable by ADS to access the variable.

        Returns
        -------
        list

        """
        result = []
        for entry in self.chain:
            result.append(entry.name)
        return result

    def __str__(self):
        return "TmcChain: " + str(self.name_list)


class RecordPackage:
    """
    Base class to be inherited by all other RecordPackages

    The subclass must implement the :attr:`.records` property which returns the
    :class:`.EPICSRecord` objects which will be rendered from the package.
    Optionally, ``RecordPackage`` can have a ``configure`` method which does
    the necessary setup before the record can be configured.
    """
    _required_keys = {'pv'}
    _required_fields = {}

    def __init__(self, ads_port, chain=None, origin=None):
        """
        All subclasses should use super on their init method.
        """
        # Just fills in a default
        self.cfg = Configuration(config=[])

        self.chain = chain  # TmcChain instance - so I could add methods there

        # TmcChain instance-do I need this? unclear
        self.origin_chain = origin
        # ^could be relevant for init fields
        # Will continue without this for now

        self.ads_port = ads_port

    @property
    def pvname(self):
        """
        Returns
        -------
        pvname : str or None
            The PV name associated with the RecordPackage
        """
        try:
            return self.cfg.get_config_lines('pv')[0]['tag']
        except (TypeError, KeyError, IndexError):
            pass

    @property
    def tcname(self):
        """Complete variable name in Twincat Project"""
        return '.'.join(self.chain.name_list)

    def configure(self):
        """
        Configure the record before it is rendered

        This can optionally be implemented by subclass if additional
        configuration is needed for a ``RecordPackage``. Exceptions raised by
        this method will be caught and the ``RecordPackage`` will not be
        rendered
        """
        pass

    def cfg_as_dict(self):
        """
        Produce a jinja-template-compatible dictionary describing this
        RecordPackage.

        Returns
        -------
        dict
            return a dict. Keys are the fields of the jinja template. Contains
            special 'field' key where the value is a dictionary with f_name and
            f_set as the key/value pairs respectively.
        """
        cfg_dict = {}
        for row in self.cfg.config:
            if row['title'] == 'pv':
                cfg_dict['pv'] = row['tag']
            if row['title'] == 'type':
                cfg_dict['type'] = row['tag']
            if row['title'] == 'field':
                cfg_dict.setdefault('field', {})
                tag = row['tag']
                cfg_dict['field'][tag['f_name']] = tag['f_set']

        return cfg_dict

    @property
    def valid(self):
        """
        Returns
        -------
        bool
            Returns true if this record is fully specified and valid.
        """
        simple_dict = self.cfg_as_dict()
        has_required_keys = all(simple_dict.get(key)
                                for key in self._required_keys)

        fields = simple_dict.get('field', {})
        has_required_fields = all(fields.get(key)
                                  for key in self._required_fields)
        return has_required_keys and has_required_fields

    @property
    def records(self):
        """Generated :class:`.EPICSRecord` objects"""
        raise NotImplementedError()

    def render_records(self):
        """
        Returns
        -------
        string
            Jinja rendered entry for the RecordPackage
        """
        if not self.valid:
            logger.error('Unable to render record: %s', self)
            return
        return '\n\n'.join([record.render_template().strip()
                          for record in self.records])

    @classmethod
    def from_chain(cls, *args, chain, **kwargs):
        """Select the proper subclass of ``TwincatRecordPackage`` from chain"""
        last = chain.last
        if last.is_array:
            spec = WaveformRecordPackage
        elif last.tc_type in {'STRING'}:
            spec = StringRecordPackage
        else:
            spec = data_types[last.tc_type]
        # Create a RecordPackage from the chain
        return spec(*args, chain=chain, **kwargs)


class TwincatTypeRecordPackage(RecordPackage):
    """
    The common parent for all RecordPackages for basic Twincat types

    This main purpose of this class is to handle the parsing of the pragma
    chains that will be shared among all variable types. This includes setting
    the appropriate asyn port together and handling the "io" directionality. If
    you have a :class:`.TmcChain` but are not certain which class is
    appropriate use the :meth:`.from_chain` class constructor and the correct
    subclass will be chosen based on the given variable information

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # use form list of dicts,1st list has 1 entry per requirement
        # dict has form {'path':[],'target':n} where n is any variable
        self.validation_list = None

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

    def apply_config_validation(self):
        """
        Apply the guessing module. Assert that the proper fields exist.

        Returns
        -------
        List
            a list of the missing requirements
        """
        violations = []
        for req in self.validation_list:
            if not self.cfg.seek(**req):
                violations.append(req)

        return violations

    def generate_naive_config(self):
        """
        Create config dictionary from current chain. Move from lowest to
        highest level to create config (highest level has highest precedence).

        Overwrites self.cfg

        Returns
        -------
        None
        """
        self.cfg = self.chain.naive_config()

    def configure(self):
        """Configure the ``BaseRecordPackage`` for rendering"""
        self.generate_naive_config()

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
        try:
            io, = self.cfg.get_config_lines('io')
            io = io['tag']
            if 'o' in io:
                return 'output'
        except ValueError:
            logger.warning("No io direction specified for %r", self)
        return 'input'

    @property
    def _asyn_port_spec(self):
        """Asyn port specification without io direction"""
        return f'"@asyn($(PORT),0,1)ADSPORT={self.ads_port}/{self.tcname}'

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
        record.fields['INP'] = self._asyn_port_spec + '?"'
        record.fields['DTYP'] = self.dtyp
        record.fields['SCAN'] = '"I/O Intr"'

        # Update with given pragamas
        record.fields.update(self.cfg_as_dict().get('field', {}))
        return record

    def generate_output_record(self):
        """
        Generate the record to write values back to the PLC

        This will only be called if the ``io_direction`` is set to ``"output"`.

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
        record.fields['OUT'] = self._asyn_port_spec + '="'

        # Update with given pragamas
        record.fields.update(self.cfg_as_dict().get('field', {}))
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
    dtyp = '"asynInt32"'
    field_defaults = {'ZNAM': '"Zero"', 'ONAM': '"One"'}


class IntegerRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for an integer Twincat Variable"""
    input_rtyp = 'longin'
    output_rtyp = 'longout'
    dtyp = '"asynInt32"'


class FloatRecordPackage(TwincatTypeRecordPackage):
    """Create a set of records for a floating point Twincat Variable"""
    input_rtyp = 'ai'
    output_rtyp = 'ao'
    dtyp = '"asynFloat64"'
    field_defaults = {'PREC': '"3"'}


class EnumRecordPackage(TwincatTypeRecordPackage):
    """Create a set of record for a floating point Twincat Variable"""
    input_rtyp = 'mbbi'
    output_rtyp = 'mbbo'
    dtyp = '"asynInt32"'


class WaveformRecordPackage(TwincatTypeRecordPackage):
    input_rtyp = 'waveform'
    output_rtyp = 'waveform'

    @property
    def ftvl(self):
        """Field type of value"""
        ftvl = {'BOOL': '"CHAR"',
                'INT': '"SHORT"',
                'ENUM': '"SHORT"',
                'DINT': '"LONG"',
                'REAL': '"FLOAT"',
                'LREAL': '"DOUBLE"'}
        return ftvl[self.chain.last.tc_type]

    @property
    def nelm(self):
        """Number of elements in record"""
        return self.chain.last.iterable_length

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
        data_types = {'BOOL': '"asynInt8',
                      'BYTE': '"asynInt8',
                      'SINT': '"asynInt8',
                      'USINT': '"asynInt8',

                      'WORD': '"asynInt16',
                      'INT': '"asynInt16',
                      'UINT': '"asynInt16',

                      'DWORD': '"asynInt32',
                      'DINT': '"asynInt32',
                      'UDINT': '"asynInt32',
                      'ENUM': '"asynInt16',  # -> Int32?

                      'REAL': '"asynFloat32',
                      'LREAL': '"asynFloat64'}

        return data_types[self.chain.last.tc_type]

    def generate_input_record(self):
        record = super().generate_input_record()
        record.fields['DTYP'] += 'ArrayIn"'
        record.fields['FTVL'] = self.ftvl
        record.fields['NELM'] = self.nelm
        return record

    def generate_output_record(self):
        record = super().generate_output_record()
        record.fields['DTYP'] += 'ArrayOut"'
        record.fields['FTVL'] = self.ftvl
        record.fields['NELM'] = self.nelm
        # Waveform records only have INP fields!
        record.fields['INP'] = record.fields.pop('OUT')
        return record


class StringRecordPackage(TwincatTypeRecordPackage):
    """RecordPackage for broadcasting string values"""
    input_rtyp = 'waveform'
    output_rtyp = 'waveform'
    dtyp = '"asynInt8'
    field_defaults = {'FTVL': '"CHAR"', 'NELM': '"81"'}

    def generate_input_record(self):
        record = super().generate_input_record()
        record.fields['DTYP'] += 'ArrayIn"'
        return record

    def generate_output_record(self):
        record = super().generate_output_record()
        record.fields['DTYP'] += 'ArrayOut"'
        # Waveform records only have INP fields!
        record.fields['INP'] = record.fields.pop('OUT')
        return record


def BaseRecordPackage(port, chain=None, **kwargs):
    """
    Create a TwincatTypeRecordPackage based on the provided chain
    """
    warnings.warn("BaseRecordPackage will be deprecated in future releases "
                  "use TwincatTypeRecordPackage.from_chain instead")
    return TwincatTypeRecordPackage.from_chain(port, chain=chain, **kwargs)


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
}
