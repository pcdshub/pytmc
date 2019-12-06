"""
Collections of higher level tests that don't fit cleanly into unit or module
test files.
"""
import logging

import pytest

from pytmc import linter, parser
from pytmc.bin.db import process as db_process
from .conftest import TMC_ROOT, PROJ_ROOT


@pytest.mark.parametrize(
    'tmc_file_name, target_pv',
    [
        pytest.param(TMC_ROOT / "ArbiterPLC.tmc", "BeamClass"),
        pytest.param(
            PROJ_ROOT / "pmps-dev-arbiter/Arbiter/ArbiterPLC/ArbiterPLC.tmc",
            "Attenuationsssss",  # sic
            marks=pytest.mark.xfail
        )
    ]
)
def test_global_pinned_variables(tmc_file_name, target_pv):
    """
    Ensure that one of the pinned global variables can be found in the list of
    records created when parsing this tmc file. This tmc file was specifically
    created to contain the 'plcAttribute_pytmc' style <Name> fields in place of
    the normal 'pytmc'.
    """
    tmc = parser.parse(tmc_file_name)

    records, exceptions = db_process(
        tmc, dbd_file=None, allow_errors=False,
        show_error_context=True
    )

    assert any((target_pv in x.pvname) for x in records)
    assert exceptions == []
