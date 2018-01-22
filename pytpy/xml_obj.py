"""
xml_obj.py

This file contains the objects for representing the essential TwinCAT
datastructures found in xml (tmc) formatted file.
"""
import logging
logger = logging.getLogger(__name__)
import xml.etree.ElementTree as ET
from collections import defaultdict

class BaseElement:

    def __init__(self, element, base='pytpy'):
        if type(element) != ET.Element:
            raise TypeError("ElementTree.Element required")
        self.element = element
        self.registered_pragmas = []
        self.com_base = base

    def _get_raw_properties(self):
        return self.element.findall("./Properties/*")

    @property
    def properties(self):
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
        if get_all:
            target_element = self.element.findall("./"+field_target)
        else:
            target_element = self.element.find("./"+field_target)

        return target_element 

    @property
    def tc_type(self):
        raise NotImplementedError
                
                    
class Symbol(BaseElement):
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
        name_field = self.get_subfield("BaseType")
        return name_field.text

class DataType(BaseElement):
    def __init__(self, element, base='pytpy'):
        super().__init__(element, base)
        self.registered_pragmas = [
            self.com_base + '_ds_name',
        ]
        if element.tag != 'DataType':
            logger.warning("DataType instance not matched to xml DataType")
    
    
    @property
    def tc_type(self):
        
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


class SubItem(BaseElement):
    def __init__(self, element, parent=None, base='pytpy'):
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
        name_field = self.get_subfield("Type")
        return name_field.text
    
    
