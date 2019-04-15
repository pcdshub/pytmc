import logging

from ._version import get_versions  # noqa
from .xml_obj import Symbol, DataType, SubItem  # noqa
from .xml_collector import TmcFile  # noqa


logger = logging.getLogger(__name__)
__version__ = get_versions()['version']
del get_versions


__all__ = [
    'DataType',
    'SubItem',
    'Symbol',
    'TmcFile',
    'logger',
]
