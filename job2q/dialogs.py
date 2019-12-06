# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

import sys
import bullet
import readline
from glob import glob
from termcolor import colored
from re import match, IGNORECASE 
from job2q.classes import ec, cl
from job2q.utils import basename, pathexpand, decorate_class_methods, catch_keyboard_interrupt, join_positional_args, override_class_methods
from past.builtins import basestring


readline.set_completer_delims(' \t\n')
readline.parse_and_bind('tab: complete')


if sys.version_info[0] < 3:
    def input(prompt):
       return raw_input(prompt.encode(sys.stdout.encoding))


class tabCompleter(object):

    def __init__(self, options=[]):
        self.options = options
        return

    def path(self, text, state):
        return [i + '/' for i in glob(readline.get_line_buffer() + '*')][state]

    def bullet(self, text, state):
        return [i + ' ' for i in self.options if i.startswith(readline.get_line_buffer())][state]

    def check(self, text, state):
        return [i + ' ' for i in self.options if i.startswith(text) if i not in readline.get_line_buffer().split()][state]


#TODO: Validate path, autocomplete path and choices
@decorate_class_methods(catch_keyboard_interrupt)
@decorate_class_methods(join_positional_args)
#@override_class_methods(bullet)
class dialog(object):

    def path(**kwargs):
        prompt = kwargs.get('prompt', [])
        readline.set_completer(tabCompleter().path)
        return pathexpand(input(prompt + ': '))
    
    def accept(**kwargs):
        prompt = kwargs.get('prompt', [])
        while True:
            answer = input(prompt + ' ')
            if match('(ok|y|ye|yes|s|si)$', answer, IGNORECASE):
                return True
            else:
                return False
    
    def yesno(**kwargs):
        prompt = kwargs.get('prompt', [])
        while True:
            answer = input(prompt + ' ')
            if match('s$', answer, IGNORECASE):
                print('Por favor escriba "si" para confirmar:')
            elif match('(y|ye)$', answer, IGNORECASE):
                print('Por favor escriba "yes" para confirmar:')
            elif match('(si|yes)$', answer, IGNORECASE):
                return True
            elif match('(n|no)$', answer, IGNORECASE):
                return False

    def Bullet(**kwargs):
        prompt = kwargs.get('prompt', [])
        choices = kwargs.get('choices', [])
        readline.set_completer(tabCompleter(choices).bullet)
        print(prompt)
        for choice in choices:
            print(' '*3 + choice);
        while True:
            chosen = input('Elección (TAB para autocompletar): ').strip()
            if chosen in choices:
                return chosen
            else:
                post('Elección inválida, intente de nuevo', kind=ec.warning)
    
    def Check(**kwargs):
        prompt = kwargs.get('prompt', [])
        choices = kwargs.get('choices', [])
        precheck = kwargs.get('precheck', [])
        readline.set_completer(tabCompleter(choices).check)
        print(prompt)
        for choice in choices:
            print(' '*3 + choice);
        while True:
            chosen = input('Selección (TAB para autocompletar): ').strip().split()
            if set(chosen) <= set(choices):
                return chosen
            else:
                post('Selección inválida, intente de nuevo', kind=ec.warning)
    

def post(*args, **kwargs):
    message = ' '.join([i if isinstance(i, basestring) else str(i) for i in args])
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


#def Bullet(prompt, choices):
#    return bullet.Bullet(
#        prompt = prompt,
#        choices = choices,
#        indent = 0,
#        align = 2, 
#        margin = 1,
#        bullet = '>',
#        #bullet_color=bullet.colors.background["black"],
#        bullet_color=bullet.colors.foreground["blue"],
#        word_color=bullet.colors.foreground["white"],
#        word_on_switch=bullet.colors.foreground["blue"],
#        background_color=bullet.colors.background["black"],
#        background_on_switch=bullet.colors.background["black"],
#        pad_right = 5,
#        ).launch()


#def Check(prompt, choices, **kwargs):
#    return bullet.Check(
#        prompt = prompt,
#        choices = choices,
#        indent = 0,
#        align = 2, 
#        margin = 1,
#        check = 'X',
#        check_color=bullet.colors.background["black"],
#        check_on_switch=bullet.colors.foreground["blue"],
#        word_color=bullet.colors.foreground["white"],
#        word_on_switch=bullet.colors.foreground["blue"],
#        background_color=bullet.colors.background["black"],
#        background_on_switch=bullet.colors.background["black"],
#        pad_right = 5,
#        ).launch(default=[choices.index(i) for i in precheck])


