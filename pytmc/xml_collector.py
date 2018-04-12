"""
xml_collector.py

This file contains the objects for intaking TMC files and generating python
interpretations. Db Files can be produced from the interpretation
"""
import logging
logger = logging.getLogger(__name__)
import xml.etree.ElementTree as ET
from collections import defaultdict, OrderedDict as odict
from . import Symbol, DataType, SubItem
from copy import deepcopy
from .xml_obj import BaseElement



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
        dict.__setitem__(self,name,value)

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
        return {name:self[name] for name in names}


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

    '''
    def __init__(self, filename):
        self.filename = filename
        self.tree = ET.parse(self.filename)
        self.root = self.tree.getroot()

        self.all_Symbols = ElementCollector()
        self.all_DataTypes = ElementCollector()
        self.all_SubItems = defaultdict(ElementCollector) 
        self.isolate_all()

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

    def isolate_DataTypes(self,process_subitems=True):
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

    def isolate_SubItems(self,parent=None):
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

    def isolate_all(self):
        '''
        Shortcut for running :func:`~isolate_Symbols` and
        :func:`~isolate_DataTypes`
        '''
        self.isolate_Symbols()
        self.isolate_DataTypes()


class PvPackage:
    '''
    PvPackage stores the information for each PV to be created. These instances
    can store the complete set of configuration lines. The initial set is taken
    from the pragma and those unfilled are guessed into place when the object
    is created.

    Deprecate the following? 
    Most of the work occurs during instantiation so the instances of this
    object are intended for single setup.

    Parameters
    ----------
    target_path : list
        This is a list of Symbols, DataTypes, and/or subitems leading to the
        targeted TwinCAT variable

    pragma : list
        The list of configuration lines specific to a single PV, taken from the
        config_by_pv method. 

    proto_name : str, optional
        The name for this proto method.

    proto_file_name : str, optional
        The local file name for the proto file. Full path is not necessary

    Attributes
    ----------
    target_path : list
        Identical to target_path parameter

    pragma : list
        this list of dictionaries is a deep-copied version of the pragmas
        attached to the TwinCAT variable. This variable is meant for
        guessing in the automated fields.

    pv_partial : str
        This str designates the pv term specific to this variable.

    pv_complete : str
        The full PV for this variable concatenating all encapsulating PVs and
        the target PV. 

    proto_name : str, None
        Identical to proto_name parameter.

    proto_file_name : str, None
        Identical to proto_file_name parameter.

    guessing_applied : bool
        Have the guessing procedures been run yet?
    '''
    versions = ['legacy']
    
    def __init__(self, target_path, pragma, proto_name=None,
            proto_file_name=None, use_proto=True,version='legacy'):
        self.define_versions()
        self.target_path = target_path
        # Create separate pragma copy to hold both original and guessed lines 
        self.pragma = deepcopy(pragma)
        # Acquire the Pv attached to this pragma (may only be the tail)
        for row in self.pragma:
            if row['title'] == 'pv':
                pv = row['tag']
        # Set partial to the component of the PV specified in this element
        self.pv_partial = pv
        # Construct the full PV by iterating through all PVs in the path
        self.prefix = ""
        for entry in target_path[:-1]: 
            self.prefix += (entry.pv + ":")
        self.pv_complete = self.prefix + self.pv_partial
        # Save the name of the proto method and file
        self.proto_name = proto_name

        self.proto_file_name = proto_file_name
        # Indicate that guessing procedures have not been applied
        self.guessing_applied = False
        self.version = version
        self.set_version()

    def define_versions(self):
        '''Define all auto-complete rule sets for ALL versions.
        '''
        # list out required pragma fields for this version
        self._all_req_fields = {
            'legacy':[
                odict([('pv',['title'])]),
                odict([('type',['title'])]),
                odict([('str',['title'])]),
                odict([('io',['title'])]),
                odict([('field',['title']),('DTYP',['tag','f_name'])]),
                odict([('field',['title']),('SCAN',['tag','f_name'])]),
                odict([('field',['title']),('INP',['tag','f_name'])]),
            ]
        }

        '''
        # list out variables that must be =/= None for this version 
        sefl._all_req_vars = {
            'legacy':[
                self.proto_name,
                self.
            ]
        }

        '''
        # list the approved guessig methods for this version 
        self._all_guess_methods = {
            'legacy': [
            ]
        }

        # list if this version uses the proto file 
        self._all_use_proto = {
            'legacy': True
        }

    def set_version(self):
        '''Set variables indicating the rules for the version this pack uses
        '''
        self.req_fields = self._all_req_fields[self.version]
        # self.req_vars = ._all_req_vars[self.version] 
        self.guess_methods = self._all_guess_methods[self.version]
        self.use_proto = self._all_use_proto[self.version]

    def term_exists(self, req_line):
        '''Return True if the req_line (required rule) exists in pragma
        '''
        for row in self.pragma:
            # determine wether this line satisfies the rule 
            valid = True
            for req_term in req_line:
                # req_term indicates the individual tags that mush exist
                req_location = req_line[req_term]
                try:
                    # recursively step into encapsulated dictionaries
                    target = row
                    for page in req_location:
                        target = target[page]
                    # If the term found at the end of dictionary rabbit-hole
                    # matches, accept it and check the next term of the rule.
                    # Allow valid to remain true
                    valid = valid and (target == req_term)
                    if not valid:
                        break
                except KeyError:
                    valid = False
                    break
            
            if valid == True:
                return True

        return False

    def missing_pragma_lines(self):
        '''Identify missing pragma lines in an array.
        '''
        requirment = self.req_fields[self.version]
        rejection_list = []
        for req_line in requirement:
            # each req_line is an individual requirement for a term to exist
            for req_term in req_line:
                # some terms need multiple 'tiers' to be verivied to exist
                #if  != term 
                pass
            



    @property
    def is_config_complete(self):
        '''Return True if all necessary config information is pressent
        '''
        raise NotImplementedError  
        
         
    @classmethod
    def from_element_path(cls, target_path, base_proto_name=None, 
            proto_file_name=None, use_proto=True):
        '''
        Produce a list of PvPackage instances, one for each unique PV being
        created from a specific TwinCAT variable. 
        
        Parameters
        ----------
        target_path : list
            Identical to target_path in __init__.
    
        proto_name : str, None
            Identical to proto_name parameter in __init__.
    
        proto_file_name : str, None
            Identical to proto_file_name parameter in __init__.
        '''
        pvpacks_output_list = []

        # Iterate through each pragma-set (one per PV) for the final element in
        # target path
        for config_set in target_path[-1].config_by_pv:
            io_line = BaseElement.parse_pragma('io',config_set)
            if "o" in io_line:
                proto_name = "Set" + base_proto_name
            elif "i" in io_line:
                proto_name = "Get" + base_proto_name

            new_pvpack = cls(
                target_path = target_path,
                pragma = config_set,
                proto_name = proto_name,
                proto_file_name = proto_file_name,
                use_proto = use_proto
            )
            pvpacks_output_list.append(new_pvpack)

        return pvpacks_output_list

    def add_config(self, title, setting, field=False):
        """Add a single entry to this object's pragma

        Parameters
        ----------
        title : str
            Configuration lines and fields have both a title designating what
            the line sets. This string sets the configuraiton type or the field
            type.

        setting : str
            Configuration lines and fields must then apply some setting. This
             argument defines what setting is applied.

        field : bool, optional, defaults to False
            If true, this method will add a field line with title and setting
            specified by the previous parameters,
        """
        if field:    
            new_entry = {
                'title': 'field', 
                'tag': {'f_name': title, 'f_set': setting}
            }
        
        else:
            new_entry = {'title': title, 'tag': setting}

        self.pragma.append(new_entry)
        
    
    def create_record(self):
        raise NotImplementedError

    def create_proto(self):
        raise NotImplementedError

