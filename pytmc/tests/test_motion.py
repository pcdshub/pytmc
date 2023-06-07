from pytmc import parser
from pytmc.bin import stcmd


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
        motors = list(plc_project.find(parser.Symbol_ST_MotionStage))
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
