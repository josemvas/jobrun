# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import errno
from time import sleep
from termcolor import colored
from importlib import import_module
from os import path, listdir, remove, chmod
from os.path import dirname, basename, realpath
from job2q.utils import post
from job2q.utils import q
from job2q.utils import rmdir
from job2q.utils import remove
from job2q.utils import prompt
from job2q.utils import makedirs
from job2q.utils import pathjoin
from job2q.utils import copyfile
from job2q.parse import loadconfig
from job2q.parse import readoptions
from job2q.parse import getelement
from job2q.queue import queuejob
from job2q.classes import Bunch
from job2q.classes import ec, pr


def run(hostspecs, jobspecs):

    alias = basename(sys.argv[0])
    srcdir = dirname(realpath(__file__))

    #commonspecs = 
    userspecs = pathjoin(path.expanduser('~'), '.j2q', 'userspecs.xml')

    sysconf = Bunch()
    sysconf.update(loadconfig(hostspecs))

    #jobconf = Bunch(package=package)
    jobconf = Bunch()
    jobconf.update(loadconfig(jobspecs))

    if path.isfile(userspecs):
        jobconf.update(loadconfig(userspecs))

    scheduler = import_module('.schedulers.' + sysconf.scheduler, package='job2q')

    options = readoptions(sysconf, jobconf, alias)

    if 'r' in options.sort:
        options.inputlist.sort(reverse=True)

    try:
        queuejob(sysconf, jobconf, options, scheduler, options.inputlist.pop(0))
        for inputfile in options.inputlist:
            sleep(options.waitime)
            queuejob(sysconf, jobconf, options, scheduler, inputfile)
    except KeyboardInterrupt:
        sys.exit(colored('Cancelado por el usario', 'red'))


def setup():

    srcdir = dirname(realpath(__file__))
    genericdir = pathjoin(srcdir, 'database', 'generic')
    platformdir = pathjoin(srcdir, 'database', 'platform')
    specdir = pathjoin(dirname(dirname(sys.argv[0])), 'etc', 'j2q')

    host = prompt('Seleccione la opción con la arquitectura más adecuada', kind=pr.radio, choices=sorted(listdir(platformdir)))

    if not path.isfile(pathjoin(platformdir, host, 'hostspecs.xml')):
        post('El archivo de configuración de la plataforma', q(host), 'no existe', kind=ec.cfgerr)

    if path.isfile(pathjoin(specdir, 'hostspecs.xml')):
        if prompt('El sistema ya está configurado, ¿quiere reinstalar la configuración por defecto (si/no)?', kind=pr.ok):
            copyfile(pathjoin(platformdir, host, 'hostspecs.xml'), pathjoin(specdir, 'hostspecs.xml'))
    else:
        makedirs(specdir)
        copyfile(pathjoin(platformdir, host, 'hostspecs.xml'), pathjoin(specdir, 'hostspecs.xml'))
         
    available = { }
    configured = [ ]

    for package in listdir(pathjoin(platformdir, host)):
        if path.isdir(pathjoin(platformdir, host, package)):
            try:
                title = getelement(pathjoin(genericdir, package, 'jobspecs.xml'), 'title')
            except AttributeError:
                post('El archivo', pathjoin(genericdir, package, 'jobspecs.xml'), 'no tiene un título', kind=ec.cfgerr)
            available[title] = package
            if path.isfile(pathjoin(specdir, package, 'jobspecs.xml')):
                configured.append(title)

    packagelist = list(available)

    if not packagelist:
        post('No hay paquetes configurados para este host', kind=ec.warning)
        return

    selected = prompt('Marque los paquetes que desea configurar o reconfigurar', kind=pr.check, choices=packagelist, precheck=configured)

    for package in selected:
        makedirs(pathjoin(specdir, available[package]))
        with open(pathjoin(specdir, available[package], 'jobspecs.xml'), 'w') as ofh:
            with open(pathjoin(genericdir, available[package], 'jobspecs.xml')) as ifh:
                ofh.write(ifh.read())
            with open(pathjoin(platformdir, host, available[package], 'jobspecs.xml')) as ifh:
                ofh.write(ifh.read())

    bindir = path.expanduser(prompt('Especifique la ruta donde se instalarán los enlaces de los paquetes configurados (ENTER para instalar en ./bin)', kind=pr.path, enter='./bin'))

    makedirs(bindir)
    with open(pathjoin(srcdir, 'exec.py.str')) as fh:
        pyrun = fh.read()
    #environ = { k : os.environ[k] for k in ('PATH', 'LD_LIBRARY_PATH') }
    for package in listdir(specdir):
        if path.isfile(pathjoin(specdir, package, 'jobspecs.xml')):
            try:
                with open(pathjoin(bindir, package), 'w') as fh:
                    fh.write(pyrun.format(version=tuple(sys.version_info), python=sys.executable, syspath=sys.path, hostspecs=pathjoin(specdir, 'hostspecs.xml'), jobspecs=pathjoin(specdir, package, 'jobspecs.xml')))
            except IOError as e:
                post('Se produjo el siguiente error al intentar instalar un enlace:', e, kind=runerror)
            else:
                chmod(pathjoin(bindir, package), 0o755)
