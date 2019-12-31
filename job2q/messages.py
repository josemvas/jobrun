# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import sys

from job2q import colors
from job2q.decorators import join_positional_args

@join_positional_args
def success(message):
    print(colors.green + message + colors.default)

@join_positional_args
def warning(message):
    print(colors.yellow + message + colors.default)

@join_positional_args
def failure(message):
    print(colors.red + message + colors.default)

@join_positional_args
def error(message):
    raise SystemExit(colors.red + message + colors.default)

@join_positional_args
def opterr(message):
    raise SystemExit(colors.red + '¡Error! {0}'.format(message) + colors.default)

@join_positional_args
def cfgerr(message):
    raise SystemExit(colors.red + '¡Error de configuración! {0}'.format(message) + colors.default)

@join_positional_args
def runerr(message):
    fcode = sys._getframe(1).f_code
    raise SystemExit(colors.red + '{0}:{1} {2}'.format(fcode.co_filename, fcode.co_name, message) + colors.default)

@join_positional_args
def lsinfo(message, info=[], default=None):
    if message:
        print(message)
    for key in info:
        if key == default:
            print(' '*3 + key + ' ' + '(default)')
        else:
            print(' '*3 + key)


