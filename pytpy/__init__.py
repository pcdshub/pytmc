import logging

logger = logging.getLogger(__name__)

from .xml_obj import Symbol, DataType

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
