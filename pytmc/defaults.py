import configparser
import pkg_resources
import logging
logger = logging.getLogger(__name__)


config = configparser.ConfigParser(allow_no_value=True)
config.read(
    pkg_resources.resource_filename('pytmc', 'default_settings/conf.ini')
)
