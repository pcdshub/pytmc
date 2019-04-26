import sys
from os import path

import versioneer
from setuptools import (setup, find_packages)


min_version = (3, 6)

if sys.version_info < min_version:
    error = """
pytmc does not support Python {0}.{1}.
Python {2}.{3} and above is required. Check your Python version like so:

python3 --version

This may be due to an out-of-date pip. Make sure you have pip >= 9.0.1.
Upgrade pip like so:

pip install --upgrade pip
""".format(*sys.version_info[:2], *min_version)
    sys.exit(error)


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as readme_file:
    readme = readme_file.read()


setup(
    name     = 'pytmc',
    version  = versioneer.get_version(),
    cmdclass = versioneer.get_cmdclass(),
    author   = 'SLAC National Accelerator Laboratory',
    license='BSD',
    packages    = find_packages(),
    description = 'Generate Epics DB records from TwinCAT .tmc files',
    long_description=readme,
    entry_points = {
        'console_scripts': [
            'pytmc = pytmc.bin.pytmc:main',
            'pytmc-debug = pytmc.bin.pytmc_debug:main',
            'xmltranslate = pytmc.bin.xmltranslate:main',
        ]
    },
    package_data={
      'pytmc': ['templates/*'],
    },
    include_package_data=True,
)
