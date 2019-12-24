# -*- coding: utf-8 -*-
python_requires = (2, 6)

import sys
if sys.version_info < python_requires:
    sys.exit('Python {0} or higher is required to setup this package.'.format('.'.join(str(i) for i in python_requires)))
import sys

import setuptools
setuptools.setup()
