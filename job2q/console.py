# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys
from os import path, listdir, chmod
from shutil import copyfile

from job2q import dialogs
from job2q import messages
from job2q.utils import rmdir, makedirs, hardlink, realpath
from job2q.readspec import readspec

main_template = '''
#!{python}
# -*- coding: utf-8 -*-
import sys
from os import path
sys.path = {syspath}
sys.argv[0] = path.join('{specdir}', path.basename(sys.argv[0]))
from job2q import submit
submit.submit()
while submit.inputlist:
    submit.wait()
    submit.submit()
'''

def setup():

    bindir = dialogs.path('Escriba la ruta donde se instalarán los ejecutables')
    etcdir = dialogs.path('Escriba la ruta donde se instalará la configuración')

    sourcedir = path.dirname(path.realpath(__file__))
    corespecdir = path.join(sourcedir, 'specdata', 'corespec')
    platformdir = path.join(sourcedir, 'specdata', 'platform')

    hostname = dialogs.optone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(listdir(platformdir)))

    if not path.isfile(path.join(platformdir, hostname, 'platform.xml')):
        messages.cfgerr('El archivo de configuración del host', hostname, 'no existe')

    if etcdir and path.isdir(etcdir):
        specdir = path.join(etcdir, 'j2q')
        if path.isfile(path.join(specdir, 'platform.xml')):
            if dialogs.yesno('El sistema ya está configurado, ¿quiere reestablecer la configuración por defecto (si/no)?'):
                copyfile(path.join(platformdir, hostname, 'platform.xml'), path.join(specdir, 'platform.xml'))
        else:
            makedirs(specdir)
            copyfile(path.join(platformdir, hostname, 'platform.xml'), path.join(specdir, 'platform.xml'))
             
        available = { }
        configured = [ ]
    
        for package in listdir(path.join(platformdir, hostname)):
            if path.isdir(path.join(platformdir, hostname, package)):
                packagename = readspec(path.join(corespecdir, package, 'corespec.xml'), 'packagename')
                if packagename is None:
                    messages.cfgerr('El archivo', path.join(corespecdir, package, 'corespec.xml'), 'no tiene un título')
                available[packagename] = package
                if path.isdir(path.join(specdir, package)):
                    configured.append(packagename)
    
        packagelist = list(available)
    
        if not packagelist:
            messages.warning('No hay paquetes configurados para este host')
            return
    
        selected = dialogs.optany('Seleccione los paquetes que desea configurar o reconfigurar', choices=packagelist, default=configured)

        if set(selected).isdisjoint(configured) or dialogs.yesno('Algunos de los paquetes seleccionados ya están configurados, ¿está seguro que quiere restablecer sus configuraciones por defecto (si/no)?'):
            for package in selected:
                makedirs(path.join(specdir, available[package]))
                hardlink(path.join(specdir, 'platform.xml'), path.join(specdir, available[package], 'platform.xml'))
                copyfile(path.join(corespecdir, available[package], 'corespec.xml'), path.join(specdir, available[package], 'corespec.xml'))
                copyfile(path.join(platformdir, hostname, available[package], 'hostspec.xml'), path.join(specdir, available[package], 'hostspec.xml'))

    if bindir and path.isdir(bindir):
        for package in listdir(specdir):
            if path.isdir(path.join(specdir, package)):
                with open(path.join(bindir, package), 'w') as fh:
                    fh.write(main_template.lstrip('\n').format(
                        version=tuple(sys.version_info),
                        python=sys.executable,
                        syspath=sys.path,
                        specdir=path.join(specdir, package)))
                chmod(path.join(bindir, package), 0o755)
