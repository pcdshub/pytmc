from pytmc.bin.stcmd import main as stcmd_main
from pytmc.bin.summary import main as summary_main


def test_summary(project_filename):
    summary_main(cmdline_args=[project_filename, '-a'])


def test_stcmd(project_filename):
    stcmd_main(cmdline_args=[project_filename])
