"""
xml_obj.py

This file contains the objects for representing the essential TwinCAT
datastructures found in xml (tmc) formatted file.
"""
import logging
logger = logging.getLogger(__name__)
import xml.etree.ElementTree as ET

class BaseElement:
    def __init__(self, element):
        if type(element) != ET.Element:
            raise TypeError("ElementTree.Element required")
        self.element = element

    def _get_raw_properties(self):
        return self.element.findall("./Properties/*")

    @property
    def properties(self):
        raw = self._get_raw_properties()



class Symbol(BaseElement):
    pass

class DataType(BaseElement):
    pass

