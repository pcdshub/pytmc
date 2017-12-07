import versioneer
from setuptools import (setup, find_packages)


setup(name     = 'pytpy',
      version  = versioneer.get_version(),
      cmdclass = versioneer.get_cmdclass(),
      author   = 'SLAC National Accelerator Laboratory',

      packages    = find_packages(),
      description = 'Generate Epics DB records from TwinCAT .tpy files',
      include_package_data = True,
)
