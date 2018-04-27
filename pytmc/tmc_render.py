'''
tmc_render.py

This file contains the tools for recursively exploring the TwinCAT program
structure, parsing relevant pragmas and rendering the resulting EPICS db file.
'''
import logging
logger = logging.getLogger(__name__)
from jinja2 import Environment, PackageLoader, select_autoescape
import re
import textwrap
import pkg_resources
import configparser
from . import defaults
from . import DataType
from . import TmcFile
from .xml_obj import BaseElement
from . import Symbol, DataType, SubItem
from . import PvPackage
import pytmc


class SingleRecordData:
    '''
    Data structre for packaging all the information required to render an epics
    record.

    SingleRecordData supports equality testing. Two instances are equal if all
    their attributes are equal.
    
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

    @property
    def has_comment(self):
        '''
        This property allows jinja to evaluate whether or not to draw a
        comments region. 

        Returns
        -------
        bool
            True if this record has a non-None comment.
        '''
        if self.comment != None:
            return True
        return False

    @classmethod
    def from_element(cls, target, prefix=None, proto_file=None, names=None): 
        '''
        Create an instance of :class:`~SingleRecordData` from a given element
        target.

        Parameters
        ----------
        target : :class:`~BaseElement` or child thereof
            This is the target element for which record(s) will be created

        prefix : str or None
            The section of the PV name to be appended to the front of the PV of
            the target element

        proto_file : str or None
            The full name of the proto file where the prototypes used by the
            record are held.

        names : list or None
            This is the list of prototype methods to be matched with the record
            created from the target element. This list must be the same size
            as the number of records to be created or be None. Note that .

        Returns
        -------
        list
            This is list of record instances generated. There is one instance
            per PV specified for the target variable

        '''
        # if a colon as not been appended to the end o the PV prefix, add one
        if prefix != None:
            if prefix[-1] != ':':
                prefix += ":"
        else:
            prefix = ""
        
        if target.pv == None:
            logger.warn("Record for {} lacks a PV".format(str(target)))
        
        config = target.config_by_pv()
        
        record_list = []

        if names == None:
            names = [''] * len(config)

        if proto_file == None:
            proto_file = ""

        for pv_group, name in zip(config,names):
            fields = BaseElement.parse_pragma('field',pv_group)
            if type(fields) != list:
                fields = [fields]
            record_list.append(cls(
                pv = prefix + BaseElement.parse_pragma('pv',pv_group),
                rec_type = BaseElement.parse_pragma('type',pv_group),
                fields = fields,
            ))
            record = record_list[-1]
            record.guess_ADS_line(pv_group, proto_file, name)

        return record_list

    def guess_ADS_line(self, pv_group,proto_file,name):
        '''
        For a given set of pragmas concerning a single PV, construct the ADS
        reference.

        pv_group : list
            This list of dictionaries gives the 
        '''
        if 'i' in BaseElement.parse_pragma('io',pv_group):
            f_name = "INP"
        elif 'o' in BaseElement.parse_pragma('io',pv_group):
            f_name = "OUT"
        
        f_set = "@" + proto_file + " " + name + "() $(PORT)"
        
        self.fields.insert(0,{'f_name':f_name,'f_set':f_set})


class SingleProtoData:
    '''
    Data structre for packaging all the information required to render an epics
    proto entry.

    SingleProtoData supports equality testing. Two instances are equal if all
    their attributes are equal.
    
    Note
    ----
    The parameters for the constructor are for setting the attributes of this
    class. 
    
    Parameters
    ----------
    name : str

    out_field : str
    
    in_field : str
    
    init : str

    Attributes
    ----------
    name : str
        This specifies the name of the proto 'method'. This is the name used to
        refer to the proto in the .db file. Name collision is prevented in
        :func:`~TmcExplorer.make_intf` by manually assigning a name for the
        :func:`~from_element_path`.

    out_field : str
        This is the content to be placed after the 'out' field in the proto
        file.
    
    in_field : str
        This is the content to be placed after the 'in' field in the proto
        file.
    
    init : str
        If this field is meant to be initialized with another value, place the
        name of the proto here. 
    
    '''
    def __init__(self,name=None,out_field=None,in_field=None,init=None):
        self.name = name
        self.out_field = out_field
        self.in_field = in_field
        self.init = init
    
    def __repr__(self):
        return "{}({})".format(
            self.__class__.__name__,
            self.name,
        )

    @property
    def has_init(self):
        '''
        Returns
        -------
        bool
            True if this proto has a non-None init.
        '''
        if self.init != None:
            return True
        return False

    def __eq__(self,other):
        return self.__dict__ == other.__dict__
    
    @classmethod
    def from_element_path(cls, path, name=None):
        '''
        Create an instance of :class:`~SingleProtoData` from a given element
        path.

        Parameters
        ----------
        path : list of :class:`~BaseElement` instances or children thereof
            This is a list of elements leading to the target element for which
            protos will be created

        name : str
            The base name for the proto. 

        Returns
        -------
        list
            This is list of proto instances generated. There is one instance
            per PV given.
        '''
        if name == None:
            name = ''
        
        inst_collection = []
        adspath = ""
        for entry in path:
            adspath = adspath + entry.name + '.'
        adspath = adspath[:-1]

        for config_set in path[-1].config_by_pv():
            inst = cls()

            io_line = BaseElement.parse_pragma('io',config_set)
            if "o" in io_line:
                inst.name = "Set" + name
                inst.out_field = adspath + "=" + \
                    BaseElement.parse_pragma('str',config_set)
                inst.in_field = "OK"
                if BaseElement.parse_pragma('init',config_set) == 'True':
                    inst.init = "Get" + name
            elif "i" in io_line:
                inst.name = "Get" + name
                inst.out_field = adspath + "?"
                inst.in_field = BaseElement.parse_pragma('str',config_set)
           
            inst_collection.append(inst)
        return inst_collection


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
        list of : instances specifying all records or protos to be made.

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
            #if entry.comment ==None:
                #entry.comment = ""

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
            version=str(pytmc.__version__)
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

    def clean_list(self):
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
            version=str(pytmc.__version__)
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

    def __init__(self, tmc, proto_file=None):
        self.tmc = tmc
        self.proto_file = proto_file
        self.tmc.isolate_all()
        self.all_records = []
        self.all_protos = []
        self.proto_name_list = []
        self.all_pvpacks = []

    def exp_DataType(self, dtype_inst, base="",path=[]):
        '''
        Method for recusively exploring variables of user-defined type and
        creating the corresponding :class:`~SingleProtoData` and
        :class:`~SingleRecordData` instances.  


        Parameters
        ----------

        dtype_inst : :class:Symbol`~`, :class:`~SubItem`, or :class:`~DataType`
            This is the target element to explore. This method is typically
            passed either a Symbol or Subitem when exploring the main program
            or user defined DataTypes. A DataType will be passed in when this
            method explores a parent DataType

        base : str
            This string builds the full PV string. At each level, the string is
            appended PV subsections. Consider deprecating as the path argument
            may take over this functionality.

        path : list
            This list of Elements is the chain of items traversed to reach the
            current element. The lowest index is the first level instance
            likely appearing in Main or a global variable and each successive
            entry in the list is the encapsulated element instance. The
            sequence ends with the current element instance. 

        '''
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
                    path
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
            # immediately go to create_intf if symbol is an array 
            if subitem_set[entry].is_array:
                self.create_intf(path+[subitem_set[entry]])
                continue
            elif subitem_set[entry].tc_type in self.tmc.all_DataTypes: 
                # recurse, explore SubItems of non-primitave type as necessary
                self.exp_DataType(
                    subitem_set[entry],
                    base + dtype_inst.pv + ":",
                    path = path + [subitem_set[entry]]
                )
                continue
             
            # Given that the variable is a primitive, create record(s)
            self.create_intf(path+[subitem_set[entry]])

    def exp_Symbols(self, pragmas_only=True,skip_datatype=False):
        '''
        Master method for exploring the entirety of the tmc file and creating
        the corresponding :class:`~SingleProtoData` and
        :class:`~SingleRecordData` instances. To achieve this, run without
        parameters

        Parameters
        ----------
        
        pragmas_only : bool
            If true, only explore symbols that are marked by pragmas. Defaults
            to True. Consider deprecating this in the near future. 

        skip_datatype : bool
            If true, skip over variables with user defined data types and only
            explore top level variables (symbols). Defaults to False.
        '''
        if pragmas_only:
            symbol_set = self.tmc.all_Symbols.registered
        else:
            symbol_set = self.tmc.all_Symbols
        
        # loop through all symbols in the set of allowed symbols
        for sym in symbol_set:
            # immediately go to create_intf if symbol is an array 
            if symbol_set[sym].is_array:
                self.create_intf([symbol_set[sym]])
            
            # if the symbol has a user-created type
            elif symbol_set[sym].tc_type in self.tmc.all_DataTypes:
                if skip_datatype:
                    continue

                # explore the datatype/datatype instance 
                self.exp_DataType(
                    symbol_set[sym], 
                    path = [symbol_set[sym]]
                )
            
            # if the datatype is not user-created, create/save a record 
            else:
                self.create_intf([symbol_set[sym]])

    def create_intf(self, target_path, prefix=None):
        '''
        Create and save the all the necessary :class:`~SingleProtoData` and
        :class:`~SingleRecordData` instances for a target variable.

        Parameters
        ----------

        target_path : list 
            This list of Elements is the chain of items traversed to reach the
            current element. The lowest index is the first level instance
            likely appearing in Main or a global variable and each successive
            entry in the list is the encapsulated element instance. The
            sequence ends with the current element instance. The target_path is
            used for constructing the PV prefix.
        
        prefix : str
            If a prefix is ofered use this as the base of constructed PV.
        '''
        
        # construct pvname
        base_proto_name = ""
        for entry in target_path:
            base_proto_name += entry.name

        base_proto_name = re.sub("\.","",base_proto_name)

        hypothesis_name = base_proto_name
        index = 0

        # reject and modify names if they are already being used
        while hypothesis_name in self.proto_name_list:
            hypothesis_name = base_proto_name + str(index)
            index +=1
        self.proto_name_list.append(hypothesis_name)

        # generate and save the new pvpackages 
        pv_pack_out = PvPackage.from_element_path(
            target_path = target_path,
            base_proto_name = hypothesis_name,
            proto_file_name = self.proto_file,
        )
        
        for pack in pv_pack_out:
            self.all_pvpacks.append(pack)


class FullRender:
    def __init__(self,tmc_path,outpath):
        self.db_f_path = outpath+".db"
        self.proto_f_path = outpath+".proto"
        self.tmc = TmcFile(tmc_path)
        self.exp = TmcExplorer(self.tmc,self.proto_f_path)
        self.exp.exp_Symbols()
        
        db_render = DbRenderAgent(self.exp.all_records)
        db_render.clean_list()
        self.db_output = db_render.render()
        
        proto_render = ProtoRenderAgent(self.exp.all_protos)
        proto_render.clean_list()
        self.proto_output = proto_render.render()

    def save(self):
        db_f = open(self.db_f_path,"w")
        db_f.write(self.db_output)
        db_f.close()
        proto_f = open(self.proto_f_path,"w")
        proto_f.write(self.proto_output)
        proto_f.close()

