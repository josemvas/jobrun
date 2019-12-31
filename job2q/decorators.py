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
            raise SystemExit(colors.red + 'Cancelado por el usuario' + colors.default)
    return wrapper

def join_positional_args(f):
    def wrapper(*args, **kwargs):
        return f(' '.join(args), **kwargs)
    return wrapper

def override_with_method(cls):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if hasattr(cls, f.__name__):
                return getattr(cls, f.__name__)(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        return wrapper
    return decorator

def decorate_class_methods(decorator):
    def decorate(cls):
        for name, f in inspect.getmembers(cls, inspect.isroutine):
            setattr(cls, name, decorator(f))
        return cls
    return decorate

def override_class_methods(cls):
    def override(cls):
        for name, _ in inspect.getmembers(cls, inspect.isroutine):
            if hasattr(cls, name):
                try: setattr(cls, name, getattr(cls, name))
                except Exception as e: print('Exception:', e)
        return cls
    return override

