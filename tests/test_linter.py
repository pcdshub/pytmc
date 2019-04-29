import logging
import os
import sys

import pytest

import pytmc
import pytmc.bin.pytmc

from . import conftest


ALL_TMC_FILES = conftest.TMC_FILES + conftest.INVALID_TMC_FILES


@pytest.mark.parametrize(
    'filename',
    [pytest.param(f, marks=pytest.mark.xfail)
     if f in conftest.INVALID_TMC_FILES else f
     for f in ALL_TMC_FILES
     ],
    ids=[f.name for f in ALL_TMC_FILES]
)
def test_db_linting(dbd_file, tmp_path, filename):
    db_fn = tmp_path / '{}.db'.format(filename)
    tmc_file = pytmc.TmcFile(filename)
    pytmc.bin.pytmc.process(tmc_file, dbd_file=dbd_file, allow_errors=True)
    db_text = tmc_file.render()
    with open(db_fn, 'wt') as f:
        print(db_text, file=f)

    results = tmc_file.validate_with_dbd(dbd_file)
    assert results.success
