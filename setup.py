# Minimum Setuptools version supporting configuration metadata in setup.cfg
#min_stversion = '30.3'
# Minimum Setuptools version supporting conditional python dependencies (PEP 508)
min_stversion = '32.2'

import sys
import setuptools
from time import time

# Record time before setup
setup_time = time()

# Setup package if Setuptools version is high enough
setuptools.setup(setup_requires=['setuptools>=' + min_stversion])

