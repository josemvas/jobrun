# -*- coding: utf-8 -*-
import sys
import readline
from os import path, getcwd
from glob import glob
from . import messages
from .fileutils import AbsPath, NotAbsolutePath
from .utils import override_function, catch_keyboard_interrupt, join_arguments, wordseps

try:
    import bulletin
except ImportError:
    dialogs = None
else:
    dialogs = bulletin.Dialogs()

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

@join_arguments(wordseps)
@catch_keyboard_interrupt
def inputpath(prompt='', check=lambda _:True):
    while True:
        readline.set_completer(tabCompleter().tcpath)
        answer = input(prompt + ': ')
        if answer:
            anspath = AbsPath(answer, cwdir=getcwd())
            if check(anspath):
                return anspath
            else:
                print('Por favor indique una ruta válida')

@join_arguments(wordseps)
@catch_keyboard_interrupt
def yesno(prompt='', default=None):
    while True:
        readline.set_completer(tabCompleter(['yes', 'si', 'no']).tclist)
        print('{} (si/no):'.format(prompt), end='')
        answer = input(' ').strip()
        if answer:
            if any(word.startswith(answer.lower()) for word in ('yes', 'si', 'no')):
                if answer in ['yes', 'si']:
                    return True
                if answer in ['no']:
                    return False
                else:
                    print('Por favor responda "si" o "yes" para confirmar o "no" para cancelar:')
        else:
            if isinstance(default, bool):
                return default

@join_arguments(wordseps)
@catch_keyboard_interrupt
@override_function(dialogs)
def chooseone(prompt='', choices=[], default=None):
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

@join_arguments(wordseps)
@catch_keyboard_interrupt
@override_function(dialogs)
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

