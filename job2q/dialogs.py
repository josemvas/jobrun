# -*- coding: utf-8 -*-
import sys
import readline
from glob import glob
from os import path, getcwd

from . import messages
from .utils import realpath, wordjoin
from .decorators import override_with_bulletin, catch_keyboard_interrupt, join_positional_args

readline.set_completer_delims(' \t\n')
readline.parse_and_bind('tab: complete')

class tabCompleter(object):
    def __init__(self, choices=[], maxtcs=1):
        self.choices = choices
        self.maxtcs = maxtcs
        return
    def tcpath(self, text, n):
        return [i + '/' if path.isdir(i) else i + ' ' for i in glob(path.expanduser(text) + '*')][n]
    def tclist(self, text, n):
        completed = readline.get_line_buffer().split()[:-1]
        if self.maxtcs is None or len(completed) < int(self.maxtcs):
            return [i + ' ' for i in self.choices if i.startswith(text) and i not in completed][n]

@join_positional_args
@catch_keyboard_interrupt
def inputpath(prompt=''):
    while True:
        readline.set_completer(tabCompleter().tcpath)
        answer = input(prompt + ': ')
        if answer:
            if path.exists(answer):
                return realpath(answer)
            else:
                print('Por favor indique una ruta válida')
def yn(prompt='', default=None):
    while True:
        readline.set_completer(tabCompleter(['yes', 'si', 'no']).tclist)
        answer = input('{} (s/n): '.format(prompt)).strip()
        if answer:
            if any(word.startswith(answer.lower()) for word in ('yes', 'si')):
                return True
            elif any(word.startswith(answer.lower()) for word in ('no')):
                return False
        else:
            if isinstance(default, bool):
                return default

@join_positional_args
@catch_keyboard_interrupt
def yesno(prompt='', default=None):
    while True:
        readline.set_completer(tabCompleter(['yes', 'si', 'no']).tclist)
        answer = input('{} (si/no): '.format(prompt)).strip()
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

@join_positional_args
@catch_keyboard_interrupt
@override_with_bulletin
def chooseone(prompt='', choices=[]):
    readline.set_completer(tabCompleter(choices).tclist)
    print(prompt)
    for choice in choices:
        print(' '*2 + choice);
    while True:
        choice = input('Elección (TAB para autocompletar): ').strip()
        if choice in choices:
            return choice
        else:
            messages.warning('Elección inválida, intente de nuevo')

@join_positional_args
@catch_keyboard_interrupt
@override_with_bulletin
def choosemany(prompt='', choices=[], default=[]):
    readline.set_completer(tabCompleter(choices, maxtcs=None).tclist)
    print(prompt)
    for choice in choices:
        print(' '*2 + choice);
    while True:
        choice = input('Selección (TAB para autocompletar): ').strip().split()
        if set(choice) <= set(choices):
            return choice
        else:
            messages.warning('Selección inválida, intente de nuevo')

