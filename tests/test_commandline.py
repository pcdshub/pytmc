import pytest
import sys

import pytmc.bin.pytmc as pytmc_main
from pytmc.bin.db import main as db_main
from pytmc.bin.debug import create_debug_gui
from pytmc.bin.pragmalint import main as pragmalint_main
from pytmc.bin.stcmd import main as stcmd_main
from pytmc.bin.summary import main as summary_main
from pytmc.bin.types import create_types_gui
from pytmc.bin.xmltranslate import main as xmltranslate_main


def test_help_main(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['--help'])
    pytmc_main.main()


@pytest.mark.parametrize('subcommand',
                         pytmc_main.COMMANDS.keys()
                         )
def test_help_module(monkeypatch, subcommand):
    monkeypatch.setattr(sys, 'argv', [subcommand, '--help'])
    with pytest.raises(SystemExit):
        pytmc_main.main()


def test_summary(project_filename):
    summary_main(project_filename, show_all=True, show_code=True,
                 use_markdown=True)


@pytest.fixture()
def project_filename_linter_success(project_filename):
    """ Return True if project should pass the linter test"""
    if "lcls-twincat-pmps.tsproj" in project_filename:
        return False
    return True


def test_pragmalint(project_filename, project_filename_linter_success):
    if not project_filename_linter_success:
        pytest.xfail("Project's current state does not satisfy linter")
    pragmalint_main(project_filename, verbose=True, use_markdown=True)


def test_stcmd(project_filename):
    if 'plc_kfe_xgmd_vac' in project_filename:
        kwargs = dict(plc_name='plc_kfe_xgmd_vac')
    elif 'lcls-twincat-motion' in project_filename:
        kwargs = dict(plc_name='Example', allow_errors=True)
    else:
        kwargs = {}
    stcmd_main(project_filename, **kwargs)


def test_xmltranslate(project_filename):
    xmltranslate_main(project_filename)


def test_db(tmc_filename):
    db_main(tmc_filename, archive_file=sys.stderr)


@pytest.mark.xfail
def test_db_archive_bad_args(tmc_filename):
    db_main(tmc_filename, archive_file=sys.stderr, no_archive_file=True)


def test_types(qtbot, tmc_filename):
    widget = create_types_gui(tmc_filename)
    qtbot.addWidget(widget)


def test_debug(qtbot, tmc_filename):
    widget = create_debug_gui(tmc_filename)
    qtbot.addWidget(widget)
