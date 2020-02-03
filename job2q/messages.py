# -*- coding: utf-8 -*-
import sys
from . import colors
from .decorators import join_positional_args
from .utils import wordseps

@join_positional_args(wordseps)
def success(message):
    print(colors.green + message + colors.default)

@join_positional_args(wordseps)
def warning(message):
    print(colors.yellow + message + colors.default)

@join_positional_args(wordseps)
def failure(message):
    print(colors.red + message + colors.default)

@join_positional_args(wordseps)
def error(message):
    raise SystemExit(colors.red + message + colors.default)

@join_positional_args(wordseps)
def opterror(message):
    raise SystemExit(colors.red + '¡Error! {0}'.format(message) + colors.default)

@join_positional_args(wordseps)
def cfgerror(message):
    raise SystemExit(colors.red + '[Error de configuración] {0}'.format(message) + colors.default)

@join_positional_args(wordseps)
def runerror(message):
    fcode = sys._getframe(1).f_code
    raise SystemExit(colors.red + '{0}:{1} {2}'.format(fcode.co_filename, fcode.co_name, message) + colors.default)

@join_positional_args(wordseps)
def listing(message, items=[], default=None):
    if message:
        print(message)
    for item in items:
        if item == default:
            print(' '*2 + item + ' ' + '(default)')
        else:
            print(' '*2 + item)


