# -*- coding: utf-8 -*-
import sys
from . import colors
from .utils import join_args, join_allargs, wordseps

@join_allargs
def success(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    print(colors.green + message + colors.default)

@join_allargs
def warning(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    print(colors.yellow + message + colors.default)

@join_allargs
def failure(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    print(colors.red + message + colors.default)

@join_allargs
def error(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    sys.exit(colors.red + message + colors.default)

@join_args
def unknown_error(message):
    fcode = sys._getframe(1).f_code
    sys.exit(colors.red + '{}:{} {}'.format(fcode.co_filename, fcode.co_name, message) + colors.default)

