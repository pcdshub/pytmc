"""
Collections of higher level tests that don't fit cleanly into unit or module
test files.
"""
import logging

import pytest

from pytmc import linter, parser
from pytmc.bin.db import process as db_process


def test_global_pinned_variables(tmc_lcls_twincat_pmps_tmc):
    """
    Ensure that one of the pinned global variables can be found in the list of
    records created when parsing this tmc file. This tmc file was specifically
    created to contain the 'plcAttribute_pytmc' style <Name> fields in place of
    the normal 'pytmc'.
    """
    tmc = parser.parse(tmc_lcls_twincat_pmps_tmc)

    records, exceptions = db_process(
        tmc, dbd_file=None, allow_errors=True,
        show_error_context=True
    )
    print(tmc)
    print(records)
    print(exceptions)
    test_string = "Attenuationssss"

    assert any((test_string in x.pvname) for x in records)
    assert exceptions == []
