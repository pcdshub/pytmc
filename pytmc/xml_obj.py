"""
xml_obj.py

This file contains the objects for representing the essential TwinCAT
variables and data structures found in the xml (tmc) formatted file.
"""
import logging
logger = logging.getLogger(__name__)
import xml.etree.ElementTree as ET
from collections import defaultdict
import re


class XmlObjError(Exception):
    pass


class NotStringError(Exception):
    pass


class PvNotFrozenError(XmlObjError):
    pass


class Configuration:
    def __init__(self, in_str=None, config=None):
        """
        """
        # str: self._raw_config (READ ONLY, set at instantaiation)
        # list: self.config
        self._raw_config = in_str
        if config is None:
            self.config = self._formatted_config_lines()
        else:
            self.config = config
        # what name identifies unique configurations? cfg_header
        self.cfg_header = 'pv'
        self.cfg_skip = 'skip'

    @property
    def raw_config(self):
        """
        raw_config will behave like a read-only variable
        """
        return self._raw_config

    def _config_lines(self, raw_config=None):
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
        if raw_config is None:
            raw_config = self._raw_config

        # Select special delimiter sequences and prepare them for re injection
        line_term_seqs = [r";",r";;",r"[\n\r]",r"$"]
        flex_term_regex = "|".join(line_term_seqs)


        # Break configuration str into list of lines paired w/ their delimiters 
        line_finder = re.compile(
            r"(?P<line>.+?)(?P<delim>"+flex_term_regex+")"
        )
        conf_lines = [m.groupdict() for m in line_finder.finditer(raw_config)]
        
        # create list of lines information only. Strip out delimiters
        result_no_delims = [r["line"] for r in conf_lines]

        # erase any empty lines
        result_no_delims = [
            x for x in result_no_delims if x.strip() != ''
        ]

        # Break lines into list of dictionaries w/ title/tag structure
        line_parser = re.compile(
            r"(?P<title>[\S]+):(?:[^\S]*)(?P<tag>.*)"
        )
        result = [
            line_parser.search(m).groupdict() for m in result_no_delims
        ]

        # Strip out extra whitespace in the tag
        for line in result:
            line['tag'] = line['tag'].strip()
        
        return result
        
    def _neaten_field(self, string):
        """
        When applied to field line's tag, break the string into its own dict
        
        Parameters
        ----------
        string : str
            This is the string to be broken into field name and field setting

        Returns
        -------
        dict
            Keys are 'f_name' for the field name and 'f_set' for the
            corresponding setting.
        """
        finder = re.compile(
            r"(?P<f_name>[\S]+)(?:[^\S]*)(?P<f_set>.*)"
        )
        return finder.search(string).groupdict()

    def _formatted_config_lines(self, config_lines=None): 
        """
        Apply the neaten (_neaten_fields) methods to clean up _config_lines.
        Formerly _config
        Derived from _config_lines
        Derived from raw_config

        Parameters
        ----------
        config_lines : list 
            This is the list of line-by-line dictionaries. Has the same format
            as the return of :func:`~_config`. Defaults to raw_config.
        
        Returns
        -------
        list
            this list contains dictionaries for each line of the config 
            statement


        """
        if config_lines is None:
            config_lines = self._config_lines()
        
        for line in config_lines:
            if line['title'] == 'field':
                line['tag'] = self._neaten_field(line['tag'])
        return config_lines

    def _config_by_name(self, formatted_config_lines=None): 
        """
        Break pragma block into separate lists for each Configuration (Pv)
        Formerly config_by_pv
        Derived from _formatted_config_lines
        Can be derived from raw_config or config
        
        Parameters
        ----------
        formatted_config_lines : list
            List of line-by-line dictionaries for each line of the
            configuration text with fields broken up. Same format as the return
            of :func:`~_formatted_config_lines`. Defaults to raw_config.
        
        Returns
        -------
        list 
            This list contains a list for each unique PV. These lists contain
            dictionaries, one for each row of the pragma.
        """
        if formatted_config_lines is None:
            formatted_config_lines = self._formatted_config_lines()

        separate_lists = []
        for line in formatted_config_lines:
            if line['title'] == self.cfg_header:
                separate_lists.append([])
                index = len(separate_lists) - 1
            separate_lists[index].append(line)
        return separate_lists

    def _select_config_by_name(self, config_name, formatted_config_lines=None):
        """
        Produce subset of formatted_config_lines specific to given config_name
        derived from _config_by_name
        can be derived from raw_config or config

        Parameters
        ----------
        config_name : str
            string for the target configuration name you're looking for

        formatted_config_lines : list, optional
            List of line-by-line dictionaries with formatted fields like the
            output of :func:`~_formatted_config_lines`. Defaults to the raw
            configuration

        Returns
        -------
        list
            List of formatted configuration lines specific to the configuration
            named in the parameters. If there was no such configuration, return
            None instead.
        """
        if formatted_config_lines is None:
            formatted_config_lines = self._formatted_config_lines()
                
        specific_configs = self._config_by_name(formatted_config_lines)

        for spec_config in specific_configs:
            if {'title': self.cfg_header, 'tag': config_name} in spec_config:
                return spec_config

        return []

    def config_names(self, formatted_config_lines=None):
        """
        Produce a list of configuration names (Pvs)
        Derived from _config_by_name
        Can be derived from raw_config or config

        Parameters
        ----------
        formatted_config_lines : list 
            List of line-by-line dictionaries with formatted fields like the
            output of :func:`~_formatted_config_lines`. Defaults to the
            processed configuration

        Returns
        -------
        list
            List of strings of all configurations found
        """
        if formatted_config_lines is None:
            formatted_config_lines = self.config
        specific_configs = self._config_by_name(formatted_config_lines)
        config_names_list = list()
        for specific_config in specific_configs:
            for line in specific_config:
                if line['title'] == self.cfg_header:
                    config_names_list.append(line['tag'])

        return config_names_list

    def fix_to_config_name(self, config_name):
        """
        Cut config down to a single configuration
        Derived from _select_config_by_name

        Parameters
        ----------
        config_name : str
            Provide the name of the 

        Returns
        -------
        None
        """
        self.config = self._select_config_by_name(config_name)

    def add_config_line(self, title, tag, line_no=None, config=None,
                overwrite=False):
        """
        add basic line to config

        Parameters
        ----------
        title : str
            The title or 'type' of the new line 

        tag : str
            The argument for the new line 

        line_no : int, optional
            The line at which to insert the new line. Defaults to appending it
            at the end 

        config : list, optional
            List of line-by-line dictionaries with formatted fields like the
            output of :func:`~_formatted_config_lines`. Defaults to
            self.config.

        overwrite : bool
            Defaults to False. If the line already exists, overwrite it. 

        Returns
        -------
        None
        """
        if config is None:
            config = self.config

        new_line = {'title': title, 'tag': tag}

        if overwrite:
            for line in self.get_config_lines(title):
                if line['title'] == title:
                    line['tag'] = tag
                    return
        
        if line_no is None:
            config.append(new_line)
        else:
            config.insert(line_no, new_line)

    def add_config_field(self, f_name, f_set, line_no=None, config=None,
                overwrite=False):
        """
        add field to config

        Parameters
        ----------
        f_name : str
            The new field type 

        f_set : str
            The argument for the setting

        line_no : int, optional
            The line at which to insert the new line. Defaults to appending it
            at the end 

        config : list, optional
            List of line-by-line dictionaries with formatted fields like the
            output of :func:`~_formatted_config_lines`. Defaults to
            self.config.

        overwrite : bool
            Defaults to False. If the line already exists, overwrite it. 

        Returns
        -------
        None

        """
        if overwrite:
            for field in self.get_config_fields(f_name):
                if line['tag']['f_set'] == f_set:
                    self.add_config_line(
                        title='field',
                        tag={'f_set': f_set, 'f_name': f_name},
                        line_no=line_no,
                        config=config,
                        overwrite=True
                    )


        self.add_config_line(
            title='field',
            tag={'f_set': f_set, 'f_name': f_name},
            line_no=line_no,
            config=config,
            overwrite=False
        )

    def get_config_lines(self, title, config=None):
        """
        return list of lines of this title type

        Parameters 
        ----------
        title : str
            Provide a list of all config lines with this title

        config : list, optional
            List of line-by-line dictionaries with formatted fields like the
            output of :func:`~_formatted_config_lines`. Defaults to
            self.config.

        Returns
        -------
        list
            list contains all configuration line dictionaries with the proper
            title. Preserves order.
        """
        if config is None:
            config = self.config

        results_list = []
        for line in config:
            if line['title'] == title:
                results_list.append(line)

        return results_list

    def get_config_fields(self, f_name, config=None):
        """
        return list of fields of this f_name type

        Parameters 
        ----------
        f_name : str
            Provide a list of all config fields with this f_name

        config : list, optional
            List of line-by-line dictionaries with formatted fields like the
            output of :func:`~_formatted_config_lines`. Defaults to
            self.config.

        Returns
        -------
        list
            list contains all configuration line dictionaries with the proper
            title. Preserves order.
        """

        results_list = []
        fields_list = self.get_config_lines('field',config)

        for line in fields_list:
            if line['tag']['f_name'] == f_name:
                results_list.append(line)

        return results_list

    def __eq__(self,other):
        """
        two Configurations are equal if their _raw_config and config are the
        same
        """
        if other.__class__ != Configuration:
            return False

        if (other._raw_config == self._raw_config
                    and other.config == self.config):
            return True

        return False

    def concat(self, other, cc_symbol = ":"):
        """
        Using configs from an object and its encapsulated data, string the two
        together concatenating the PV and using the outside (self) config to
        assume any unfilled entries in the interior (other) config. Only works
        for singular or empty Configurations.

        Parameters
        ----------
        other : Configuration
            This configuration will be added onto the tail of this
            configuration. 'other' represents the interanal configuration.

        cc_symbol : str, optional
            When concatenating the PV. Add this seperator between individual
            PV's. Defaults to ":". 
        """
        if not self.config_names():
            title_base = ""
        if len(self.config_names()) == 1:
            title_base = self.config_names()[0]+cc_symbol
        
        for line in other.config:
            # handle config titles
            if line['title'] == self.cfg_header:
                self.add_config_line(
                    title=self.cfg_header,
                    tag=title_base+line['tag'],
                    overwrite=True
                )
            # handle fields
            elif line['title'] is 'field':
                self.add_config_field(
                    f_name=line['tag']['f_name'],
                    f_set=line['tag']['f_set'],
                    overwrite=True
                )
            # hanlde all normal lines
            else:
                self.add_config_line(
                    title = line['title'],
                    tag = line['tag'],
                    overwrite=True
                )

    def seek(self, path, target):
        """
        Return list of parameters that fit this description.
       
        Parameters
        ----------
        path : list
            List of dictionary keys to seek the target value
        target : any
            The value or variable expected at this location

        Returns
        -------
        List 
            list of all rows that fulfill the given description
        """
        results = []
        for line in self.config:
            z = line 
            for step in path:
                if type(z) is not dict:
                    break
                try:
                    z = z[step]
                except KeyError:
                    pass
            if z == target:
                results.append(line)

        return results


class BaseElement:
    '''
    Base class for representing variables as they appear in the .tmc (xml)
    format.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytmc's consumption.
    '''
    def __init__(self, element, base=None, suffixes=None):
        if type(element) != ET.Element and element is not None:
            raise TypeError("ElementTree.Element required")
        self.is_array_ = None
        self._string_info_ = None
        self.is_str_ = None
        self.iterable_length_ = None
        
        self.is_enum_ = None
        
        self.element = element
        #self.registered_pragmas = []
        #self.freeze_config = False
        #self.freeze_pv_target = None 

        if base is None:
            self.com_base = 'pytmc'
        else:
            self.com_base = base
            
        #if suffixes is None:
        #    self.suffixes = {
        #        'Pv': '_pv',
        #        'DataType': '_dt_name',
        #        'Field': '_field'
        #    }
        #else:
        #    self.suffixes = suffixes

        #self._pragma = None
        self._cached_name = None
        
        # This is to allow testing without actual tmc elements 
        if element is None:
            self.pragma = None 
            return

        raw_config = self.raw_config
        if raw_config is None:
            self.pragma = None
        else:
            self.pragma = Configuration(self.raw_config)

    def _get_raw_properties(self):
        """
        Obtain all elements contained in the 'Properties' element. Intended for
        internal use.

        Returns
        -------
        [xml.etree.ElementTree.Element]
            List of elements
        """
        return self.element.findall("./Properties/*")

    @property
    def properties(self):
        """
        Produce a dictionary of lists for the properties associated with this
        element. The value of the dictionary is a list allowing for multiple
        properties w/ the same name.

        Returns
        -------
        dict
            Dictionary. The key is the property name and the value is a list of
            values found in the xml
        """
        raw = self._get_raw_properties()
        if raw is None:
            return None

        result = {}

        for entry in raw:
            name_element = entry.find("./Name")
            if name_element is None:
                logger.debug("Property Name not found")
                continue

            name_text = name_element.text

            value_element = entry.find("./Value")
            if value_element is None:
                value_text = None
            else:
                value_text = value_element.text

            result[name_text] = value_text

        return result

    @property
    def raw_config(self):
        """
        Produce a stripped-down set of properties including only those that are
        recognized as pragmas intended for pytmc's consumption.

        Returns
        -------

        str or None
            produce the string from the pragma marked for pytmc or a None if no
            such pragma can be found

        """
        return self.properties.get('pytmc')

    @property
    def has_config(self):
        '''
        Shortcut for determining if this element has pragmas.

        Returns
        -------
        bool
            True if there is a config pragma attached to this xml element
        '''
        if self.raw_config is not None:
            return True

        return False

    def _get_subfield(self, field_target, get_all=False):
        """
        Produce element(s) within the class instance's target element. If
        seeking only a single element, return the first one encountered.

        Parameters
        ----------
        
        field_target : str
            The tag name of the contained field

        get_all : bool
            If True, seek all elements, otherwise return only the first
            encountered

        Returns
        -------

        xml.etree.ElementTree.Element or list(xml...Element) or None
            Return the first element found, the list of all elements found. If
            the element is not found None or [] is returned for single-find or
            find-all respectively.
        """
        if self.element is None:
            return None
        if get_all:
            target_element = self.element.findall("./"+field_target)
        else:
            target_element = self.element.find("./"+field_target)

        return target_element

    @property
    def is_array(self):
        """
        This property is true if this twincat element is an array.
        
        Returns
        -------
        Bool
            is true if this twincat element is an array
        """
        if self.is_array_ is not None:
            return self.is_array_
        if self.element is None:
            return False
        if None != self._get_subfield('ArrayInfo'):
            return True
        return False
    
    @is_array.setter
    def is_array(self, new_data):
        """
        Make setable for tests
        """
        self.is_array_ = new_data

    @property
    def _string_info(self):
        """
        Internal method for getting stats on strings
        
        Returns
        -------
            Bool, int or None
            The bool indicates whether or not this is a string. The Int will
            return the lenght or a None if it is not a string.
        """
        if self._string_info_ is not None:
            return self._string_info_
        
        base_type = self._get_subfield('BaseType')
        if base_type is None:
            return False, None
        base_type_str = base_type.text

        finder = re.compile(r"(?P<type>STRING)\((?P<count>[0-9]+)\)")
        result = finder.search(base_type_str)
        if result is None:
            return False, None
        if result['type'] == "STRING":
            return True, int(result['count'])
    
    @_string_info.setter
    def _string_info(self, new_data):
        """
        Make setable for tests
        """
        self._string_info_ = new_data
        
    @property
    def iterable_length(self):
        """
        Obtain the length of an iterable type.

        Returns
        -------
        int or None
            Return the length of the string/array if the element is a string or
            an array. Otherwise return None
        """
        if self.iterable_length_ is not None:
            return self.iterable_length_
        if self.is_str:
            is_str, str_len = self._string_info
            return str_len
        if self.is_array:
            response_string = self._get_subfield('ArrayInfo/Elements')
            logger.debug("text:" + str(response_string.text))
            return int(response_string.text)
    
    @iterable_length.setter
    def iterable_length(self, new_data):
        """
        Make setable for tests
        """
        self.iterable_length_ = new_data
    
    @property
    def is_str(self):
        """
        This property is true if this twincat element is a string.
        
        Returns
        -------
        Bool
            is true if this twincat element is an string
        """
        if self.is_str_ is not None:
            return self.is_str_
        if self.element is None:
            return False
        is_str, str_len = self._string_info
        return is_str
    
    @is_str.setter
    def is_str(self, new_data):
        """
        Make setable for tests
        """
        self.is_str_ = new_data

    def __eq__(self, other):
        '''
        Two objects are equal if they point to the same xml element. e.g. their
        element fields point to the same place in the same file.
        '''
        if (type(other) != BaseElement
                and type(other) != Symbol
                and type(other) != DataType
                and type(other) != SubItem):
            return False
        if self.element == other.element:
            return True
        else:
            return False

    def __repr__(self):
        if self.element is None:
            name = "None"
        else:
            name = "<xml(" + self.element.find("./Name").text + ")>"
            
        return "{}(element={})".format(
            self.__class__.__name__,
            name 
        )

    @property
    def name(self):
        '''
        Return the user assigned TwinCAT variable name for this
        Symbol/DataType/SubItem. This info is taken from the text of the name
        field sub-element.

        Returns
        -------
        str
            The name of the variable
        '''
        if self._cached_name is None:
            return self._get_subfield("Name").text
        else:
            return self._cached_name

    @name.setter
    def name(self, name):
        """
        Allow the name to be set for testing purposes
        Paramters
        ---------
        value : any
            Henceforth, return this value instead of the name derived from a
            tmc file.  Setting value to None causes normal derivation of name
            to resume.
        """
        self._cached_name = name


class Symbol(BaseElement):
    '''
    Inherits from :class:`~pytmc.xml_obj.BaseElement`

    Symbol instances represent instantiated variables and DataTypes. 

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytmc's consumption. 
    '''
    def __init__(self, element, base=None,suffixes=None):
        super().__init__(element, base, suffixes)
        #self.registered_pragmas = [
        #    self.com_base + self.suffixes['Field'], 
        #    self.com_base + self.suffixes['Pv'], 
        #]
        if element.tag != 'Symbol':
            logger.warning("Symbol instance not matched to xml Symbol")
        
        # set during isolation phase
        self.is_enum = False

    @property
    def tc_type(self):
        '''
        Return the type of the data this symbol represents.

        Returns
        -------

        str
            Name of data type (e.g. DINT in the case of a basic type or
            'iterator' if it is an instance of a user defined struct/fb named
            'iterator'
        '''
        if self.is_enum:
            return "ENUM"
        if self.is_str:
            return "STRING"
        name_field = self._get_subfield("BaseType")
        return name_field.text


class DataType(BaseElement):
    '''
    Inherits from :class:`~pytmc.xml_obj.BaseElement`

    DataType instances represents the templates for uninstantiated 
    FunctionBlocks, Enums, Structs, Unions, and Aliases.

    Attributes
    ----------
    children : list
        This list contains the :class:`~pytmc.SubItem` instances that this
        DataType contains. It is not recommended to set this attribute
        directly. Instead, set :py:attr:`~pytmc.SubItem.parent`, which
        automates the setup of :py:attr:`~pytmc.DataType.children` for
        bi-directional look-up. 

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytmc's consumption. 
    '''
    children = []
    
    def __init__(self, element, base=None, suffixes=None):
        super().__init__(element, base, suffixes)
        #self.registered_pragmas = [
        #    self.com_base + self.suffixes['DataType'],
        #]
        
        self.children = []

        if element.tag != 'DataType':
            logger.warning("DataType instance not matched to xml DataType")
 
    @property
    def datatype(self):
        '''
        Return the type of the data this symbol represents.

        Returns
        -------

        str
            Name of data type
        '''        
        has_EnumInfo = False
        has_SubItem = False
        has_Properties = False

        if None != self._get_subfield("EnumInfo"):
            has_EnumInfo = True
            
        if None != self._get_subfield("SubItem"):
            has_SubItem = True
        
        if None != self._get_subfield("Properties"):
            has_Properties = True
        
        result = None

        if has_Properties:
            result = "FunctionBlock"
        
        if has_SubItem and not has_Properties:
            result = "Struct"

        if has_EnumInfo:
            result = "Enum"

        return result

    @property
    def tc_type(self):
        return None

    @property
    def tc_extends(self):
        '''
        Return the DataType that this DataType is built upon

        Returns
        -------

        str or None
            DataType name or None if there is no parent 

        '''
        extension_element = self._get_subfield("ExtendsType")
        if extension_element == None:
            return None
        return extension_element.text
    

    @property
    def is_enum(self):
        """
        This property is true if this twincat element is an enum. It works for
        Datatypes, symbols and subItems.
        
        Returns
        -------
        Bool
            is true if this twincat element is an enum.
        """
        if self.is_enum_ is not None:
            return self.is_enum_
        if self.element is None:
            return False
        if None != self._get_subfield('EnumInfo'):
            return True
        return False
    

class SubItem(BaseElement):
    '''
    Inherits from :class:`~pytmc.xml_obj.baseElement`

    SubItem instances represent variables and DataTypes instantiated within
    DataTypes.

    Attributes
    ----------
    parent : str or None
        This is a reference to the :class:`~pytmc.DataType` that contains this
        :class:`~pytmc.SubItem`.  We reccommend setting this attribute directly
        instead of setting :attr:`~pytmc.DataType.children`. This property
        automates settting :attr:`~pytmc.DataType.children` for bi-directional
        look-up.  The relationship can be deleted using `del
        SubItem_instance.parent` or by setting :attr:`~pytmc.SubItem.parent`
        equal to None. To create a relationship, simply set
        :attr:`~pytmc.SubItem.parent` equal to the intended parent.


    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytmc's consumption.

    parent : :class:`~pytmc.xml_obj.baseElement`
        The DataStructure in which this SubItem appears
    '''
    def __init__(self, element, base=None, suffixes=None, parent = None):
        super().__init__(element, base, suffixes)
        #self.registered_pragmas = [
        #    self.com_base + self.suffixes['Field'], 
        #    self.com_base + self.suffixes['Pv'], 
        #]
        self.__parent = None
        self.parent = parent
        # set during isolation phase
        self.is_enum = False

        if self.parent == None:
            logger.warning("SubItem has no parent")

        if element.tag != 'SubItem':
            logger.warning("SubItem not matched to xml SubItem")
    
    @property
    def tc_type(self):
        '''
        Return the type of the data this symbol represents.

        Returns
        -------
        str
            Name of data type (e.g. DINT in the case of a basic type or
            'iterator' if it is an instance of a user defined struct/fb named
            'iterator'
        '''
        if self.is_enum:
            return "ENUM"
        if self.is_str:
            return "STRING"
        name_field = self._get_subfield("Type")
        return name_field.text

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self,other):
        del self.parent

        self.__parent = other
        if other == None:
            return
        # add self to parent's list of children 
        if self not in self.__parent.children:
            self.__parent.children.append(self)

    @parent.deleter
    def parent(self):
        if self.__parent != None:
            new_list = list(filter(
                lambda g : g != self,
                self.__parent.children
            ))
            self.__parent.children = new_list
            self.__parent = None 
