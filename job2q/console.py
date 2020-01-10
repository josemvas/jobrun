# -*- coding: utf-8 -*-

def setup():

    import sys
    from os import path, listdir, chmod
    from shutil import copyfile
    from . import dialogs
    from . import messages
    from .utils import rmdir, makedirs, hardlink, realpath
    from .readspec import readspec
    
    main_template = '''
#!{python}
# -*- coding: utf-8 -*-
import sys
from os import path
sys.path = {syspath}
from job2q import submit
submit.submit()
while submit.inputlist:
    submit.wait()
    submit.submit()
'''
    
    bindir = dialogs.path('Escriba la ruta donde se instalarán los ejecutables')
    etcdir = dialogs.path('Escriba la ruta donde se instalará la configuración')

    sourcedir = path.dirname(path.realpath(__file__))
    corespecdir = path.join(sourcedir, 'specdata', 'corespecs')
    platformdir = path.join(sourcedir, 'specdata', 'platforms')

    hostname = dialogs.optone('Seleccione la opción con la arquitectura más adecuada', choices=sorted(listdir(platformdir), key=str.casefold))

    if not path.isfile(path.join(platformdir, hostname, 'platform.xml')):
        messages.cfgerr('El archivo de configuración del host', hostname, 'no existe')

    if etcdir and path.isdir(etcdir):
        specdir = path.join(etcdir, 'j2q')
        if path.isfile(path.join(specdir, 'platform.xml')):
            if dialogs.yesno('El sistema ya está configurado, ¿quiere reestablecer la configuración por defecto?'):
                copyfile(path.join(platformdir, hostname, 'platform.xml'), path.join(specdir, 'platform.xml'))
        else:
            makedirs(specdir)
            copyfile(path.join(platformdir, hostname, 'platform.xml'), path.join(specdir, 'platform.xml'))
             
        available = { }
        configured = [ ]
    
        for package in listdir(path.join(platformdir, hostname)):
            if path.isdir(path.join(platformdir, hostname, package)):
                pkgname = readspec(path.join(corespecdir, package, 'corespec.xml'), 'pkgname')
                if pkgname is None:
                    messages.cfgerr('El archivo', path.join(corespecdir, package, 'corespec.xml'), 'no tiene un título')
                available[pkgname] = package
                if path.isdir(path.join(specdir, package)):
                    configured.append(pkgname)
    
        packagelist = list(available)
    
        if not packagelist:
            messages.warning('No hay paquetes configurados para este host')
            return
    
        selected = dialogs.optany('Seleccione los paquetes que desea configurar o reconfigurar', choices=sorted(packagelist, key=str.casefold), default=configured)

        if set(selected).isdisjoint(configured) or dialogs.yesno('Algunos de los paquetes seleccionados ya están configurados, ¿está seguro que quiere restablecer sus configuraciones por defecto?'):
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
                        syspath=sys.path + [path.join(specdir, package)],
                        specdir=path.join(specdir, package)))
                chmod(path.join(bindir, package), 0o755)

def xdialog():

    from argparse import ArgumentParser
    from .tkboxes import listbox

    parser = ArgumentParser(description='Crea un cuadro de diálogo con una lista de opciones.')
    parser.add_argument('-o', '--option', metavar=('DESCRIPCIÓN', 'COMANDO'), dest='options', action='append', nargs=2, help='Agregar opción a la lista de opciones')
    parser.add_argument('message', metavar='MENSAJE', type=str, help='Mensaje del cuadro de diálogo.')
    arguments = parser.parse_args()
    choice = listbox(arguments.message, choices=[i for i,j in arguments.options])
    if choice is not None:
         print(dict(arguments.options)[choice])
    
