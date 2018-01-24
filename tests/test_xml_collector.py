import pytest
import logging

import xml.etree.ElementTree as ET

#from pytpy.xml_obj import Symbol, DataType
from pytpy import Symbol, DataType, SubItem
from pytpy.xml_obj import BaseElement

from pytpy import TmcFile 
from collections import defaultdict

logger = logging.getLogger(__name__)


def test_TmcFile_instantiation():
    try:
        tmc = TmcFile()
    except:
        pytest.fail("Instantiation of TmcFile should not generate errors")
