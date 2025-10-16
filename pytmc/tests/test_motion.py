from pathlib import Path

from pytmc import parser
from pytmc.bin import stcmd

from .conftest import get_real_motor_symbols


def test_motion_stcmd(capsys, project_filename):
    """
    Sanity check of motor setup in the st.cmd files

    For all plc projects:
        1. Is a controller created only when needed?
        2. Are the right number of axes created?

    Note: capsys is a built-in pytest fixture for capturing stdout and stderr
    """
    controller_func = "EthercatMCCreateController"
    motor_func = "EthercatMCCreateAxis"

    full_project = parser.parse(project_filename)

    for plc_name, plc_project in full_project.plcs_by_name.items():
        motors = get_real_motor_symbols(plc_project)
        # Clear captured buffer just in case
        capsys.readouterr()
        stcmd.main(
            project_filename, plc_name=plc_name, only_motor=True, allow_errors=True
        )
        output = capsys.readouterr().out

        if motors:
            assert controller_func in output
        else:
            assert controller_func not in output

        assert output.count(motor_func) == len(motors)


def test_axis_name_without_pragma():
    from .test_xml_collector import make_mock_twincatitem, make_mock_type

    axis = make_mock_twincatitem(
        name="Main.my_axis",
        data_type=make_mock_type("ST_MotionStage", is_complex_type=True),
        # pragma='pv: OUTER',
    )

    class NCAxis:
        name = "Axis 1"

    axis.nc_axis = NCAxis
    user_config = dict(delim=":", prefix="PREFIX")
    prefix, name = stcmd.get_name(axis, user_config=user_config)
    assert name == NCAxis.name.replace(" ", user_config["delim"])
    assert prefix == user_config["prefix"] + user_config["delim"]


def test_axis_name_with_pragma():
    from .test_xml_collector import make_mock_twincatitem, make_mock_type

    axis = make_mock_twincatitem(
        name="Main.my_axis",
        data_type=make_mock_type("ST_MotionStage", is_complex_type=True),
        pragma="pv: MY:STAGE",
    )

    # axis.nc_axis is unimportant here as we have the pragma
    user_config = dict(delim=":", prefix="PREFIX")
    prefix, name = stcmd.get_name(axis, user_config=user_config)
    assert (prefix, name) == ("MY:", "STAGE")


def test_mixed_motionstage_naming():
    """
    Check an example tmc file with 9 ST_MotionStage and 1 DUT_MotionStage

    We are expecting 10 motor symbols
    If only 9: we only recognize ST_MotionStage
    If only 1: we only recognize DUT_MotionStage
    """
    file = Path(__file__).parent / 'tmc_files' / 'tc_mot_example.tmc'
    tmc_item = parser.parse(file)
    motors = tmc_item.find(parser.Symbol_ST_MotionStage)
    assert len(list(motors)) == 10


def test_macro_in_motor_stcmd():
    """
    Make sure the @ -> $ substitutions happen in stcmd.

    The example TMC has some @(PREFIX) substitutions on motors as well as some
    motors with no @ substitutions.
    """
    file = Path(__file__).parent / 'tmc_files' / 'tc_mot_example.tmc'
    tmc_item = parser.parse(file)
    all_motors = list(tmc_item.find(parser.Symbol_ST_MotionStage))
    yes_sub = [
        motor for motor in all_motors if "@" in next(parser.get_pragma(motor))
    ]
    assert len(yes_sub) > 0, "No motors found that need subs"
    assert len(all_motors) > len(yes_sub), "No motors found that don't need subs"
    user_config = dict(delim=":", prefix="")
    for motor in all_motors:
        prefix, name = stcmd.get_name(obj=motor, user_config=user_config)
        if motor in yes_sub:
            # All the subs here are supposed to drop in the PREFIX
            assert "$(PREFIX)" in prefix
        else:
            # Make sure the non-subs don't get distorted
            assert prefix + name in next(parser.get_pragma(motor))
            # Make sure we didn't miscategorize a yes_sub
            assert "$(PREFIX)" not in prefix + name
        assert "@" not in prefix
        assert "@" not in name
