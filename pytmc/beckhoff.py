import logging
logger = logging.getLogger(__name__)


beckhoff_types = [
    "BOOL",
    "BYTE",
    "WORD",
    "DWORD",
    "SINT",
    "USINT",
    "INT",
    "UINT",
    "DINT",
    "UDINT",
    "LINT",
    "ULINT",
    "REAL",
    "LREAL",
    "STRING",
    "TIME",
    "TIME_OF_DAY",
    "TOD", #unclear if this is the xml abbreviation for TIME_OF_DAY
    "DATE",
    "DATE_AND_TIME",
    "DT", #unclear if this is the xml abbreviation for DATE_AND_TIME
]
