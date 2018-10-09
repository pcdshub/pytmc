import pytest
import logging

import xml.etree.ElementTree as ET

#from pytmc.xml_obj import Symbol, DataType
from pytmc import Symbol, DataType, SubItem
from pytmc.xml_obj import BaseElement

from pytmc import TmcFile
from pytmc.xml_collector import ElementCollector
from pytmc import (DbRenderAgent, SingleRecordData, TmcExplorer, FullRender,
        SingleProtoData, ProtoRenderAgent)

from collections import defaultdict

logger = logging.getLogger(__name__)

def test_DbRenderAgent_instantiation():
    try:
        agent = DbRenderAgent()
    except:
        pytest.fail("Instantiation with no arguments has erred")
    
    try:
        agent = DbRenderAgent(master_list = ['a','b'])
    except:
        pytest.fail("Instantiation with arguments has erred")


def test_SingleRecordData_instantiation():
    try:
        rec = SingleRecordData()
    except:
        pytest.fail("Instantiation with no arguments has erred")
    
    try:
        rec = SingleRecordData(
            pv = "GDET:FEE1:241:ENRC",
            rec_type = "ai",
            fields = [
                ("DTYP","asynInt32"),
                ("INP",None),
                ("ZNAM",""),
            ]
        )
    except:
        pytest.fail("Instantiation with arguments has erred")


def test_SingleRecordData_render(safe_record_factory,capsys):
    out,err = capsys.readouterr()
    rec1 = safe_record_factory
    rec2 = safe_record_factory
    agent = DbRenderAgent([rec1,rec2]) 

def test_SingleRecordData_pv_append():
    rec = SingleRecordData(
        pv = "GDET:FEE1:241:ENRC"
    )
    rec.add("ABC:DEF")
    assert rec.pv == "GDET:FEE1:241:ENRC:ABC:DEF"


def test_SingleRecordData_eq():
    a = SingleRecordData(
        pv = 'a',
        fields = {'c':'c'},
        rec_type = 'b'
    )
    b = SingleRecordData(
        pv = 'a',
        fields = {'c':'c'},
        rec_type = 'b'
    )
    c = SingleRecordData(
        pv = 'a',
        fields = {'c':'c'},
        rec_type = 'n'
    )
    assert a == b
    assert a != c


@pytest.mark.skip(reason="checking features to be developed soon")
def test_SingleRecordData_check_pv(safe_record_factory):
    rec = safe_record_factory
    pv += ":"
    assert rec.check_pv == False
    
    rec = safe_record_factory
    pv += "::ABC"
    assert rec.check_pv == False
    
    rec = safe_record_factory
    pv += "%ABC"
    assert rec.check_pv == False
    
    rec = safe_record_factory
    pv += " ABC"
    assert rec.check_pv == False


@pytest.mark.skip(reason="checking features to be developed soon")
def test_SingleRecordData_check_rec_type(safe_record_factory):
    assert False


@pytest.mark.skip(reason="checking features to be developed soon")
def test_SingleRecordData_check_fields(safe_record_factory):
    assert False


def test_TmcExplorer_instantiation(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    try:
        exp = TmcExplorer(tmc)
    except:
        pytest.fail("Instantiation of TmcExplorer should not generate errors")


@pytest.mark.skip(reason="Pending deprecation")
def test_TmcExplorer_create_intf(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc,'file.proto')

    # Create intf for singular variable in MAIN scope
    
    path = [tmc.all_Symbols['MAIN.ulimit']] 
    exp.create_intf(path)
    pv_packs = PvPackage.from_element_path(
        target_path = path,
        base_proto_name = 'MAINulimit',
        proto_file_name = 'file.proto',
    )
    
    for pack in pv_packs:
        #logging.debug(str(pack.__dict__))
        #logging.debug(str(exp.all_pvpacks[0].__dict__))
        assert pack in exp.all_pvpacks

    # create intf for variable in encapsulated scope
    path = [
        tmc.all_Symbols['MAIN.struct_base'],
        tmc.all_SubItems['DUT_STRUCT']['struct_var']
    ]
    exp.create_intf(path)
    pv_packs = PvPackage.from_element_path(
        target_path = path,
        base_proto_name = 'MAINstruct_basestruct_var',
        proto_file_name = 'file.proto',
    )
    
    for pack in pv_packs:
        #logging.debug(str(pack.__dict__))
        #logging.debug(str(exp.all_pvpacks[1].__dict__))
        assert pack in exp.all_pvpacks


    # create intf for user-defined data structure instance 
    path = [tmc.all_Symbols['MAIN.NEW_VAR']]
    exp.create_intf(path)
    pv_packs = PvPackage.from_element_path(
        target_path = path,
        base_proto_name = 'MAINNEW_VAR',
        proto_file_name = 'file.proto',
    )
    #logging.debug(str(exp.all_pvpacks[2].__dict__))
    #logging.debug(str(exp.all_pvpacks[3].__dict__))
    for pack in pv_packs:
        #logging.debug(str(pack.__dict__))
        assert pack in exp.all_pvpacks

    # create intf for basic array
    path = [tmc.all_Symbols['MAIN.dtype_samples_int_array']]
    exp.create_intf(path)
    pv_packs = PvPackage.from_element_path(
        target_path = path,
        base_proto_name = 'MAINdtype_samples_int_array',
        proto_file_name = 'file.proto',
    )
    for pack in pv_packs:
        assert pack in exp.all_pvpacks
    
    # create intf for array of user-defined types
    path = [tmc.all_Symbols['MAIN.dtype_samples_iter_array']]
    exp.create_intf(path)
    pv_packs, rejects = PvPackage.from_element_path(
        target_path = path,
        base_proto_name = 'MAINdtype_samples_iter_array',
        proto_file_name = 'file.proto',
        return_rejects = True,
    )
    for pack in pv_packs:
        assert pack not in exp.all_pvpacks
    logging.debug(str(rejects))


@pytest.mark.skip(reason="Pending deprecation")
def test_SingleRecordData_from_element(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    records = SingleRecordData.from_element(tmc.all_Symbols['MAIN.ulimit'])
    record = records[0]
    assert type(record) == SingleRecordData
    assert record.pv == 'TEST:MAIN:ULIMIT'
    assert record.rec_type == 'ai'
    assert record.fields == [
        {'f_name':'INP','f_set':'@ () $(PORT)'},
        {'f_name':'DTYP','f_set':'asynFloat64'},
        {'f_name':'EGU','f_set':'mm'},
    ]

    records = SingleRecordData.from_element(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        prefix = tmc.all_Symbols['MAIN.struct_base'].pv,
        proto_file = 'file.proto',
        names = ['SetVar']
    )
    record = records[0]
    assert type(record) == SingleRecordData
    assert record.pv == 'TEST:MAIN:STRUCTBASE:STRUCT_VAR'
    assert record.rec_type == 'ao'
    assert record.fields == [
        {'f_name':'OUT','f_set':'@file.proto SetVar() $(PORT)'},
        {'f_name':'DTYP','f_set':'asynFloat64'},
        {'f_name':'EGU','f_set':'mm'},
    ] 
    
    record_o, record_i = SingleRecordData.from_element(
        tmc.all_Symbols['MAIN.NEW_VAR'],
        proto_file = 'file.proto',
        names = ['SetVar','GetVar']
    )
    assert type(record) == SingleRecordData
    assert record_o.pv == 'TEST:MAIN:NEW_VAR_OUT'
    assert record_o.rec_type == 'bo'
    assert record_o.fields == [
        {'f_name':'OUT','f_set':'@file.proto SetVar() $(PORT)'},
        {'f_name':'ZNAM','f_set':'SINGLE'},
        {'f_name':'ONAM','f_set':'MULTI'},
        {'f_name':'SCAN','f_set':'1 second'},
    ] 
    assert record_i.pv == 'TEST:MAIN:NEW_VAR_IN'
    assert record_i.rec_type == 'bi'
    assert record_i.fields == [
        {'f_name':'INP','f_set':'@file.proto GetVar() $(PORT)'},
        {'f_name':'ZNAM','f_set':'SINGLE'},
        {'f_name':'ONAM','f_set':'MULTI'},
        {'f_name':'SCAN','f_set':'1 second'},
    ] 
   

@pytest.mark.skip(reason="Pending deprecation")
def test_TmcExplorer_exp_DataType(generic_tmc_path):
    '''Explore single level Datatype (Datatype doesn't contain others)
    '''
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc,'file.proto')
    exp.exp_DataType(
        tmc.all_Symbols['MAIN.struct_base'],
        path = [tmc.all_Symbols['MAIN.struct_base']],
    )
    records = SingleRecordData.from_element(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        proto_file= 'file.proto',
        prefix = "TEST:MAIN:STRUCTBASE",
        names = ['SetMAINstruct_basestruct_var']
    )
    assert records[0] in exp.all_records

    records = SingleRecordData.from_element(
        tmc.all_SubItems['DUT_STRUCT']['struct_var2'],
        proto_file= 'file.proto',
        prefix = "TEST:MAIN:STRUCTBASE",
        names = ['GetMAINstruct_basestruct_var2']
    )
    assert records[0] in exp.all_records
    assert len(exp.all_records) == 2


@pytest.mark.skip(reason="Pending deprecation")
def test_TmcExplorer_exp_DataType_recursive(generic_tmc_path):
    '''Explore multi level Datatype (Datatype contains others)
    '''
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc,'file.proto')
    exp.exp_DataType(
        tmc.all_Symbols['MAIN.test_iterator'],
        path = [tmc.all_Symbols['MAIN.test_iterator']],
    )
    records = SingleRecordData.from_element(
        tmc.all_SubItems['iterator']['value'],
        proto_file= 'file.proto',
        prefix = "TEST:MAIN:ITERATOR",
        names = ['SetMAINtest_iteratorvalue']
    )
    assert records[0] in exp.all_records

    records = SingleRecordData.from_element(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        proto_file= 'file.proto',
        prefix = "TEST:MAIN:ITERATOR:EXT1",
        names = ['SetMAINtest_iteratorextra1struct_var']
    )
    
    assert records[0] in exp.all_records
    assert len(exp.all_records) == 7


@pytest.mark.skip(reason="Pending deprecation")
def test_TmcExplorer_exp_Symbols(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc,'file.proto')
    exp.exp_Symbols(pragmas_only=True,skip_datatype=True)

    records = SingleRecordData.from_element(
        tmc.all_Symbols['MAIN.ulimit'],
        proto_file = 'file.proto',
        names=['GetMAINulimit']
    )
    assert records[0] in exp.all_records
    records = SingleRecordData.from_element(
        tmc.all_Symbols['MAIN.multi'],
        proto_file = 'file.proto',
        names=['GetMAINmulti']
    )
    assert records[0]in exp.all_records

    record_o, record_i = SingleRecordData.from_element(
        tmc.all_Symbols['MAIN.NEW_VAR'],
        proto_file = 'file.proto',
        names=['SetMAINNEW_VAR','GetMAINNEW_VAR']
    )
    assert record_o in exp.all_records
    assert record_i in exp.all_records 
    
    records = SingleRecordData.from_element(
        tmc.all_Symbols['sample_gvl.test_global'],
        proto_file = 'file.proto',
        names=['Setsample_gvltest_global']
    )    
    assert records[0]in exp.all_records
    
    assert len(exp.all_records) == 5


@pytest.mark.skip(reason="Pending deprecation")
def test_TmcExplorer_exp_Symbols_all(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc,'file.proto')
    exp.exp_Symbols(pragmas_only=True)
    
    records = SingleRecordData.from_element(
        tmc.all_Symbols['MAIN.ulimit'],
        proto_file = 'file.proto',
        names=['GetMAINulimit']
    )
    assert records[0] in exp.all_records
    records = SingleRecordData.from_element(
        tmc.all_Symbols['MAIN.multi'],
        proto_file = 'file.proto',
        names=['GetMAINmulti']
    )
    assert records[0]in exp.all_records

    record_o, record_i = SingleRecordData.from_element(
        tmc.all_Symbols['MAIN.NEW_VAR'],
        proto_file = 'file.proto',
        names=['SetMAINNEW_VAR','GetMAINNEW_VAR']
    )
    assert record_o in exp.all_records
    assert record_i in exp.all_records 
    
    records = SingleRecordData.from_element(
        tmc.all_Symbols['sample_gvl.test_global'],
        proto_file = 'file.proto',
        names=['Setsample_gvltest_global']
    )    
    assert records[0]in exp.all_records 
    
    assert len(exp.all_records) == 26


def test_TmcExplorer_read_ini(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)


@pytest.mark.skip(reason="Pending deprecation")
def test_FullRender_instantiation(generic_tmc_path):
    fr = FullRender(generic_tmc_path,'TEST')


def test_SingleProtoData_instantiation():
    spd = SingleProtoData(
        "Test Function",
        "OK",
        "MAIN.test_float=%f",
    )
    assert spd.has_init == False


def test_ProtoRenderAgent_instantiation(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    try:
        agent = ProtoRenderAgent()
    except:
        pytest.fail("Instantiation has thrown errors")
    
    try:
        agent = ProtoRenderAgent()
    except:
        pytest.fail("Instantiation has thrown errors")


def test_SingleProtoDataRender():
    a = SingleProtoData(
        "getFTest",
        "Main.fTest?",
        "%d"
    )
    b = SingleProtoData(
        "setfTest",
        "Main.fTest=%d",
        "OK",
        "getFTest",
    )
    agent = ProtoRenderAgent([a,b])


def test_SingleProtoData_has_init(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    proto = SingleProtoData(
        name = "GetMainulimit",
        out_field = 'MAIN.ulimit?',
        in_field = '%d',
    )
    assert type(proto) == SingleProtoData
    assert proto.name == "GetMainulimit"
    assert proto.out_field == 'MAIN.ulimit?'
    assert proto.in_field == '%d'
    assert proto.has_init == False 
    

@pytest.mark.skip(reason="Pending deprecation")
def test_SingleProtoData_from_element_path(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)


    protos = SingleProtoData.from_element_path(
        [tmc.all_Symbols['MAIN.ulimit']],
        'fake_name'
    )
    assert len(protos) == 1

    proto = protos[0]
    assert type(proto) == SingleProtoData
    assert proto.name == 'Getfake_name'
    assert proto.out_field == 'MAIN.ulimit?'
    assert proto.in_field == '%d'
    assert proto.has_init == False 
   
    # Test variable with input and output 
    proto_out, proto_in = SingleProtoData.from_element_path(
        [
            tmc.all_Symbols['MAIN.NEW_VAR'],
        ],
        'fake_name',
    )
    
    assert type(proto_out) == SingleProtoData
    assert proto_out.name == 'Setfake_name'
    assert proto_out.out_field == 'MAIN.NEW_VAR=%d'
    assert proto_out.in_field == 'OK'
    assert proto_out.init == 'Getfake_name'

    assert type(proto_in) == SingleProtoData
    assert proto_in.name == 'Getfake_name'
    assert proto_in.out_field == 'MAIN.NEW_VAR?'
    assert proto_in.in_field == '%d'
    assert proto_in.has_init == False 

    # Test encapsulated variable
    protos  = SingleProtoData.from_element_path(
        [
            tmc.all_Symbols['MAIN.struct_base'],
            tmc.all_SubItems['DUT_STRUCT']['struct_var']
        ],
        name = 'fake_name'
    )
    assert len(protos) == 1

    proto = protos[0]
    assert type(proto) == SingleProtoData
    assert proto.name == 'Setfake_name'
    assert proto.out_field == 'MAIN.struct_base.struct_var=%d'
    assert proto.in_field == 'OK'
    assert proto.has_init == False 
