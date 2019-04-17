"""
xml_collector.py

This file contains the objects for intaking TMC files and generating python
interpretations. Db Files can be produced from the interpretation
"""
import re
import logging
import functools
import xml.etree.ElementTree as ET

from collections import defaultdict
from copy import deepcopy

from jinja2 import Environment, PackageLoader

from . import Symbol, DataType, SubItem
from .xml_obj import Configuration


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
        value : :class:`~pytmc.Symbol`, :class:`~pytmc.DataType`,or :class:`~pytmc.SubItem`.
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
        port = int(re.search('(\d+)', element_value).group())
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
            brp = BaseRecordPackage(self.ads_port, chain=singular_chain)
            #brp = BaseRecordPackage(chain=singular_chain, origin=chain)
            self.all_RecordPackages.append(brp)

    def configure_packages(self):
        """
        Apply guessing methods to self.all_RecordPackages.
        """
        for pack in list(self.all_RecordPackages):
            try:
                pack.generate_naive_config()
                pack.guess_all()
            except ChainNotSingularError:
                logger.debug("Invalid RecordPackage: %s", pack)
                self.all_RecordPackages.remove(pack)

    def render(self):
        """
        Produce .db file as string
        """
        rec_list = []
        for pack in self.all_RecordPackages:
            record_str = pack.render_record()
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

        for term, term_index in zip(master_list[0], range(len(master_list[0]))):
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
        cfg_title = ""
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


class BaseRecordPackage:
    """
    BaseRecordPackage includes some basic funcionality that should be shared
    across most versions. This includes things like common methods so things
    like validation can be configured at the __init__ with an instance
    variable. Overwrite/inherit features as necessary.

    """

    _required_keys = {'pv', 'type', 'field'}
    _required_fields = {'DTYP', }

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

        # List of methods defined in the class
        self.guess_methods_list = [
            self.guess_PINI,
            self.guess_TSE,
            self.guess_type,
            self.guess_io,
            self.guess_DTYP,
            self.guess_INP_OUT,
            self.guess_SCAN,
            self.guess_ONAM,
            self.guess_ZNAM,
            self.guess_PREC,
            self.guess_FTVL,
            self.guess_NELM,
        ]

        # use form list of dicts,1st list has 1 entry per requirement
        # dict has form {'path':[],'target':n} where n is any variable
        self.validation_list = None

        # Load jinja templates
        self.jinja_env = Environment(
            loader=PackageLoader("pytmc", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.record_template = self.jinja_env.get_template(
            "asyn_standard_record.jinja2"
        )
        self.file_template = self.jinja_env.get_template(
            "asyn_standard_file.jinja2"
        )

        self.ads_port = ads_port

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

    def ID_type(self):
        """
        Distinguish special record types from one another such as a motor
        record. Select from the available types of "standard" and "motor
        record." Should always return a value. No guessing should be required
        to use this method

        Returns
        -------
        string
            String name of type
        """
        # Instantly remove list formatting if this is len(1) list, leaves dict
        type_search, = self.cfg.seek(['title'], 'type')
        if type_search['tag'] == 'motor':
            return 'motor'
        else:
            return 'standard'

    def generate_record_entry(self):
        """
        apply all jinja functionality to create the template
        return dict w/ filename as key for each entry in the iterable
        """
        raise NotImplementedError

    def motor_record_as_dict(self):
        """
        Produce a jinja-template-compatible dict describing this RecordPackage

        Returns
        -------
        dict
            return a dict. Keys are the fields of the jinja template. Contains
            special 'field' key where the value is a dictionary with f_name and
            f_set as the key/value pairs respectively.
        """
        raise NotImplementedError

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
            if row['title'] == 'info':
                cfg_dict['info'] = True

        cfg_dict.setdefault('info', False)
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

    def render_record(self):
        """
        Returns
        -------
        string
            Jinja rendered entry for this BaseRecordPackage
        """
        simple_dict = self.cfg_as_dict()
        if not self.valid:
            logger.error('Unable to render record: %s', simple_dict)
            return

        return self.record_template.render(**simple_dict)

    @staticmethod
    def generate_files(records):
        """
        Parameters
        ----------
        records : list
            list of all incoming Record objects

        Returns
        -------
        str
            The Jinja-made output of the full resulting file.
        """
        raise NotImplementedError

    def _skip_if_field_set(field):
        '''
        decorator: skip a `guess` function if `field` is already set

        Parameters
        ----------
        field : str
            The field name
        '''
        def wrapper(func):
            @functools.wraps(func)
            def wrapped(self, *args, **kwargs):
                try:
                    field_value, = self.cfg.get_config_fields(field)
                    return False
                except ValueError:
                    pass
                return func(self, *args, **kwargs)
            return wrapped
        return wrapper

    @_skip_if_field_set('PINI')
    def guess_PINI(self):
        """
        Add process-on-init (PINI) field
        """
        self.cfg.add_config_field("PINI", '"1"')
        return True

    @_skip_if_field_set('TSE')
    def guess_TSE(self):
        """
        Add timestamp event (TSE) field
        """
        # TSE=-2: the device support provides the time stamp from the hardware
        self.cfg.add_config_field("TSE", "-2")
        return True

    def guess_type(self):
        """
        Add information indicating record type (e.g. ai, bo, waveform, etc.)

        Returns
        -------
        bool
            Return a boolean that is true iff a change has been made.
        """
        try:
            ty, = self.cfg.get_config_lines('type')
            return False
        except ValueError:
            pass

        try:
            io, = self.cfg.get_config_lines('io')
        except ValueError:
            return False

        # must be tested first, arrays will have the tc_type of the iterable:
        if self.chain.last.is_array:
            io, = self.cfg.get_config_lines('io')
            if 'i' in io['tag'] and 'o' in io['tag']:
                self.cfg.add_config_line("type", "waveform")
                return True
            elif 'i' in io['tag']:
                self.cfg.add_config_line("type", "waveform")
                return True
            elif 'o' in io['tag']:
                self.cfg.add_config_line("type", "waveform")
                return True

        bi_bo_set = {
            "BOOL"
        }
        if self.chain.last.tc_type in bi_bo_set:
            io, = self.cfg.get_config_lines('io')
            if 'i' in io['tag'] and 'o' in io['tag']:
                self.cfg.add_config_line("type", "bo")
                return True
            elif 'i' in io['tag']:
                self.cfg.add_config_line("type", "bi")
                return True
            elif 'o' in io['tag']:
                self.cfg.add_config_line("type", "bo")
                return True

        ai_ao_set = {
            "INT",
            "DINT",
            "REAL",
            "LREAL",
            "ENUM",
        }
        if self.chain.last.tc_type in ai_ao_set:
            io, = self.cfg.get_config_lines('io')
            if 'i' in io['tag'] and 'o' in io['tag']:
                self.cfg.add_config_line("type", "ao")
                return True
            elif 'i' in io['tag']:
                self.cfg.add_config_line("type", "ai")
                return True
            elif 'o' in io['tag']:
                self.cfg.add_config_line("type", "ao")
                return True

        waveform_set = {
            "STRING",
        }
        if self.chain.last.tc_type in waveform_set:
            io, = self.cfg.get_config_lines('io')
            if 'i' in io['tag'] and 'o' in io['tag']:
                self.cfg.add_config_line("type", "waveform")
                return True
            elif 'i' in io['tag']:
                self.cfg.add_config_line("type", "waveform")
                return True
            elif 'o' in io['tag']:
                self.cfg.add_config_line("type", "waveform")
                return True

        return False

    def guess_io(self):
        """
        Add information indicating io direction if it is not provided.

        Returns
        -------
        bool
            Return a boolean that is true iff a change has been made.

        """
        try:
            io, = self.cfg.get_config_lines('io')
            return False
        except ValueError:
            self.cfg.add_config_line("io", "io")
            return True

    @_skip_if_field_set('DTYP')
    def guess_DTYP(self):
        """
        Add field specifying DTYP.

        The following is taken from the EPICS wiki: "This field specifies the
        device type for the record. Each record type has its own set of device
        support routines which are specified in devSup.ASCII. If a record type
        does not have any associated device support, DTYP and DSET are
        meaningless."

        Returns
        -------
        bool
            Return a boolean that is True iff a change has been made.
        """
        io, = self.cfg.get_config_lines('io')
        io = io['tag']

        BOOL_set = {"BOOL"}
        if self.chain.last.tc_type in BOOL_set:
            base = '"asynInt32'
            if self.chain.last.is_array:
                if 'i' in io and 'o' in io:
                    self.cfg.add_config_field("DTYP", '"asynInt8ArrayOut"')
                    return True
                elif 'i' in io:
                    self.cfg.add_config_field("DTYP", '"asynInt8ArrayIn"')
                    return True
                elif 'o' in io:
                    self.cfg.add_config_field("DTYP", '"asynInt8ArrayOut"')
                    return True
            else:
                self.cfg.add_config_field("DTYP", base+'"')
                return True

        INT_set = {"INT", "ENUM"}
        if self.chain.last.tc_type in INT_set:
            base = '"asynInt32'
            if self.chain.last.is_array:
                if 'i' in io and 'o' in io:
                    self.cfg.add_config_field("DTYP", '"asynInt16ArrayOut"')
                    return True
                elif 'i' in io:
                    self.cfg.add_config_field("DTYP", '"asynInt16ArrayIn"')
                    return True
                elif 'o' in io:
                    self.cfg.add_config_field("DTYP", '"asynInt16ArrayOut"')
                    return True
            else:
                self.cfg.add_config_field("DTYP", base+'"')
                return True

        DINT_set = {"DINT"}
        if self.chain.last.tc_type in DINT_set:
            base = '"asynInt32'
            if self.chain.last.is_array:
                if 'i' in io and 'o' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayOut"')
                    return True
                elif 'i' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayIn"')
                    return True
                elif 'o' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayOut"')
                    return True
            else:
                self.cfg.add_config_field("DTYP", base+'"')
                return True

        REAL_set = {"REAL"}
        if self.chain.last.tc_type in REAL_set:
            if self.chain.last.is_array:
                base = '"asynFloat32'
                if 'i' in io and 'o' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayOut"')
                    return True
                elif 'i' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayIn"')
                    return True
                elif 'o' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayOut"')
                    return True
            else:
                self.cfg.add_config_field("DTYP", '"asynFloat64"')
                return True

        LREAL_set = {"LREAL"}
        if self.chain.last.tc_type in LREAL_set:
            base = '"asynFloat64'
            if self.chain.last.is_array:
                if 'i' in io and 'o' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayOut"')
                    return True
                elif 'i' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayIn"')
                    return True
                elif 'o' in io:
                    self.cfg.add_config_field("DTYP", base+'ArrayOut"')
                    return True
            else:
                self.cfg.add_config_field("DTYP", base+'"')
                return True

        asynInt8ArrayOut_set = {"STRING"}
        if self.chain.last.tc_type in asynInt8ArrayOut_set:
            io, = self.cfg.get_config_lines('io')
            if 'i' in io['tag'] and 'o' in io['tag']:
                self.cfg.add_config_field("DTYP", '"asynInt8ArrayOut"')
                return True
            elif 'i' in io['tag']:
                self.cfg.add_config_field("DTYP", '"asynInt8ArrayIn"')
                return True
            elif 'o' in io['tag']:
                self.cfg.add_config_field("DTYP", '"asynInt8ArrayOut"')
                return True

        return False

    def guess_INP_OUT(self):
        """
        Construct, add, INP or OUT field
        Fields will have this form:
        "@asyn($(PORT),0,1)ADSPORT=851/Main.bEnableUpdateSine="

        Returns
        -------
        bool
            Return a boolean that is true iff a change has been made.
        """

        io, = self.cfg.get_config_lines('io')
        io = io['tag']
        name_list = self.chain.name_list
        name = '.'.join(name_list)
        assign_symbol = ""
        field_type = ""
        if 'i' in io and 'o' in io:
            assign_symbol = "?"
            if self.chain.last.is_array or self.chain.last.is_str:
                field_type = 'INP'
            else:
                field_type = 'OUT'
        elif 'i' in io:
            assign_symbol = "?"
            field_type = 'INP'
        elif 'o' in io:
            assign_symbol = "="
            if self.chain.last.is_array or self.chain.last.is_str:
                field_type = 'INP'
            else:
                field_type = 'OUT'

        str_template = '"@asyn($(PORT),0,1)ADSPORT={port}/{name}{symbol}"'

        final_str = str_template.format(
            port=self.ads_port,
            name=name,
            symbol=assign_symbol,
        )

        try:
            res, = self.cfg.get_config_fields(field_type)
            return False
        except ValueError:
            pass

        self.cfg.add_config_field(field_type, final_str)
        return True

    @_skip_if_field_set('SCAN')
    def guess_SCAN(self):
        """
        add field for SCAN field

        Returns
        -------
        bool
            Return a boolean that is true iff a change has been made.
        """

        io, = self.cfg.get_config_lines('io')
        if 'i' in io['tag'] and 'o' in io['tag']:
            self.cfg.add_config_field("SCAN", '"Passive"')
            self.cfg.add_config_line("info", True)
            return True

        elif 'i' in io['tag']:
            fast_i_set = {'BOOL'}
            if self.chain.last.tc_type in fast_i_set:
                self.cfg.add_config_field("SCAN", '"I/O Intr"')
                return True
            else:
                self.cfg.add_config_field("SCAN", '".5 second"')
                return True
        elif 'o' in io['tag']:
            self.cfg.add_config_field("SCAN", '"Passive"')
            return True

        return False

    # guess lines below this comment are not always used (context specific)

    @_skip_if_field_set('ONAM')
    def guess_ONAM(self):
        """
        Add ONAM fields for booleans

        Returns
        -------
        bool
            Return a boolean that is true iff a change has been made.
        """
        if self.chain.last.tc_type in {'BOOL'}:
            self.cfg.add_config_field("ONAM", "One")
            return True
        return False

    @_skip_if_field_set('ZNAM')
    def guess_ZNAM(self):
        """
        Add ZNAM fields for booleans

        Returns
        -------
        bool
            Return a boolean that is true iff a change has been made.
        """
        if self.chain.last.tc_type in {'BOOL'}:
            self.cfg.add_config_field("ZNAM", "Zero")
            return True

        return False

    @_skip_if_field_set('PREC')
    def guess_PREC(self):
        """
        Add precision field for the ai/ao type

        Returns
        -------
        bool
            Return a boolean that is true iff a change has been made.
        """
        try:
            epics_type, = self.cfg.get_config_lines("type")
        except ValueError:
            # raise MissingConfigError
            return False

        float_set = {'ai', 'ao'}
        if epics_type['tag'] in float_set:
            self.cfg.add_config_field("PREC", '"3"')
            return True

        return False

    @_skip_if_field_set('FTVL')
    def guess_FTVL(self):
        """
        Add datatype specification field for waveforms
        """
        if self.chain.last.is_array:
            tc_type = self.chain.last.tc_type
            if tc_type == "BOOL":
                self.cfg.add_config_field("FTVL", '"CHAR"')
                return True
            INT_set = {"INT", "ENUM"}
            if tc_type in INT_set:
                self.cfg.add_config_field("FTVL", '"SHORT"')
                return True
            DINT_set = {"DINT"}
            if tc_type in DINT_set:
                self.cfg.add_config_field("FTVL", '"LONG"')
                return True
            if tc_type == "REAL":
                self.cfg.add_config_field("FTVL", '"FLOAT"')
                return True
            if tc_type == "LREAL":
                self.cfg.add_config_field("FTVL", '"DOUBLE"')
                return True

        if self.chain.last.is_str:
            self.cfg.add_config_field("FTVL", '"CHAR"')
            return True

        return False

    @_skip_if_field_set('NELM')
    def guess_NELM(self):
        """
        Add data length secification for waveforms
        """
        if self.chain.last.is_array or self.chain.last.is_str:
            length = self.chain.last.iterable_length
            self.cfg.add_config_field("NELM", length)
            return True

        return False

    def guess_all(self):
        """
        Cycle through guessing methods until none can be applied.
        guess_methods_list is a list of functions.
        """
        complete = False
        count = 0
        while not complete:
            count += 1
            assert count < 20
            complete = True
            for method in self.guess_methods_list:
                if method() is True:
                    complete = False

    def render_to_string(self):
        """
        Create the individual record to be inserted in the DB file. To be
        returned as a string.
        redundant?
        """
        raise NotImplementedError
