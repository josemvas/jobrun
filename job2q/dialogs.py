# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import sys
import inspect
import readline
from glob import glob
from builtins import str
from job2q.utils import basename, pathexpand
from job2q import colors

try:
    import bulletin
    bulletin_dialogs = bulletin.Dialogs(margin=1, pad_left=1, pad_right=1)
except ImportError:
    bulletin_dialogs = None

if sys.version_info[0] < 3:
    def input(prompt):
       return raw_input(prompt.encode(sys.stdout.encoding))

readline.set_completer_delims(' \t\n')
readline.parse_and_bind('tab: complete')

def catch_keyboard_interrupt(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except KeyboardInterrupt:
            notices.runerr('Cancelado por el usuario')
    return wrapper

def join_positional_args(fn):
    def wrapper(*args, **kwargs):
        prompt = ' '.join([i if isinstance(i, str) else str(i) for i in args])
        return fn(prompt, **kwargs)
    return wrapper

def decorate_class_methods(decorator):
    def decorate(cls):
        for name, fn in inspect.getmembers(cls, inspect.isroutine):
            setattr(cls, name, decorator(fn))
        return cls
    return decorate

def override_class_methods(module):
    def override(cls):
        for name, fn in inspect.getmembers(cls, inspect.isroutine):
            if hasattr(module, name):
                try: setattr(cls, name, getattr(module, name))
                except Exception as e: print('Exception:', e)
        return cls
    return override

class tabCompleter(object):
    def __init__(self, options=[], maxtcs=1):
        self.options = options
        self.maxtcs = maxtcs
        return
    def tcpath(self, text, n):
        return [i + '/' for i in glob(readline.get_line_buffer() + '*')][n]
    def tclist(self, text, n):
        completed = readline.get_line_buffer().split()[:-1]
        if self.maxtcs is None or len(completed) < int(self.maxtcs):
            return [i + ' ' for i in self.options if i.startswith(text) and i not in completed][n]

@decorate_class_methods(catch_keyboard_interrupt)
@decorate_class_methods(join_positional_args)
@override_class_methods(bulletin_dialogs)
class dialogs(object):
    @staticmethod
    def path(prompt=''):
        readline.set_completer(tabCompleter().path)
        return pathexpand(input(prompt + ': '))
    @staticmethod
    def yn(prompt='', default=None):
        while True:
            readline.set_completer(tabCompleter(['yes', 'si', 'no']).tclist)
            answer = input(prompt + ' ').strip()
            if answer:
                if any(word.startswith(answer.lower()) for word in ('yes', 'si')):
                    return True
                elif any(word.startswith(answer.lower()) for word in ('no')):
                    return False
            else:
                if isinstance(default, bool):
                    return default
    @staticmethod
    def yesno(prompt='', default=None):
        while True:
            readline.set_completer(tabCompleter(['yes', 'si', 'no']).tclist)
            answer = input(prompt + ' ').strip()
            if answer:
                if any(word.startswith(answer.lower()) for word in ('yes', 'si', 'no')):
                    if answer in ('yes', 'si'):
                        return True
                    if answer in ('no'):
                        return False
                    else:
                        print('Por favor responda "si" o "yes" para confirmar o "no" para cancelar:')
            else:
                if isinstance(default, bool):
                    return default
    @staticmethod
    def optone(prompt='', choices=[]):
        readline.set_completer(tabCompleter(choices).tclist)
        print(prompt)
        for choice in choices:
            print(' '*2 + choice);
        while True:
            chosen = input('Elección (TAB para autocompletar): ').strip()
            if chosen in choices:
                return chosen
            else:
                notices.warning('Elección inválida, intente de nuevo')
    @staticmethod
    def optany(prompt='', choices=[], default=[]):
        readline.set_completer(tabCompleter(choices, maxtcs=None).tclist)
        print(prompt)
        for choice in choices:
            print(' '*2 + choice);
        while True:
            chosen = input('Selección (TAB para autocompletar): ').strip().split()
            if set(chosen) <= set(choices):
                return chosen
            else:
                notices.warning('Selección inválida, intente de nuevo')
    
@decorate_class_methods(join_positional_args)
class notices(object):
    @staticmethod
    def success(message=''):
        print(colors.green + message + colors.default)
    @staticmethod
    def warning(message=''):
        print(colors.yellow + message + colors.default)
    @staticmethod
    def error(message=''):
        print(colors.red + message + colors.default)
    @staticmethod
    def opterr(message=''):
        sys.exit(colors.red + '¡Error! {0}'.format(message) + colors.default)
    @staticmethod
    def cfgerr(message=''):
        sys.exit(colors.red + '¡Error de configuración! {0}'.format(message) + colors.default)
    @staticmethod
    def runerr(message=''):
        frame = sys._getframe(1)
        sys.exit(colors.red + '¡Error de configuración! {0}'.format(message) + colors.default)
        sys.exit(colors.red + '{0}:{1} {2}'.format(basename(frame.f_code.co_filename), frame.f_code.co_name, message) + colors.default)

