import pytmc
from . import conftest


def test_generate_fields():
    print(pytmc.epics.generate_pytmc_valid_fields(conftest.DBD_FILE))
