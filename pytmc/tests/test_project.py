import pprint

import pytest

from pytmc import parser

from .conftest import get_real_motor_symbols


def test_load_and_repr(project):
    info = repr(project)
    print(info[:1000], "...")


def test_summarize(project):
    assert project.root is project
    for cls in [parser.Axis, parser.Encoder]:
        for inst in project.find(cls):
            print(inst.path)
            print("-----------------")
            pprint.pprint(dict(inst.summarize()))

    for inst in project.find(parser.Symbol):
        pprint.pprint(inst.info)
        inst.plc


def test_module_ads_port(project):
    for inst in project.find(parser.Module):
        assert inst.ads_port == 851 or inst.ads_port == 852  # probably!


@pytest.mark.xfail(reason="TODO / project")
def test_smoke_ams_id(project):
    print(project.ams_id)
    print(project.target_ip)


def test_fb_motionstage_linking(project):
    for inst in get_real_motor_symbols(project):
        pprint.pprint(inst)
        print("Program name", inst.program_name)
        print("Motor name", inst.motor_name)
        print("NC to PLC link", inst.nc_to_plc_link)

        nc_axis = inst.nc_axis
        print("Short NC axis name", nc_axis.name)
        print("NC axis", nc_axis)
