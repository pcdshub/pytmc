"""
xml_collector.py

This file contains the objects for intaking TMC files and generating python
interpretations. Db Files can be produced from the interpretation
"""
import logging
logger = logging.getLogger(__name__)
import xml.etree.ElementTree as ET
from collections import defaultdict
from pytpy import Symbol, DataType, SubItem



class ElementCollector(dict):
    def add(self, value):
        name = value.name
        dict.__setitem__(self,name,value)

    @property
    def registered(self):
        names = list(filter(
            lambda x: self[x].has_pragma,
            self,

        ))
        return {name:self[name] for name in names}



class TmcFile:
    def __init__(self, filename):
        self.filename = filename
        self.tree = ET.parse(self.filename)
        self.root = self.tree.getroot()

        self.all_Symbols = ElementCollector()
        self.all_DataTypes = ElementCollector()
        self.all_SubItems = ElementCollector() 

    def isolate_Symbols(self):
        data_area = self.root.find(
            "./Modules/Module/DataAreas/DataArea/[Name='PlcTask Internal']"
        )
        xml_symbols = data_area.findall('./Symbol')
        for xml_symbol in xml_symbols:
            sym = Symbol(xml_symbol)
            self.all_Symbols.add(sym)

    def isolate_DataTypes(self,process_subitems=True):
        xml_data_types = self.root.findall(
            "./DataTypes/DataType"
        )
        for xml_data_type in xml_data_types:
            data = DataType(xml_data_type)
            if process_subitems:
                self.isolate_SubItems(data)
            self.all_DataTypes.add(data)

    def isolate_SubItems(self,parent=None):
        if type(parent) == DataType:
            xml_subitems = parent.element.findall('./SubItem')
            for xml_subitem in xml_subitems:
                s_item = SubItem(xml_subitem,parent=parent)
                self.all_SubItems.add(s_item)


        if type(parent) == ET.Element:
            pass

