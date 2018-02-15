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
    print()
    print(agent.render())
    

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
   

def test_TmcExplorer_create_intf(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    exp.create_intf([tmc.all_Symbols['MAIN.ulimit']])
    records = exp.make_record(tmc.all_Symbols['MAIN.ulimit'])
    assert records[0] in exp.all_records

    exp.create_intf(
        [
            tmc.all_Symbols['MAIN.struct_base'],
            tmc.all_SubItems['DUT_STRUCT']['struct_var']
        ],
        prefix = "TEST:MAIN:STRUCTBASE" 
    )
    records = exp.make_record(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        prefix = tmc.all_Symbols['MAIN.struct_base'].pv
    )
    print(exp.all_records[1])
    print(records[0])
    assert records[0] in exp.all_records

    exp.create_intf([tmc.all_Symbols['MAIN.NEW_VAR']])
    record_o, record_i = exp.make_record(tmc.all_Symbols['MAIN.NEW_VAR'])
    assert record_o in exp.all_records
    assert record_i in exp.all_records


def test_TmcExplorer_make_record(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    records = exp.make_record(tmc.all_Symbols['MAIN.ulimit'])
    record = records[0]
    assert type(record) == SingleRecordData
    assert record.pv == 'TEST:MAIN:ULIMIT'
    assert record.rec_type == 'ai'
    assert record.fields == [
        {'f_name':'DTYP','f_set':'asynFloat64'},
        {'f_name':'EGU','f_set':'mm'},
    ]

    records = exp.make_record(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        prefix = tmc.all_Symbols['MAIN.struct_base'].pv
    )
    record = records[0]
    assert type(record) == SingleRecordData
    assert record.pv == 'TEST:MAIN:STRUCTBASE:STRUCT_VAR'
    assert record.rec_type == 'ao'
    assert record.fields == [
        {'f_name':'DTYP','f_set':'asynFloat64'},
        {'f_name':'EGU','f_set':'mm'},
    ] 
    
    record_o, record_i = exp.make_record(tmc.all_Symbols['MAIN.NEW_VAR'])
    assert type(record) == SingleRecordData
    assert record_o.pv == 'TEST:MAIN:NEW_VAR_OUT'
    assert record_o.rec_type == 'bo'
    assert record_o.fields == [
        {'f_name':'ZNAM','f_set':'SINGLE'},
        {'f_name':'ONAM','f_set':'MULTI'},
        {'f_name':'SCAN','f_set':'1 second'},
    ] 
    assert record_i.pv == 'TEST:MAIN:NEW_VAR_IN'
    assert record_i.rec_type == 'bi'
    assert record_i.fields == [
        {'f_name':'ZNAM','f_set':'SINGLE'},
        {'f_name':'ONAM','f_set':'MULTI'},
        {'f_name':'SCAN','f_set':'1 second'},
    ] 
    
    
def test_TmcExplorer_exp_DataType(generic_tmc_path):
    '''Explore single level Datatype (Datatype doesn't contain others)
    '''
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    exp.exp_DataType(
        tmc.all_Symbols['MAIN.struct_base'],
        path = [tmc.all_Symbols['MAIN.struct_base']],
    )
    struct_var = exp.make_record(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        prefix = "TEST:MAIN:STRUCTBASE"
    )[0]
    assert struct_var in exp.all_records
    struct_var2 = exp.make_record(
        tmc.all_SubItems['DUT_STRUCT']['struct_var2'],
        prefix = "TEST:MAIN:STRUCTBASE"
    )[0]
    assert struct_var2 in exp.all_records
    assert len(exp.all_records) == 2


def test_TmcExplorer_exp_DataType_recursive(generic_tmc_path):
    '''Explore multi level Datatype (Datatype contains others)
    '''
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    exp.exp_DataType(
        tmc.all_Symbols['MAIN.test_iterator'],
        path = [tmc.all_Symbols['MAIN.test_iterator']],
    )
    struct_var = exp.make_record(
        tmc.all_SubItems['iterator']['value'],
        prefix = "TEST:MAIN:ITERATOR"
    )[0]
    assert struct_var in exp.all_records
    struct_var2 = exp.make_record(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        prefix = "TEST:MAIN:ITERATOR:EXT1"
    )[0]
    for x in exp.all_records:
        print(x)
    assert struct_var2 in exp.all_records
    assert len(exp.all_records) == 7


def test_TmcExplorer_exp_Symbols(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    exp.exp_Symbols(pragmas_only=True,skip_datatype=True)
    assert exp.make_record(tmc.all_Symbols['MAIN.ulimit'])[0] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['MAIN.multi'])[0] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['MAIN.NEW_VAR'])[0] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['MAIN.NEW_VAR'])[1] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['sample_gvl.test_global'])[0] \
            in exp.all_records
    assert len(exp.all_records) == 5


def test_TmcExplorer_exp_Symbols_all(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    exp.exp_Symbols(pragmas_only=True)
    assert exp.make_record(tmc.all_Symbols['MAIN.ulimit'])[0] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['MAIN.multi'])[0] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['MAIN.NEW_VAR'])[0] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['MAIN.NEW_VAR'])[1] \
        in exp.all_records
    assert exp.make_record(tmc.all_Symbols['sample_gvl.test_global'])[0] \
            in exp.all_records
    assert len(exp.all_records) == 24


@pytest.mark.skip(reason="Not yet implemented")
def test_TmcExplorer_generate_ads_line(generic_tmc_path):
    pytest.fail("WIP")


def test_TmcExplorer_read_ini(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)


def test_FullRender_instantiation(generic_tmc_path):
    fr = FullRender(generic_tmc_path)

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
    print(agent.render())


@pytest.mark.skip(reason="feature to be developed soon")
def test_TmcExplorer_make_proto(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    proto_A = exp.make_proto(
        tmc.all_Symbols['MAIN.ulimit'],
        ['MAIN']
    )    
    
    proto = exp.make_proto(
        tmc.all_Symbols['MAIN.ulimit'],
        ['MAIN']
    )    

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
    



def test_TmcExplorer_make_proto_from_data(generic_tmc_path):
    tmc = TmcFile(generic_tmc_path)
    exp = TmcExplorer(tmc)
    proto = exp.make_proto(
        "Main.ulimit",
        tmc.all_Symbols['MAIN.ulimit'],
        ['MAIN']
    )
    assert type(proto) == SingleProtoData
    assert proto.name == "Main.ulimit"
    assert proto.out_field == 'MAIN.ulimit?'
    assert proto.in_field == 'OK'
    assert proto.has_init == False 
    
    proto  = exp.make_proto(
        tmc.all_SubItems['DUT_STRUCT']['struct_var'],
        ['MAIN', 'struct_base'],
        prefix = tmc.all_Symbols['MAIN.struct_base'].pv,
    )
    assert type(proto) == SingleProtoData
    assert proto.out_field == 'MAIN.struct_base.struct_var=%d'
    assert proto.in_field == "OK";
    assert proto.has_init == False
    #
    #record = exp.make_record(tmc.all_Symbols['MAIN.NEW_VAR'])
    #assert type(record) == SingleRecordData
    #assert record.pv == 'TEST:MAIN:NEW_VAR'
    #assert record.rec_type == 'bo'
    #assert record.fields == {'ZNAM':'SINGLE','ONAM':'MULTI'}
