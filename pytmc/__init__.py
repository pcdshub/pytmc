import logging

from . import linter, parser, pragmas
from ._version import get_versions
from .record import EPICSRecord, RecordPackage

logger = logging.getLogger(__name__)
__version__ = get_versions()['version']
del get_versions


__all__ = [
    'EPICSRecord',
    'RecordPackage',
    'linter',
    'logger',
    'parser',
    'pragmas',
]
