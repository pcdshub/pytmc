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
from copy import deepcopy, copy
from .xml_obj import BaseElement
from .beckhoff import beckhoff_types


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
        
        self.all_TmcChains = []

        

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

class TmcChain:
    """
    Pointer to the tmc instances and track order
    """
    def __init__(self, chain):    
        self.chain = chain

class PvPackage:
    pass

class PvPackage_old:
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
    
    def __init__(self, target_path, pragma=None, proto_name=None,
            proto_file_name=None, use_proto=True,version='legacy'):
        self.define_versions()
        self.target_path = target_path
        # Create separate pragma copy to hold both original and guessed lines
        if pragma != None:
            self.pragma = deepcopy(pragma)
        else:
            self.pragma = target_path[-1].config_by_pv()[0]
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
        self._all_req_vars = {
            'legacy':[
                self.proto_name,
                self.
            ]
        }

        '''
        # list the approved guessig methods for this version
        # number referes to which requirement in _all_req_fields (by index)
        self._all_guess_methods = {
            'legacy': {
                 1: [ # type
                    self.set_version
                 ],
                 2: [ # str
                 ],
                 3: [ # io
                 ],
                 4: [ # DTYP field
                 ],
                 5: [ # SCAN field
                 ],
                 6: [ # INP field
                 ],
            }
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
        rejection_list = []
        for req_line in self.req_fields:
            # each req_line is an individual requirement for a term to exist
            if not self.term_exists(req_line):
                rejection_list.append(req_line)
            
        return rejection_list 
            
    @property
    def is_config_complete(self):
        '''Return True if all necessary config information is pressent
        '''
        if len(self.missing_pragma_lines()) == 0:
            return True

        return False

    @classmethod
    def assemble_package_chains(cls, target_path, progress_chain=None):
        '''
        When provided with a target path (list of element objects), assemble
        unique lists for each PV to be created. Because multiple PVs can be
        specified from a single element (arrays or IO pairs) the PV hierarchy
        can follow a tree like structure.

        Parameters
        ----------
        target_path : list of elements
            Specify the sequence of encapsulated elements in order of
            least deeply encapsulated to most deeply encapsulated.

        progress_chain : list or None
            This is the list of individual lists to be returned when the
            recursion is complete. Only used for recursive application of this
            method. 

        Returns
        -------
        list
            List contains lists of elements with frozen PVs such that each list
            can be be used for constructing a single PV package or be 
        '''
        if progress_chain == None:
            progress_chain = []
        target = target_path[0]
        progress_chain_inital_len = len(progress_chain)
        
        new_elements = []
        # Examine the configs in the first entry of the target_path provided
        for config_set in target.config_by_pv():
            # construct the 'virtual tree' of copied 1:1 element-pragmas  
            pv_line = BaseElement.parse_pragma('pv',config_set)
            element_copy = copy(target)
            element_copy.freeze_pv(pv_line)
            # add array parsing here (for discrete arrays) 
            new_elements.append(element_copy)

        # Iterate through the previously processed chains
        for chain_idx in range(len(progress_chain)):
            for new_elem_idx in range(len(new_elements)):
                if new_elem_idx == 0:
                    # append the new element to an existing chain
                    progress_chain[chain_idx].append(new_elements[new_elem_idx])
                if new_elem_idx > 0:
                    # create new chain and append the new element
                    progress_chain.append(progress_chain[chain_idx].copy())
                    progress_chain[-1].append(new_elements[new_elem_idx])
        # If this is the first-tier call and the progress chain is empty,
        if len(progress_chain) == 0: 
            for new_elem_idx in range(len(new_elements)):
                progress_chain.append([new_elements[new_elem_idx]])

        # Limit recursion depth
        if len(target_path) == 1:
            return progress_chain

        return cls.assemble_package_chains(
            target_path = target_path[1:],
            progress_chain = progress_chain
        )

    @classmethod
    def from_element_path(cls, target_path, base_proto_name=None, 
            proto_file_name=None,use_proto=None,return_rejects=False):
        '''
        Produce a list of PvPackage instances, one for each unique PV being
        created from a specific TwinCAT variable. 
        
        Parameters
        ----------
        target_path : list
            Identical to target_path in __init__.
    
        base_proto_name : str, None
            Stub for the name of the proto. Get/Set will be appended to the
            front depending on io.

        proto_file_name : str, None
            Name of the file to store the protos.

        use_proto : bool, None
            Explicity state whether or not to use protos. Typically this should
            be left undefined (equal to None) so from_element_path will guess 
            it automatically
        '''
        logger.debug("target_path: "+str(target_path))
        logger.debug("t: "+str(target_path[-1].is_array))
        pvpacks_output_list = []
        reject_path_list = []
        # Presume that no proto file is being used if all are left blank 
        if use_proto == None:
            if base_proto_name != None or proto_file_name != None:
                use_proto = True
            else:
                use_proto = False

        direct_paths = cls.assemble_package_chains(target_path)
        
        for path in direct_paths:
            # If the last element in the path isn't default type, don't create
            # a package and pass the path back for further processing
            logging.debug(str(path[-1])+ ' tc_type: ' + path[-1].tc_type)
            target_pv = path[-1].freeze_pv_target
            if '[' in target_pv or ']' in target_pv:
                reject_path_list.append(path)
            # otherwise create a pvpackage
            else:
                # prepare the proto if it is necessary
                if use_proto:
                    io_line = BaseElement.parse_pragma(
                        'io',
                        path[-1].config_by_pv()[0]
                    )
                    try:
                        if "o" in io_line:
                            proto_name = "Set" + base_proto_name
                        elif "i" in io_line:
                            proto_name = "Get" + base_proto_name
                    # If no 'io' value is set, do the following 
                    except TypeError:
                        proto_name = base_proto_name
                else:
                    proto_file_name = None
                    proto_name = None
    
                new_pvpack = cls(
                    target_path = path,
                    proto_name = proto_name,
                    proto_file_name = proto_file_name,
                    use_proto = use_proto
                )
                pvpacks_output_list.append(new_pvpack)
        
        if return_rejects:
            return pvpacks_output_list, reject_path_list
        return pvpacks_output_list

    def make_config(self, title, setting, field=False):
        """Create pragma formatted dict. 

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

        return new_entry
    
    def create_record(self):
        raise NotImplementedError

    def create_proto(self):
        raise NotImplementedError

    def __eq__(self, other):
        """
        Compare the dictionaries of the two objects against one another but
        don't compare the entries in the 'skip field - this causes infinite
        recursion issues 
        """
        skip = [
            '_all_req_fields',
            '_all_req_vars',
            '_all_guess_methods',
            'req_fields',
            'req_vars',
            'guess_methods',
        ] 
        s_dict = {i:self.__dict__[i] for i in self.__dict__ if i not in skip}
        o_dict = {i:other.__dict__[i] for i in other.__dict__ if i not in skip}

        return s_dict == o_dict

