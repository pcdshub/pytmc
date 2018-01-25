"""
xml_collector.py

This file contains the objects for intaking TMC files and generating python
interpretations. Db Files can be produced from the interpretation
"""
import logging
logger = logging.getLogger(__name__)
import xml.etree.ElementTree as ET
from collections import defaultdict
from pytmc import Symbol, DataType, SubItem



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
            lambda x: self[x].has_pragma,
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
        self.isolate_Symbols()
        self.isolate_DataTypes()

