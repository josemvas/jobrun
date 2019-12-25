# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import sys
import readline
import job2q.colors
from glob import glob
from builtins import str
from termcolor import colored
from re import match, IGNORECASE 
from job2q.classes import ec, cl
from job2q.utils import basename, pathexpand, decorate_class_methods, catch_keyboard_interrupt, join_positional_args, override_class_methods

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

class tabCompleter(object):
    def __init__(self, options=[], maxtcs=1):
        self.options = options
        self.maxtcs = maxtcs
        return
    def tcpath(self, text, state):
        return [i + '/' for i in glob(readline.get_line_buffer() + '*')][state]
    def tclist(self, text, state):
        completions = readline.get_line_buffer().split()
        if self.maxtcs is None or len(completions) <= int(self.maxtcs):
            return [i + ' ' for i in self.options if i.startswith(text) if i not in completions][state]

#TODO: Validate path, autocomplete path and choices
@decorate_class_methods(catch_keyboard_interrupt)
@decorate_class_methods(join_positional_args)
@override_class_methods(bulletin_dialogs)
class dialogs(object):
    def path(prompt=''):
        readline.set_completer(tabCompleter().path)
        return pathexpand(input(prompt + ': '))
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
                post('Elección inválida, intente de nuevo', kind=ec.warning)
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
                post('Selección inválida, intente de nuevo', kind=ec.warning)
    

@decorate_class_methods(join_positional_args)
class notices(object):
    def success(message=''):
        print(colors.green + message + colors.default)
    def warning(message=''):
        print(colors.yellow + message + colors.default)
    def error(message=''):
        print(colors.red + message + colors.default)
    def opterr(message=''):
        sys.exit(colors.red + '¡Error! {0}'.format(message) + colors.default)
    def cfgerr(message=''):
        sys.exit(colors.red + '¡Error de configuración! {0}'.format(message) + colors.default)
    def runerr(message=''):
        frame = sys._getframe(1)
        sys.exit(colors.red + '¡Error de configuración! {0}'.format(message) + colors.default)
        sys.exit(colors.red + '{0}:{1} {2}'.format(basename(frame.f_code.co_filename), frame.f_code.co_name, message) + colors.default)

def post(*args, **kwargs):
    message = ' '.join([i if isinstance(i, str) else str(i) for i in args])
    kind = kwargs.pop('kind')
    if kind == ec.sucess:
        print(colored(message, 'green'))
    elif kind == ec.warning:
        print(colored(message, 'yellow'))
    elif kind == ec.joberr:
        print(colored(message, 'red'))
    elif kind == ec.opterr:
        sys.exit(colored('¡Error! ' + message, 'red'))
    elif kind == ec.cfgerr:
        sys.exit(colored('¡Error de configuración! ' + message, 'red'))
    elif kind == ec.runerr:
        frame = sys._getframe(1)
        sys.exit(colored('{}:{} {}'.format(basename(frame.f_code.co_filename), frame.f_code.co_name, message), 'red'))
    else:
        message('Tipo de aviso inválido:', kind, kind=cfgkind)

