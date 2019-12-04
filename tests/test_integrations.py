"""
Collections of higher level tests that don't fit cleanly into unit or module
test files.
"""
import logging

import pytest

from pytmc import linter, parser
from pytmc.bin.db import process as db_process

def test_global_pinned_variables(tmc_ArbiterPlc):
    
    tmc = parser.parse(tmc_ArbiterPlc)

    records, exceptions = db_process(
        tmc, dbd_file=None, allow_errors=False,
        show_error_context=True
    )
    test_string = "BunchEnergy"
    contains_test_string_list = [
        (test_string in x.pvname) for x in records
    ]
    
    assert any(contains_test_string_list)
    assert exceptions == []
