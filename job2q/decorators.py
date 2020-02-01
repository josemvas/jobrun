# -*- coding: utf-8 -*-
from os import path
#from itertools import repeat
from . import colors

nothing = ('')
wordseps = (' ', '')
pathseps = (path.sep, '.')

def deepjoin(a, i):
    return next(i).join(x if isinstance(x, str) else deepjoin(x, i) if hasattr(x, '__iter__') else str(x) for x in a if x)

def join_positional_args(seq):
    def decorator(f):
        def wrapper(*args, **kwargs):
            return f(deepjoin(args, iter(seq)), **kwargs)
        return wrapper
    return decorator

def catch_keyboard_interrupt(f):
    def wrapper(*args, **kwargs):
        try: return f(*args, **kwargs)
        except KeyboardInterrupt:
            raise SystemExit(colors.red + 'Cancelado por el usuario' + colors.default)
    return wrapper

def override_dialogs(f):
    def wrapper(*args, **kwargs):
        try:
            from bulletin import Dialogs
            return getattr(Dialogs(), f.__name__)(*args, **kwargs)
        except (ImportError, AttributeError):
            return f(*args, **kwargs)
    return wrapper

