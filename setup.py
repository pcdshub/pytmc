import versioneer
from setuptools import (setup, find_packages)


setup(name     = 'pytmc',
      version  = versioneer.get_version(),
      cmdclass = versioneer.get_cmdclass(),
      author   = 'SLAC National Accelerator Laboratory',
      license='BSD',
      packages    = find_packages(),
      description = 'Generate Epics DB records from TwinCAT .tmc files',
      scripts = ['bin/xmltranslate','bin/makerecord'],
      include_package_data = True,
)
