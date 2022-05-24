import configparser
import logging

import pkg_resources

logger = logging.getLogger(__name__)


config = configparser.ConfigParser(allow_no_value=True)
config.read(
    pkg_resources.resource_filename('pytmc', 'default_settings/conf.ini')
)
