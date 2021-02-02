# -*- coding: utf-8 -*-
from os import getcwd
from . import messages
from . import readmol
from .utils import natsort
from .fileutils import AbsPath, NotAbsolutePath, diritems

def printchoices(choices, indent=1, default=None):
    for choice in natsort(choices):
        if choice == default:
            print(' '*2*indent + choice + ' '*3 + '(default)')
        else:
            print(' '*2*indent + choice)

def findparameters(rootpath, components, defaults, indent):
    component = next(components, None)
    if component:
        try:
            findparameters(rootpath.joinpath(component.format()), components, defaults, indent)
        except IndexError:
            choices = diritems(rootpath, component)
            try:
                default = component.format(*defaults)
            except IndexError:
                default = None
            printchoices(choices=choices, default=default, indent=indent)
            for choice in choices:
                findparameters(rootpath.joinpath(choice), components, defaults, indent + 1)
            
def readcoords(molfile):
    if molfile.hasext('.mol'):
        reader = readmol.readmol
    elif molfile.hasext('.xyz'):
        reader = readmol.readxyz
    elif molfile.hasext('.log'):
        reader = readmol.readlog
    else:
        messages.error('Solamente se pueden leer archivos mol, xyz y log')
    if molfile.isfile():
        with open(molfile, mode='r') as fh:
            return reader(fh)
    elif molfile.isdir():
        messages.error('El archivo de coordenadas', molfile, 'es un directorio')
    elif molfile.exists():
        messages.error('El archivo de coordenadas', molfile, 'no es un archivo regular')
    else:
        messages.error('El archivo de coordenadas', molfile, 'no existe')

