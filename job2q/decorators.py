# -*- coding: utf-8 -*-
from . import colors
from .utils import deepjoin, pathseps

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

