import sys
import pytest
import pytmc
import pytmc.bin.makerecord

from . import conftest

dbdlint = pytest.importorskip('pyPDB.dbdlint')


def test_db_linting(caplog, tmp_path, tmc_filename, monkeypatch):
    db_fn = tmp_path / 'test.db'
    tmc_file = pytmc.TmcFile(tmc_filename)
    db_text = pytmc.bin.makerecord.make_db_text(tmc_file)
    with open(db_fn, 'wt') as f:
        print(db_text, file=f)

    exit_code = 0

    def linter_exit(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr(sys, 'exit', linter_exit)

    args = dbdlint.getargs(
        [str(arg) for arg in
         ['-Wno-quoted', '-F', conftest.DBD_FILE, db_fn]])

    with caplog.at_level('WARNING', logger='dbdlint'):
        dbdlint.main(args)

    print('Captured logs:')
    print(caplog.text)
    print('Linter exited with code', exit_code)
    assert exit_code == 0
