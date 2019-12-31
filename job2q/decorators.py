# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import inspect

from job2q import colors

def catch_keyboard_interrupt(f):
    def wrapper(*args, **kwargs):
        try: return f(*args, **kwargs)
        except KeyboardInterrupt:
            raise SystemExit(colors.red + 'Cancelado por el usuario' + colors.normal)
    return wrapper

def join_positional_args(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), **kwargs)
    return wrapper

def decorate_class_methods(decorator):
    def decorate(cls):
        for name, f in inspect.getmembers(cls, inspect.isroutine):
            setattr(cls, name, decorator(f))
        return cls
    return decorate

def override_class_methods(module):
    def override(cls):
        for name, _ in inspect.getmembers(cls, inspect.isroutine):
            if hasattr(module, name):
                try: setattr(cls, name, getattr(module, name))
                except Exception as e: print('Exception:', e)
        return cls
    return override

