"""
Collections of higher level tests that don't fit cleanly into unit or module
test files.
"""

import pytest

from pytmc import parser
from pytmc.bin.db import process as db_process

from .conftest import PROJ_ROOT, TMC_ROOT


@pytest.mark.parametrize(
    "tmc_file_name, target_pv",
    [
        pytest.param(TMC_ROOT / "ArbiterPLC.tmc", "BeamClass"),
        pytest.param(
            PROJ_ROOT / "pmps-dev-arbiter/Arbiter/ArbiterPLC/ArbiterPLC.tmc",
            "Attenuationsssss",  # sic
            marks=pytest.mark.xfail,
        ),
    ],
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
        tmc, dbd_file=None, allow_errors=False, show_error_context=True
    )

    assert any((target_pv in x.pvname) for x in records)
    assert exceptions == []


def test_allow_no_pragma():
    """
    Test for the existence of a variable included in the records, despite it
    lacking a proper set of pragmas.
    """
    tmc_file_name = TMC_ROOT / ("xtes_sxr_plc.tmc")

    tmc = parser.parse(tmc_file_name)

    records, exceptions = db_process(
        tmc,
        dbd_file=None,
        allow_errors=True,
        show_error_context=True,
        allow_no_pragma=False,
    )

    all_records, exceptions = db_process(
        tmc,
        dbd_file=None,
        allow_errors=True,
        show_error_context=True,
        allow_no_pragma=True,
    )
    good_records = 129
    total_records = 1005

    assert good_records == len(records)
    assert good_records == len(list(x.valid for x in records if x.valid))
    assert total_records == len(all_records)
    assert good_records == len(list(x.valid for x in all_records if x.valid))

    # this variable lacks a pragma
    target_variable = "GVL_DEVICES.MR2K3_GCC_1.rV"
    for x in all_records:
        print(x.tcname)
    assert any((target_variable == x.tcname) for x in all_records)
    assert exceptions == []
