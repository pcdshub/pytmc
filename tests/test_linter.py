import logging
import os
import sys

import pytest

import pytmc
import pytmc.bin.pytmc

from . import conftest


@pytest.mark.parametrize(
        'filename',
        conftest.TMC_FILES,
        ids=[f.name for f in conftest.TMC_FILES])
def test_db_linting(dbd_file, tmp_path, filename):
    db_fn = tmp_path / '{}.db'.format(filename)
    tmc_file = pytmc.TmcFile(filename)
    pytmc.bin.pytmc.process(tmc_file, dbd_file=dbd_file, allow_errors=True)
    db_text = tmc_file.render()
    with open(db_fn, 'wt') as f:
        print(db_text, file=f)

    results = tmc_file.validate_with_dbd(dbd_file)
    assert results.success


@pytest.mark.parametrize(
        'filename',
        conftest.INVALID_TMC_FILES,
        ids=[f.name for f in conftest.INVALID_TMC_FILES])
def test_invalid_db_linting(dbd_file, tmp_path, filename):
    db_fn = tmp_path / '{}.db'.format(filename)
    tmc_file = pytmc.TmcFile(filename)
    db_text = pytmc.bin.pytmc.process(tmc_file, dbd_file=dbd_file,
                                      allow_errors=True)
    with open(db_fn, 'wt') as f:
        print(db_text, file=f)

    results = tmc_file.validate_with_dbd(dbd_file)
    assert not results.success
