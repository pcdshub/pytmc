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
    registered_pragmas = []

    def __init__(self, element):
        if type(element) != ET.Element:
            raise TypeError("ElementTree.Element required")
        self.element = element

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
                
                    
            

class Symbol(BaseElement):
    pass

class DataType(BaseElement):
    pass

