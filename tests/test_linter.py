import logging
import os
import sys

import pytest

import pytmc
import pytmc.bin.makerecord

from . import conftest

dbdlint = pytest.importorskip('pyPDB.dbdlint')

dbdlint_logger = logging.getLogger('dbdlint')

ALL_TMC_FILES = conftest.TMC_FILES + conftest.INVALID_TMC_FILES


@pytest.mark.parametrize(
    'filename',
    [pytest.param(f, marks=pytest.mark.xfail)
     if f in conftest.INVALID_TMC_FILES else f
     for f in ALL_TMC_FILES
     ],
    ids=[f.name for f in ALL_TMC_FILES]
)
def test_db_linting(caplog, tmp_path, filename, monkeypatch):
    db_fn = tmp_path / '{}.db'.format(filename)
    tmc_file = pytmc.TmcFile(filename)
    db_text = pytmc.bin.makerecord.make_db_text(tmc_file)
    with open(db_fn, 'wt') as f:
        print(db_text, file=f)

    exit_code = 0

    def linter_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr(sys, 'exit', linter_exit)

    with conftest.caplog_at_level(caplog, 'dbdlint', level='WARNING'):
        args = dbdlint.getargs(
            [str(arg) for arg in
             ['-Wno-quoted', '-F', conftest.DBD_FILE, db_fn]])

        dbdlint.main(args)

    print('Warnings/errors from the linter:')

    lines = [
        '{dbfile} line {dbline} {tag}: {msg}'
        ''.format(dbfile=os.path.split(record.dbfile)[-1],
                  dbline=record.dbline, tag=record.tag,
                  msg=record.message)
        for record in caplog.records
        if hasattr(record, 'dbfile')
    ]

    for line in sorted(set(lines)):
        print('[DBDLINT]', line)

    # Clear the log so pytest doesn't show the full list:
    caplog.clear()

    print('Linter exited with code', exit_code)
    assert exit_code == 0
