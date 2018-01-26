import pytest
import logging

import xml.etree.ElementTree as ET

#from pytmc.xml_obj import Symbol, DataType
from pytmc import Symbol, DataType, SubItem
from pytmc.xml_obj import BaseElement

from pytmc import TmcFile
from pytmc.xml_collector import ElementCollector
from pytmc import DbRenderAgent, SingleRecordData

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
                ("INP","Fake_input"),
                ("ZNAM",""),
            ]
        )
    except:
        pytest.fail("Instantiation with arguments has erred")

def test_SingleRecordData_pv_append():
    rec = SingleRecordData(
        pv = "GDET:FEE1:241:ENRC"
    )
    rec.add("ABC:DEF")
    assert rec.pv == "GDET:FEE1:241:ENRC:ABC:DEF"

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
def test_SingleRecordData_check_fields(save_record_factory):
    assert False
