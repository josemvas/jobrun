# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import sys
import readline
from glob import glob

from job2q.utils import pathexpand, wordjoin
from job2q.decorators import decorate_class_methods, override_class_methods, catch_keyboard_interrupt, join_positional_args
from job2q.messages import messages

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
    def tcpath(self, text, n):
        return [i + '/' for i in glob(readline.get_line_buffer() + '*')][n]
    def tclist(self, text, n):
        completed = readline.get_line_buffer().split()[:-1]
        if self.maxtcs is None or len(completed) < int(self.maxtcs):
            return [i + ' ' for i in self.options if i.startswith(text) and i not in completed][n]

@decorate_class_methods(catch_keyboard_interrupt)
@decorate_class_methods(join_positional_args)
@override_class_methods(bulletin_dialogs)
@decorate_class_methods(staticmethod)
class dialogs(object):
    def path(prompt=''):
        readline.set_completer(tabCompleter().tcpath)
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
                messages.warning('Elección inválida, intente de nuevo')
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
                messages.warning('Selección inválida, intente de nuevo')
    
