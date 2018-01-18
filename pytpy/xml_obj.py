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

    @property
    def properties(self):
        return self.element.findall("./Properties/*")

class Symbol(BaseElement):
    pass

class DataType(BaseElement):
    pass

