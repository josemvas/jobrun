# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from past.builtins import basestring

import os
import sys
import errno
import shutil
from termcolor import colored
from re import match, IGNORECASE 
from os.path import basename, dirname
from jobToQueue.classes import ec, it, cl


if sys.version_info[0] < 3:
    def input(question):
       return raw_input(question.encode(sys.stdout.encoding))


# Python 2 and 3
def textform(*args, **kwargs):
    sep = kwargs.pop('sep', ' ')
    end = kwargs.pop('end', '\n')
    indent = kwargs.pop('indent', 0)
    line = [ ]
    for arg in args:
        if type(arg) is list: line.append(sep.join(arg))
        elif arg: line.append(arg)
    return ' '*indent + sep.join(line) + end
# Python 3 only
#def textform(*args, sep=' ', end='\n', indent=0):
#    line = [ ]
#    for arg in args:
#        if type(arg) is list: line.append(sep.join(arg))
#        elif type(arg) is str: line.append(arg)
#    return ' '*indent + sep.join(line) + end


def quote(string):
    if '"' in string and "'" in string: post('El texto contiene comillas simples y dobles:', string , kind=runerror)
    if '"' in string: return '"{}"'.format(string.rstrip().replace('"', "'"))
    else: return '"{}"'.format(string.rstrip())


def prompt(*args, **kwargs):
    #TODO: Validate path
    def path_prompt(question):
        return input(question + ':' + ' ')
    def ok_prompt(question):
        while True:
            answer = input(question + ' ')
            if match('(ok|y|ye|yes|s|si)$', answer, IGNORECASE):
                return True
            else:
                return False
    def yesno_prompt(question):
        while True:
            answer = input(question + ' ')
            if match('s$', answer, IGNORECASE):
                print('Por favor escriba "si" para confirmar:')
            elif match('(y|ye)$', answer, IGNORECASE):
                print('Por favor escriba "yes" para confirmar:')
            elif match('(si|yes)$', answer, IGNORECASE):
                return True
            elif match('(n|no)$', answer, IGNORECASE):
                return False
    try:
        import bullet
    except ImportError:
        def list_prompt(question, choices):
            print(question)
            for i, option in enumerate(choices):
                print('  {}) {}'.format(cl.lower[i], option));
            while True:
                letter = input('Selección: ').strip()
                if len(letter.split()) != 1:
                    post('Seleccione exactamente una opción', kind=ec.warning)
                else:
                    try:
                        return choices[cl.lower.index(letter.lower())]
                    except ValueError:
                        post(letter, 'no es una letra, intente de nuevo', kind=ec.warning)
                    except IndexError:
                        post(letter, 'no es una opción válida, intente de nuevo', kind=ec.warning)
        def check_prompt(question, choices, default):
            print(question)
            for i, choice in enumerate(choices):
                print('  {}) {}'.format(cl.upper[i] if choice in default else cl.lower[i], choice));
            while True:
                chosen = [ ]
                letters = input('Selección separada por espacios: ').strip().split()
                for letter in letters:
                    try:
                        chosen.append(choices[cl.lower.index(letter.lower())])
                    except ValueError:
                        post(letter, 'no es una letra, intente de nuevo', kind=ec.warning)
                        break
                    except IndexError:
                        post(letter, 'no es una opción válida, intente de nuevo', kind=ec.warning)
                        break
                if len(chosen) == len(letters):
                    return chosen
    else:
        def list_prompt(question, choices):
            return bullet.Bullet(
                prompt = question,
                choices = choices,
                indent = 0,
                align = 2, 
                margin = 1,
                bullet = '>',
                #bullet_color=bullet.colors.background["black"],
                bullet_color=bullet.colors.foreground["blue"],
                word_color=bullet.colors.foreground["white"],
                word_on_switch=bullet.colors.foreground["blue"],
                background_color=bullet.colors.background["black"],
                background_on_switch=bullet.colors.background["black"],
                pad_right = 5,
                ).launch()
        def check_prompt(question, choices, default):
            return bullet.Check(
                prompt = question,
                choices = choices,
                indent = 0,
                align = 2, 
                margin = 1,
                check = 'X',
                check_color=bullet.colors.background["black"],
                check_on_switch=bullet.colors.foreground["blue"],
                word_color=bullet.colors.foreground["white"],
                word_on_switch=bullet.colors.foreground["blue"],
                background_color=bullet.colors.background["black"],
                background_on_switch=bullet.colors.background["black"],
                pad_right = 5,
                ).launch(default=[choices.index(i) for i in default])
    question = ' '.join([i if isinstance(i, basestring) else str(i) for i in args])
    kind = kwargs.pop('kind')
    choices = kwargs.pop('choices', [ ])
    default = kwargs.pop('default', [ ])
    try:
        if kind == it.path:
            return path_prompt(question)
            #return bullet.Input(prompt=question).launch()
        elif kind == it.ok:
            return ok_prompt(question)
            #return bullet.YesNo(prompt=question).launch()
        elif kind == it.yn:
            return yesno_prompt(question)
            #return bullet.YesNo(prompt=question).launch()
        elif kind == it.radio:
            return list_prompt(question, choices)
        elif kind == it.check:
            return check_prompt(question, choices, default)
        else:
            post('Tipo de prompt inválido', kind=ec.cfgerr)
    except KeyboardInterrupt:
        sys.exit(colored('Cancelado por el usuario', 'red'))


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
    elif kind == runerror:
        frame = sys._getframe(1)
        sys.exit(colored('{}:{} {}'.format(basename(frame.f_code.co_filename), frame.f_code.co_name, message), 'red'))
    else:
        message('Tipo de aviso inválido:', kind, kind=cfgkind)


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            post('No se pudo crear el directorio', e, kind=runerror)

def remove(path):
    try:
        os.remove(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            post('No se pudo eliminar el archivo:', e, kind=runerror)


def rmdir(path):
    try:
        os.rmdir(path)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            post('No se pudo eliminar el directorio:', e, kind=runerror)


def copyfile(source, dest):
    try:
        shutil.copyfile(source, dest)
    except IOError as e:
        if e.errno == errno.ENOENT:
            post('No existe el archivo de origen', source + ',', 'o el directorio de destino', dirname(dest), kind=runerror)
        if e.errno == errno.EEXIST:
            post('Ya existe el archivo de destino', dest, kind=runerror)


def pathjoin(*components):
    return os.path.join(*[ '.'.join(x) if type(x) is list else x for x in components ])


