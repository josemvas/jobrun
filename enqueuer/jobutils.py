# -*- coding: utf-8 -*-
from os import getcwd
from . import messages
from .utils import natsort
from .fileutils import AbsPath, NotAbsolutePath, diritems
from .chemistry import readxyz

class InputFileError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

def printchoices(choices, indent=1, default=None):
    for choice in natsort(choices):
        if choice == default:
            print(' '*2*indent + choice + ' ' + '(default)')
        else:
            print(' '*2*indent + choice)

def findparameters(rootpath, components, indent):
    if components:
        prepath, postpath, default = components.pop(0)
        choices = diritems(rootpath.joinpath(prepath))
        printchoices(choices=choices, default=default, indent=indent)
        for choice in choices:
            findparameters(rootpath.joinpath(prepath, choice, postpath), components, indent + 1)
            
def readmol(molfile, keywords):
    try:
        molfile = AbsPath(molfile)
    except NotAbsolutePath:
        molfile = AbsPath(getcwd(), molfile)
    if molfile.isfile():
        if molfile.hasext('.xyz'):
            molformat = '{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format
            for i, step in enumerate(readxyz(molfile), 1):
                keywords['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
        else:
            messages.opterror('Solamente están soportados archivos de coordenadas en formato xyz')
    elif molfile.isdir():
        messages.opterror('El archivo de coordenadas', molfile, 'es un directorio')
    elif molfile.exists():
        messages.opterror('El archivo de coordenadas', molfile, 'no es un archivo regular')
    else:
        messages.opterror('El archivo de coordenadas', molfile, 'no existe')
    keywords['file'] = molfile
    return molfile.stem

