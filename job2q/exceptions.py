# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys

if sys.version_info[0] < 3:

    FileExistsError = EnvironmentError
    FileNotFoundError = EnvironmentError

