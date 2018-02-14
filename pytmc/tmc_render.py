'''
tmc_render.py

This file contains the tools for recursively exploring the TwinCAT program
structure, parsing relevant pragmas and rendering the resulting EPICS db file.
'''
import logging
logger = logging.getLogger(__name__)
from jinja2 import Environment, PackageLoader, select_autoescape
import re
import versioneer
import textwrap
import pkg_resources
import configparser
from . import defaults
from . import DataType
from . import TmcFile
from .xml_obj import BaseElement


class SingleRecordData:
    '''
    Data structre for packaging all the information required to render an epics
    record.

    Note
    ----
    The parameters for the constructor are for setting the attributes of this
    class. 
    
    Parameters
    ----------
    pv : str

    rec_type : str

    fields : dict

    comment : str
    
    Attributes
    ----------
    pv : str
        The full PV for the record

    rec_type : str
        Code for record type (e.g. 'ai','bo', etc.)

    fields : dict
        Specifications for each field type and their settings.

    comment : str
        An additional string to be printed above the record in the db file.
    '''
    def __init__(self, pv=None, rec_type=None, fields=None, comment=None):
        self.pv = pv 
        self.rec_type = rec_type
        self.fields = fields
        self.comment = comment

    def add(self, pv_extra):
        '''
        Append an extension term onto the current base. This allows a PV to be
        be constructed in multiple stages. This class could start with a PV of
        'GDET:FEE1' and could use .add('241') and again use .add('ENRC') to
        produce a final PV of 'GDET:FEE1:241:ENRC'.

        Parameters
        ----------
        pv_extra : str
            This is the new term to be appended to the tail end of the existing
            PV. Leading/trailing spaces and colons are scrubbed from pv_extra.
            A colon is used to adjoin the existing PV and the new addition.
        '''
        pv_extra = pv_extra.strip(" :")
        self.pv = self.pv + ":" + pv_extra

    def __eq__(self,other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            self.pv,
        )

    @property
    def check_pv(self):
        return True 

    @property
    def check_rec_type(self):
        return True

    @property
    def check_fields(self):
        return True

    @property
    def check(self):
        '''
        Collection of funcitons to evaluate whether the data in this object
        would make a safe record

        Note
        ----
        Implementation not complete.

        Returns
        -------
        bool
            True if the data is deemed safe through existing checks.  
        '''
        return check_pv and check_rec_type and check_fields


class SingleProtoData:
    def __init__(self,name,out_field,in_field,init=None):
        self.name = name
        self.out_field = out_field
        self.in_field = in_field
        self.init = init

    @property
    def has_init(self):
        if self.init != None:
            return True
        return False


class RenderAgent:
    '''
    RenderAgent provides convenient tools for rendering the final records
    file.

    Parameters
    ----------
    master_list : list
        list of :class:`~pytmc.SingleRecordData` instances specifying all
        records to be made. This parameter can be accessed later. 

    loader : tuple
        Specify package location of jinja templates. Names in the package are
        speperated by tuple entries instead of periods like normal python
        packages. Uses Jinja2's PackageLoader. 
    
    template : str
        name of the template to be used 
    
    Attributes
    ----------
    master_list : list
        list of :class:`~pytmc.SingleRecordData` instances specifying all
        records to be made.


    '''
    def __init__(self, master_list=None, loader=("pytmc","templates"),
                template=None):
        if master_list == None:
            master_list = []
        self.master_list = master_list
        self.jinja_env = Environment(
            loader = PackageLoader(*loader),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.jinja_env.get_template(template)
    
    def clean_list(self):
        for entry in self.master_list:
            if entry.pv == None:
                entry.pv = ""
            if entry.rec_type == None:
                entry.rec_type = ""
            if entry.fields ==None:
                entry.fields = []
            if entry.comment ==None:
                entry.comment = ""

    def render(self):
        '''
        Generate the rendered document

        Returns
        -------
        str
            Epics record document as a string
        '''
        return self.template.render(
            header = self.header,
            master_list = self.master_list
        )

    @property
    def header(self):
        '''
        Generate and return the message to be placed at the top of generated
        files. Includes information such as pytmc verison

        Returns
        -------
        str
            formatted header message
        '''
        message = ""
        return message


class DbRenderAgent(RenderAgent):
    '''
    DbRenderAgent provides convenient tools for rendering the final records
    file.

    Parameters
    ----------
    master_list : list
        list of :class:`~pytmc.SingleRecordData` instances specifying all
        records to be made. This parameter can be accessed later. 

    loader : tuple
        Specify package location of jinja templates. Names in the package are
        speperated by tuple entries instead of periods like normal python
        packages. Uses Jinja2's PackageLoader. 
    
    template : str
        name of the template to be used 
    
    Attributes
    ----------
    master_list : list
        list of :class:`~pytmc.SingleRecordData` instances specifying all
        records to be made.
    '''
    def __init__(self, master_list=None, loader=("pytmc","templates"),
                template="EPICS_record_template.db"):
        super().__init__(
            master_list,
            loader,
            template="EPICS_record_template.db"
        )

    def clean_list(self):
        for entry in self.master_list:
            if entry.pv == None:
                entry.pv = ""
            if entry.rec_type == None:
                entry.rec_type = ""
            if entry.fields ==None:
                entry.fields = []
            if entry.comment ==None:
                entry.comment = ""

    @property
    def header(self):
        '''
        Generate and return the message to be placed at the top of generated
        files. Includes information such as pytmc verison

        Returns
        -------
        str
            formatted header message
        '''
        message = '''\
        Epics Record file automatically generated using Pytmc

            pytmc version: {version}'''
        message = message.format(
            version=str(versioneer.get_version())
        )
        message = textwrap.dedent(message)
        message = textwrap.indent(message,"# ",lambda line: True)
        return message


class ProtoRenderAgent(RenderAgent):
    '''
    ProtoRenderAgent provides convenient tools for rendering the final proto
    file.

    Parameters
    ----------
    master_list : list
        list of :class:`~pytmc.SingleRecordData` instances specifying all
        records to be made. This parameter can be accessed later. 

    loader : tuple
        Specify package location of jinja templates. Names in the package are
        speperated by tuple entries instead of periods like normal python
        packages. Uses Jinja2's PackageLoader. 
    
    template : str
        name of the template to be used 
    
    Attributes
    ----------
    master_list : list
        list of :class:`~pytmc.SingleRecordData` instances specifying all
        records to be made.
    '''
    def __init__(self, master_list=None, loader=("pytmc","templates"),
                template="EPICS_record_template.db"):
        super().__init__(
            master_list,
            loader,
            template="EPICS_proto_template.proto"
        )

    def clean_data(self):
        pass
    
    @property
    def header(self):
        '''
        Generate and return the message to be placed at the top of generated
        files. Includes information such as pytmc verison

        Returns
        -------
        str
            formatted header message
        '''
        message = '''\
        Epics PROTO file automatically generated using Pytmc

            pytmc version: {version}'''
        message = message.format(
            version=str(versioneer.get_version())
        )
        message = textwrap.dedent(message)
        message = textwrap.indent(message,"# ",lambda line: True)
        return message
    

class TmcExplorer:
    '''
    TmcExplorer contains the tools to compile a list of SingleRecordData
    instances from the :class:`~pytmc.TmcFile`.

    Parameters
    ----------
    tmc : :class:`~pytmc.xml_collector.TmcFile`

    Attributes
    ----------
    tmc.all_records : list of :class:`~SingleRecordData`
        This is a list of all records to be made for the DB file. Populated by
        running :func:`~exp_Symbols`.
    
    '''

    def __init__(self, tmc):
        self.tmc = tmc
        self.tmc.isolate_all()
        self.all_records = []
        self.all_protos = []

    def exp_DataType(self, dtype_inst, base=""):
        # this is the datatype name of the targeted datatype instance
        dtype_type_str = dtype_inst.tc_type

        # If this datatype is user-defined (also a Symbol or SubItem)
        if dtype_type_str in self.tmc.all_DataTypes:
            # locate parent if it exists
            dtype_parent = self.tmc.all_DataTypes[dtype_type_str].tc_extends 
            if dtype_parent != None:
                # recurse, explore the parent datatype
                self.exp_DataType(
                    self.tmc.all_DataTypes[dtype_parent],
                    base + dtype_inst.pv,
                )
                
            dt = False
        # If dtype_inst is pointing to a DataType, not Symbol or SubItem 
        else:    
            dt = True
            dtype_type_str = dtype_inst.name 

        # Regardles of dtype_inst's typedtype_type_str is now a DataType's name
        subitem_set = self.tmc.all_SubItems[dtype_type_str].registered

        # Loop through SubItems in that DataType
        for entry in subitem_set:
            if subitem_set[entry].tc_type in self.tmc.all_DataTypes: 
                # recurse, explore SubItems of non-primitave type as necessary
                self.exp_DataType(
                    subitem_set[entry],
                    base + dtype_inst.pv + ":"
                )
                continue
             
            # Given that the variable is a primitive, create record(s)
            recs = self.make_record(
                subitem_set[entry],
                prefix = base + ("" if dt else dtype_inst.pv)
            )
            # Save the record(s)
            for rec in recs: 
                self.all_records.append(rec)
                logger.debug("create {}".format(str(rec)))    

    def exp_Symbols(self, pragmas_only=True,skip_datatype=False):
        if pragmas_only:
            symbol_set = self.tmc.all_Symbols.registered
        else:
            symbol_set = self.tmc.all_Symbols
        
        # loop through all symbols in the set of allowed symbols
        for sym in symbol_set:
            # if the symbol has a user-created type
            if symbol_set[sym].tc_type in self.tmc.all_DataTypes:
                if not skip_datatype:
                    # explore the datatype/datatype instance 
                    self.exp_DataType(
                        symbol_set[sym], 
                    )
                continue
            
            # if the datatype is not user-created, create/save a record 
            recs = self.make_record(symbol_set[sym])
            for rec in recs:
                self.all_records.append(rec)
                logger.debug("create {}".format(str(rec))) 

    def create_intf(self, target, prefix=None):
        if prefix != None:
            prefix = prefix + ":"
        else:
            prefix = ""

        if target.pv == None:
            logger.warn("Record for {} lacks a PV".format(str(target)))
        
        fields = target.fields
        
        record = SingleRecordData(
            pv = prefix + target.pv,
            rec_type = target.rec_type,
            fields = fields,
        )
        return record

    def make_record(self, target, prefix=None):
        if prefix != None:
            prefix = prefix + ":"
        else:
            prefix = ""

        if target.pv == None:
            logger.warn("Record for {} lacks a PV".format(str(target)))
        
        config = target.config_by_pv
        
        record_list = []

        for pv_group in config:
            record_list.append(SingleRecordData(
                pv = prefix + BaseElement.parse_pragma('pv',pv_group),
                rec_type = BaseElement.parse_pragma('type',pv_group),
                fields = BaseElement.parse_pragma('field',pv_group),
            ))
    
        return record_list

    def generate_ads_line(self, target, direction):
        raise NotImplementedError


class FullRender:
    def __init__(self,tmc_path):
        self.tmc = TmcFile(tmc_path)
        self.exp = TmcExplorer(self.tmc)
        self.exp.exp_Symbols()
        db_render = DbRenderAgent(self.exp.all_records)
        db_render.clean_list()
        self.dboutput = db_render.render()
        proto_render = ProtoRenderAgent(self.exp.all_protos)
        proto_render.clean_list()
        self.proto_output = proto_render.render()

    def save(self,outpath):
        db_f = open(outpath+".db","w")
        db_f.write(self.dboutput)
        db_f.close()
        proto_f = open(outpath+".db","w")
        proto_f.write(self.proto_output)
        proto_f.close()

