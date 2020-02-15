# -*- coding: utf-8 -*-
import sys
from . import colors
from .utils import join_arguments, wordseps

@join_arguments(wordseps)
def success(message):
    print(colors.green + message + colors.default)

@join_arguments(wordseps)
def warning(message):
    print(colors.yellow + message + colors.default)

@join_arguments(wordseps)
def failure(message):
    print(colors.red + message + colors.default)

@join_arguments(wordseps)
def error(message):
    raise SystemExit(colors.red + '[Error] {0}'.format(message) + colors.default)

@join_arguments(wordseps)
def opterror(message):
    raise SystemExit(colors.red + '[Error de opciones] {0}'.format(message) + colors.default)

@join_arguments(wordseps)
def cfgerror(message):
    raise SystemExit(colors.red + '[Error de configuración] {0}'.format(message) + colors.default)

@join_arguments(wordseps)
def runerror(message):
    raise SystemExit(colors.red + '[Error de ejecución] {0}'.format(message) + colors.default)

@join_arguments(wordseps)
def unknownerror(message):
    fcode = sys._getframe(1).f_code
    raise SystemExit(colors.red + '{0}:{1} {2}'.format(fcode.co_filename, fcode.co_name, message) + colors.default)

