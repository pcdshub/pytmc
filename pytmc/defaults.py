import logging
logger = logging.getLogger(__name__)
import pkg_resources
import configparser


config = configparser.ConfigParser(allow_no_value=True)
config.read(
    pkg_resources.resource_filename('pytmc', 'default_settings/conf.ini')
)
