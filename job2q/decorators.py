# -*- coding: utf-8 -*-
from os import path
from . import colors

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

def join_path_components(f):
    def wrapper(*args, **kwargs):
        return f(path.join(*args), **kwargs)
    return wrapper

def override_dialogs(f):
    def wrapper(*args, **kwargs):
        try:
            from bulletin import Dialogs
            return getattr(Dialogs(), f.__name__)(*args, **kwargs)
        except (ImportError, AttributeError):
            return f(*args, **kwargs)
    return wrapper

