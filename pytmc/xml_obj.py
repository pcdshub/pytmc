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
        if type(element) != ET.Element:
            raise TypeError("ElementTree.Element required")
        self.element = element
        self.registered_pragmas = []
        if base == None:
            self.com_base = 'pytmc'
        else:
            self.com_base = base
        if suffixes == None:
            self.suffixes = {
                'Pv' : '_pv',
                'DataType' : '_dt_name',
                'Field' : '_field'
            }
        else:
            self.suffixes = suffixes

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

        result = {}

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
            
            result[name_text] = value_text

        return result

    @property
    def pragmas(self):
        """
        Produce a stripped-down set of properties including only those that are
        recognized as pragmas intended for pytmc's consumption. 

        Returns
        -------

        dict
            Dictionary. The key is the property name and the value is a list of
            values found in the xml

        """
        props = self.properties
        pragmas = {}
        for entry in self.registered_pragmas:
            if entry in props:
                pragmas[entry] = props.get(entry)

        return pragmas
    
    @property
    def has_pragma(self):
        '''
        Shortcut for determining if this element has pragmas. 
        
        Returns
        -------
        bool
            True if there are regestered pragmas attached to this xml element
        '''
        if len(self.pragmas) > 0:
            return True

        return False

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

    def __eq__(self,other):
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
        if self.element == None:
            name = "None"
        else:
            name = "<xml(" + self.element.find("./Name").text + ")>"
            #name = "<xml(" + self.element.tag + ")>"
            
        return "{}(element={})".format(
            self.__class__.__name__,
            name 
        )

    @property
    def name(self):
        '''
        Return the TwinCAT name for this Symbol/DataType/SubItem. This info is
        taken from the text of the name field sub-element.

        Returns
        -------
        str
            The name of the variable
        '''
        return self.get_subfield("Name").text

    @property
    def pv(self):
        '''
        Get the pragma designated PV name for this xml entity.

        Returns
        -------
        str
            The pv or partial pv
        '''
        pragma_pv_string = self.pragmas[self.com_base+self.suffixes['Pv']]
        match = re.search(
            r"(?P<pv>[\S]+)(?P<space>[^\S]*)(?P<record_type>[\S]*)",
            pragma_pv_string
        )
        return match.group('pv')
    
    @property
    def field(self):
        '''
        Get the pragma designated fields for this xml entity.

        Returns
        -------
        dict
            Contains pairings between the parameter names (key) and the
            parameter settings (value)
        '''
        pragma_field = self.pragmas[self.com_base+self.suffixes['Field']]
        pattern = "(?P<field>[\S]+)(?:[^\S]+)(?P<set>[\S]+)(?:[.]*)(?:[\r\n]*)"
        matches = re.findall( pattern, pragma_field)
        return dict(matches)
        for x in matches:
            print(x)
            #print(x.group())

    @property
    def dtname(self):
        '''
        Get the pragma designated data type name for this DataType.

        Returns
        -------
        str
            The partial pv
        '''
        pragma_dt = self.pragmas[self.com_base+self.suffixes['DataType']]
        return pragma_dt.strip()
    
    @property
    def record_type(self):
        '''
        Get the pragma designated record type for this xml entity.

        Returns
        -------
        str
            Record type
        '''
        pragma_pv_string = self.pragmas[self.com_base+self.suffixes['Pv']]
        match = re.search(
            r"(?P<pv>[\S]+)(?P<space>[^\S]*)(?P<record_type>[\S]*)",
            pragma_pv_string
        )
        return match.group('record_type')


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
        self.registered_pragmas = [
            self.com_base + self.suffixes['Field'], 
            self.com_base + self.suffixes['Pv'], 
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
        self.registered_pragmas = [
            self.com_base + self.suffixes['DataType'],
        ]
        
        self.children = []

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

        str or None
            DataType name or None if there is no parent 

        '''
        extension_element = self.get_subfield("ExtendsType")
        if extension_element == None:
            return None
        return extension_element.text
    

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
        self.registered_pragmas = [
            self.com_base + self.suffixes['Field'], 
            self.com_base + self.suffixes['Pv'], 
        ]
        self.__parent = None
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
            print("NEW_LIST",new_list)
            self.__parent.children = new_list
            self.__parent = None 
    
