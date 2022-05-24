import logging

from . import _version, linter, parser, pragmas
from .record import EPICSRecord, RecordPackage

logger = logging.getLogger(__name__)

__version__ = _version.get_versions()['version']

__all__ = [
    'EPICSRecord',
    'RecordPackage',
    'linter',
    'logger',
    'parser',
    'pragmas',
]
