"""
xml_obj.py

This file contains the objects for representing the essential TwinCAT
variables and data structures found in the xml (tmc) formatted file.
"""
import logging
logger = logging.getLogger(__name__)
import xml.etree.ElementTree as ET
from collections import defaultdict

class BaseElement:
    '''
    Base class for representing variables as they appear in the .tmc (xml)
    format.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytpy's consumption. 
    '''
    def __init__(self, element, base='pytpy'):
        if type(element) != ET.Element:
            raise TypeError("ElementTree.Element required")
        self.element = element
        self.registered_pragmas = []
        self.com_base = base

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

        dict()
            Dictionary. The key is the property name and the value is a list of
            values found in the xml
        """
        raw = self._get_raw_properties()
        if raw == None:
            return None

        result = defaultdict(list)

        for entry in raw:
            name_element = entry.find("./Name")
            if name_element == None:
                logger.debug("Property Name not found")
                continue

            name_text = name_element.text

            value_element = entry.find("./Value")
            if value_element == None:
                value_text = None
            else:    
                value_text = value_element.text
            
            result[name_text].append(value_text)

        return result

    @property
    def pragmas(self):
        """
        Produce a stripped-down set of properties including only those that are
        recognized as pragmas intended for pytpy's consumption. 

        Returns
        -------

        dict()
            Dictionary. The key is the property name and the value is a list of
            values found in the xml
        """
        props = self.properties
        pragmas = defaultdict(list)
        for entry in self.registered_pragmas:
            if entry in props:
                pragmas[entry] = props.get(entry)

        return pragmas

    def _get_raw_parent(self):
        '''
        slated for removal
        '''
        return self.element.find('.')

    def get_subfield(self, field_target, get_all=False):
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
        if get_all:
            target_element = self.element.findall("./"+field_target)
        else:
            target_element = self.element.find("./"+field_target)

        return target_element 

    @property
    def tc_type(self):
        raise NotImplementedError


class Symbol(BaseElement):
    '''
    Inherits from :class:`~pytpy.xml_obj.BaseElement`

    Symbol instances represent instantiated variables and DataTypes. 

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytpy's consumption. 
    '''
    def __init__(self, element, base='pytpy'):
        super().__init__(element, base)
        registered_pragmas = [
            self.com_base + '_field', 
            self.com_base + '_pv', 
        ]
        if element.tag != 'Symbol':
            logger.warning("Symbol instance not matched to xml Symbol")

    @property
    def tc_type(self):
        '''
        Return the type of the data this symbol represents.

        Returns
        -------

        str
            Name of data type
        '''
        name_field = self.get_subfield("BaseType")
        return name_field.text


class DataType(BaseElement):
    '''
    Inherits from :class:`~pytpy.xml_obj.BaseElement`

    DataType instances represents the templates for uninstantiated 
    FunctionBlocks, Enums, Structs, Unions, and Aliases. 

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytpy's consumption. 
    '''
    def __init__(self, element, base='pytpy'):
        super().__init__(element, base)
        self.registered_pragmas = [
            self.com_base + '_ds_name',
        ]
        if element.tag != 'DataType':
            logger.warning("DataType instance not matched to xml DataType")
    
    @property
    def tc_type(self):
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

        if None != self.get_subfield("EnumInfo"):
            has_EnumInfo = True
            
        if None != self.get_subfield("SubItem"):
            has_SubItem = True
        
        if None != self.get_subfield("Properties"):
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
    def tc_extends(self):
        '''
        Return the DataType that this DataType is built upon

        Returns
        -------

        str
            DataType name

        '''
        extension_element = self.get_subfield("ExtendsType")
        return extension_element.text


class SubItem(BaseElement):
    '''
    Inherits from :class:`~pytpy.xml_obj.baseElement`

    SubItem instances represent variables and DataTypes instantiated within
    DataTypes.

    Parameters
    ----------
    element : xml.etree.ElementTree.Element
        A python xml element object connected to the intended .tmc datagroup

    base : str
        The prefix that will mark pragmas intended for pytpy's consumption.

    parent : :class:`~pytpy.xml_obj.baseElement`
        The DataStructure in which this SubItem appears
    '''
    def __init__(self, element, base='pytpy', parent = None):
        super().__init__(element, base)
        registered_pragmas = [
            self.com_base + '_field', 
            self.com_base + '_pv', 
        ]

        self.parent = parent

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
            Name of data type
        '''
        name_field = self.get_subfield("Type")
        return name_field.text
    
    
