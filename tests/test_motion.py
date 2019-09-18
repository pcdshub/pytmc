from pytmc import parser
from pytmc.bin.stcmd import main as stcmd_main


def test_motion_stcmd(capsys, project_filename):
    """
    Sanity check of motor setup in the st.cmd files

    For all plc projects:
        1. Is a controller created only when needed?
        2. Are the right number of axes created?

    Note: capsys is a built-in pytest fixture for capturing stdout and stderr
    """
    controller_func = 'EthercatMCCreateController'
    motor_func = 'EthercatMCCreateAxis'

    full_project = parser.parse(project_filename)

    for plc_name, plc_project in full_project.plcs_by_name.items():
        motors = list(plc_project.find(parser.Symbol_DUT_MotionStage))
        # Clear captured buffer just in case
        capsys.readouterr()
        stcmd_main(project_filename, plc_name=plc_name,
                   only_motor=True, allow_errors=True)
        output = capsys.readouterr().out

        if motors:
            assert controller_func in output
        else:
            assert controller_func not in output

        assert output.count(motor_func) == len(motors)
