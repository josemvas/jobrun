# -*- coding: utf-8 -*-
#TODO: Support different copy methods besides ssh (for shared filesystems)

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import sys
from os import path, listdir
from argparse import ArgumentParser
from xml.etree import ElementTree
from pyparsing import infixNotation, opAssoc, Keyword, Word, alphas, alphanums
from os.path import basename, realpath, expandvars, expanduser
from distutils import util

from job2q.utils import post, prompt, pathjoin
from job2q.classes import BoolNot, BoolAnd, BoolOr, BoolOperand, Bunch, XmlTreeBunch
from job2q.classes import ec, pr


def getelement(xmlfile, element):

    try:
        with open(xmlfile) as f:
            try:
                xmlroot = ElementTree.fromstringlist(['<root>', f.read(), '</root>'])
            except ElementTree.ParseError as e:
                post('El archivo', xmlfile, 'no es válido:', str(e), kind=ec.cfgerr)
    except IOError:
        post('El archivo', xmlfile, 'no existe o no es legible', kind=ec.cfgerr)
    try:
        return xmlroot.find(element).text
    except AttributeError:
        raise


def loadconfig(xmlfile):

    try:
        with open(xmlfile) as f:
            try:
                xmlroot = ElementTree.fromstringlist(['<root>', f.read(), '</root>'])
            except ElementTree.ParseError as e:
                post('El archivo', xmlfile, 'no es válido:', str(e), kind=ec.cfgerr)
    except IOError:
        post('El archivo', xmlfile, 'no existe o no es legible', kind=ec.cfgerr)
    return XmlTreeBunch(xmlroot)


def parse_boolexpr(boolstring, context):

    TRUE = Keyword("True")
    FALSE = Keyword("False")
    boolOperand = TRUE | FALSE | Word(alphas, alphanums + '._-')
    boolOperand.setParseAction(lambda tokens: BoolOperand(tokens, context))
    # define expression, based on expression operand and
    # list of operations in precedence order
    boolExpr = infixNotation( boolOperand, [
        ("not", 1, opAssoc.RIGHT, BoolNot),
        ("and", 2, opAssoc.LEFT,  BoolAnd),
        ("or",  2, opAssoc.LEFT,  BoolOr),
    ])
    return bool(boolExpr.parseString(boolstring)[0])


#TODO: Move listings to utils.py
def readoptions(sysconf, jobconf, alias):

    parser = ArgumentParser(prog=alias, add_help=False)
    parser.add_argument('-l', '--list', dest='listonly', action='store_true', help='Lista las versiones de los programas y parámetros disponibles.')
    args = parser.parse_known_args()
    if args[0].listonly:
        if 'versionlist' in jobconf:
            print('Versiones disponibles:')
            for key in jobconf.versionlist:
                try: isdefault = key == jobconf.defaults.version
                except AttributeError: isdefault = False
                if isdefault:
                    print(' '*3 + key + ' ' + '(default)')
                else:
                    print(' '*3 + key)
        #TODO: fix parameterlist
        if 'parameterlist' in jobconf:
            print('Conjuntos de parámetros disponibles:')
            for key in jobconf.parameterlist:
                try: isdefault = key == jobconf.defaults.parameter
                except AttributeError: isdefault = False
                if isdefault:
                    print(' '*3 + key + ' ' + '(default)')
                else:
                    print(' '*3 + key)
        sys.exit(0)

    parser = ArgumentParser(prog=alias, description='Ejecuta trabajos de Gaussian, VASP, deMon2k, Orca y DFTB+ en sistemas PBS, LSF y Slurm.')
    parser.add_argument('-l', '--list', dest='listonly', action='store_true', help='Lista las versiones de los programas y conjuntos de parámetros disponibles.')
    parser.add_argument('-v', '--version', metavar = 'PROGVERSION', type=str, dest='version', help='Versión del ejecutable.')
    parser.add_argument('-p', '--parameter', metavar = 'PARAMETERSET', type=str, dest='parameter', help='Versión del conjunto de parámetros.')
    parser.add_argument('-q', '--queue', metavar = 'QUEUENAME', type=str, dest='queue', help='Nombre de la cola requerida.')
    parser.add_argument('-n', '--ncpu', metavar ='CPUCORES', type=int, dest='ncpu', default=1, help='Número de núcleos de procesador requeridos.')
    parser.add_argument('-N', '--nodes', metavar ='NODELIST', type=int, dest='nodes', help='Lista de los nodos requeridos.')
    parser.add_argument('-H', '--hostname', metavar = 'HOSTNAME', type=str, dest='exechost', help='Nombre del host requerido.')
    parser.add_argument('-s', '--scratch', metavar = 'SCRATCHDIR', type=str, dest='scratch', help='Directorio temporal de escritura.')
    parser.add_argument('-i', '--interactive', dest='interactive', action='store_true', help='Selección interactiva de las versiones de los programas y los parámetros.')
    parser.add_argument('-X', '--xdialog', dest='xdialog', action='store_true', help='Usar Xdialog en vez de la terminal para interactuar con el usuario.')
    parser.add_argument('-w', '--wait', metavar='WAITTIME', type=float, dest='waitime', help='Tiempo de pausa (en segundos) después de cada ejecución.')
    parser.add_argument('--sort', dest='sort', type=str, default='', help='Ordena la lista de argumentos en el orden especificado')
    parser.add_argument('--si', '--yes', dest='defaultanswer', action='store_true', default=None, help='Responder "si" a todas las preguntas.')
    parser.add_argument('--no', dest='defaultanswer', action='store_false', default=None, help='Responder "no" a todas las preguntas.')
    parser.add_argument('inputlist', nargs='+', metavar='INPUTFILE', help='Nombre del archivo de entrada.')

    options = Bunch()
    options.update(vars(parser.parse_args(args[1])))

    if not options.inputlist:
        post('Debe especificar al menos un archivo de entrada', kind=ec.opterr)

    try: sysconf.scheduler
    except AttributeError: post('No se especificó el nombre del sistema de colas (scheduler)', kind=ec.cfgerr)

    try: sysconf.storage
    except AttributeError: post('No se especificó el tipo de almacenamiento (storage)', kind=ec.cfgerr)

    if options.scratch is None:
        try: options.scratch = expandvars(sysconf.defaults.scratch)
        except AttributeError: post('No se especificó el directorio temporal de escritura por defecto (scratch)', kind=ec.cfgerr)

    if options.queue is None:
        try: options.queue = sysconf.defaults.queue
        except AttributeError: post('No se especificó la cola por defecto (queue)', kind=ec.cfgerr)

    if options.waitime is None:
        try: options.waitime = float(sysconf.defaults.waitime)
        except AttributeError: post('No se especificó el tiempo de pausa por defecto (waitime)', kind=ec.cfgerr)

    try: jobconf.outputdir = bool(util.strtobool(jobconf.outputdir))
    except AttributeError: post('No se especificó si se debe crear una carpeta de salida (outputdir)', kind=ec.cfgerr)
    except ValueError: post('El valor debe ser True or False (outputdir)', kind=ec.cfgerr)

    if options.interactive is True:
        jobconf.get('defaults', None)

    try: jobconf.runtype
    except AttributeError: post('No se especificó el tipo de paralelización del programa', kind=ec.cfgerr)

    if jobconf.runtype in ('intelmpi', 'openmpi', 'mpich'):
        try: jobconf.mpiwrapper = bool(util.strtobool(jobconf.mpiwrapper))
        except AttributeError: post('No se especificó ningún wrapper MPI (mpiwrapper)', kind=ec.cfgerr)
        except ValueError: post('El valor de debe ser True or False (mpiwrapper)', kind=ec.cfgerr)

    if 'versionlist' in jobconf:
        if len(jobconf.versionlist):
            if options.version is None:
                if 'defaults' in jobconf:
                    if 'version' in jobconf.defaults:
                        options.version = jobconf.defaults.version
                else:
                    choices = sorted(list(jobconf.versionlist))
                    options.version = prompt('Seleccione una versión', kind=pr.radio, choices=choices)
            try: jobconf.program = jobconf.versionlist[options.version]
            except KeyError as e: post('La versión seleccionada', quote(str(e.args[0])), 'no es válida', kind=ec.opterr)
            except TypeError: post('La lista de versiones está mal definida', kind=ec.cfgerr)
            try: jobconf.program.executable = expandvars(jobconf.program.executable)
            except AttributeError: post('No se especificó el ejecutable para la versión', options.version, kind=ec.cfgerr)
        else: post('La lista de versiones está vacía (versionlist)', kind=ec.cfgerr)
    else: post('No se definió ninguna lista de versiones (versionlist)', kind=ec.cfgerr)

    #TODO: Implement default parameter sets
    jobconf.parsets = [ ]
    for item in jobconf.get('parameteroot', []):
        itempath = realpath(expanduser(expandvars(item)))
        try:
            choices = sorted(listdir(itempath))
        except IOError:
            post('El directorio padre de parámetros', item, 'no existe o no es un directorio', kind=ec.cfgerr)
        if not choices:
            post('El directorio padre de parámetros', item, 'está vacío', kind=ec.cfgerr)
        if options.parameter is None:
            options.parameter = choices[0] if len(choices) == 1 else prompt('Seleccione un conjunto de parámetros', kind=pr.radio, choices=choices)
        jobconf.parsets.append(pathjoin(itempath, options.parameter))

    return options
