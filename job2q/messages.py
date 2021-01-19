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
def error(message, **kwargs):
    if kwargs:
        sys.exit(colors.red + '{} ({})'.format(message, ', '.join([key + ': ' + value for key, value in kwargs.items()])) + colors.default)
    else:
        sys.exit(colors.red + '{}'.format(message) + colors.default)

@join_arguments(wordseps)
def unknownerror(message):
    fcode = sys._getframe(1).f_code
    sys.exit(colors.red + '{}:{} {}'.format(fcode.co_filename, fcode.co_name, message) + colors.default)

