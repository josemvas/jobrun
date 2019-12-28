# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys
import errno
from time import sleep
from importlib import import_module
from os import path, listdir, remove, chmod
from os.path import dirname, basename, realpath

from job2q.classes import Bunch
from job2q.utils import rmdir, remove, makedirs, copyfile, pathjoin, pathexpand
from job2q.parsing import loadconfig, readoptions, getelement
from job2q.dialogs import messages, dialogs
from job2q.queue import queuejob


def run(hostspecs, jobspecs):

    alias = basename(sys.argv[0])
    srcdir = dirname(realpath(__file__))

    #WTF!
    #TODO: commonspecs = ??? 
    userspecs = pathjoin(path.expanduser('~'), '.j2q', 'userspecs.xml')

    sysconf = Bunch(initscript=[], offscript=[])
    sysconf.update(loadconfig(hostspecs))

    jobconf = Bunch(defaults={}, versions={}, parameters=[], filevars=[], prescript=[], postscript=[])
    jobconf.update(loadconfig(jobspecs))

    if path.isfile(userspecs):
        jobconf.update(loadconfig(userspecs))

    scheduler = import_module('.schedulers.' + sysconf.scheduler, package='job2q')

    options = readoptions(sysconf, jobconf, alias)

    #TODO: Sort in alphabetical or numerical order
    if 'r' in options.sort:
        options.inputlist.sort(reverse=True)

    try:
        queuejob(sysconf, jobconf, options, scheduler, options.inputlist.pop(0))
        for inputfile in options.inputlist:
            sleep(options.waitime)
            queuejob(sysconf, jobconf, options, scheduler, inputfile)
    except KeyboardInterrupt:
        dialogs.runerr('Cancelado por el usario')


def setup(**kwargs):

    srcdir = dirname(realpath(__file__))
    genericdir = pathjoin(srcdir, 'database', 'generic')
    platformdir = pathjoin(srcdir, 'database', 'platform')

    cfgdir = kwargs['cfgdir'] if 'cfgdir' in kwargs else dialogs.path('Escriba la ruta donde se instalará la configuración (o deje vacío para omitir)')
    bindir = kwargs['bindir'] if 'bindir' in kwargs else dialogs.path('Escriba la ruta donde se instalarán los scripts configurados (o deje vacío para omitir)')
    hostname = kwargs['hostname'] if 'hostname' in kwargs else dialogs.optone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(listdir(platformdir)))

    if not path.isfile(pathjoin(platformdir, hostname, 'hostspecs.xml')):
        messages.cfgerr('El archivo de configuración del host', hostname, 'no existe')

    if cfgdir and os.path.isdir(cfgdir):
        specdir = pathjoin(cfgdir, 'j2q')
        if path.isfile(pathjoin(specdir, 'hostspecs.xml')):
            if dialogs.yesno('El sistema ya está configurado, ¿quiere reestablecer la configuración por defecto (si/no)?'):
                copyfile(pathjoin(platformdir, hostname, 'hostspecs.xml'), pathjoin(specdir, 'hostspecs.xml'))
        else:
            makedirs(specdir)
            copyfile(pathjoin(platformdir, hostname, 'hostspecs.xml'), pathjoin(specdir, 'hostspecs.xml'))
             
        available = { }
        configured = [ ]
    
        for package in listdir(pathjoin(platformdir, hostname)):
            if path.isdir(pathjoin(platformdir, hostname, package)):
                try:
                    title = getelement(pathjoin(genericdir, package, 'jobspecs.xml'), 'title')
                except AttributeError:
                    messages.cfgerr('El archivo', pathjoin(genericdir, package, 'jobspecs.xml'), 'no tiene un título')
                available[title] = package
                if path.isfile(pathjoin(specdir, package, 'jobspecs.xml')):
                    configured.append(title)
    
        packagelist = list(available)
    
        if not packagelist:
            messages.warning('No hay paquetes configurados para este host')
            return
    
        selected = dialogs.optany('Seleccione los paquetes que desea configurar o reconfigurar', choices=packagelist, default=configured)
        if not set(selected) & set(configured) or dialogs.yesno('Algunos de los paquetes seleccionados ya están configurados, ¿está seguro que quiere restablecer sus configuraciones por defecto (si/no)?'):
            for package in selected:
                makedirs(pathjoin(specdir, available[package]))
                with open(pathjoin(specdir, available[package], 'jobspecs.xml'), 'w') as ofh:
                    with open(pathjoin(genericdir, available[package], 'jobspecs.xml')) as ifh:
                        ofh.write(ifh.read())
                    with open(pathjoin(platformdir, hostname, available[package], 'jobspecs.xml')) as ifh:
                        ofh.write(ifh.read())

    if bindir and os.path.isdir(bindir):
        with open(pathjoin(srcdir, 'strings', 'exec.py.str')) as fh:
            pyrun = fh.read()
        #environ = { k : os.environ[k] for k in ('PATH', 'LD_LIBRARY_PATH') }
        for package in listdir(specdir):
            if path.isfile(pathjoin(specdir, package, 'jobspecs.xml')):
                try:
                    with open(pathjoin(bindir, package), 'w') as fh:
                        fh.write(pyrun.format(version=tuple(sys.version_info), python=sys.executable, syspath=sys.path, hostspecs=pathjoin(specdir, 'hostspecs.xml'), jobspecs=pathjoin(specdir, package, 'jobspecs.xml')))
                except IOError as e:
                    messages.runerr('Se produjo el siguiente error al intentar instalar un enlace:', e)
                else:
                    chmod(pathjoin(bindir, package), 0o755)
