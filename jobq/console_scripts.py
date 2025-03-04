import os
import sys
import re
import json
from string import Template
from argparse import ArgumentParser
from clinterface import messages, prompts, _
from subprocess import check_output, DEVNULL
from .fileutils import AbsPath
from .json5 import json5_load
from .utils import ConfDict

selector = prompts.Selector()
completer = prompts.Completer()
completer.set_truthy_options(['si', 'yes'])
completer.set_falsy_options(['no'])

def config():
    parser = ArgumentParser(description="Herramienta de configuración.")
    subparsers = parser.add_subparsers(dest="command", help="Subcomando a ejecutar")
    setup_parser = subparsers.add_parser("setup", help="Carga un archivo de configuración existente")
    reload_parser = subparsers.add_parser("reload", help="Carga un archivo de configuración existente")
    new_parser = subparsers.add_parser("write", help="Crea un nuevo archivo de configuración")
    args = parser.parse_args()

    if args.command == 'setup':
        config_setup()
    elif args.command == 'reload':
        config_reload()
    elif args.command == 'write':
        config_write()
    else:
        messages.error(_('$command no es un subcomando válido', command=args.command))

def config_write():
    messages.error(_('config_write no ha sido implementado todavía'))

def config_reload():
    messages.error(_('config_reload no ha sido implementado todavía'))

def config_setup():
    packagelist = []
    enabled_packages = []
    packagenames = {}

    execdir = AbsPath(sys.argv[0]).parent()
    packagedir = AbsPath(__file__).parent()
    site_packages = AbsPath(__file__).parent().parent()

    completer.set_message(_('Escriba la ruta del directorio de configuración:'))
    confdir = AbsPath(completer.directory_path(), parent=os.getcwd())

    if not (confdir).isdir():
        messages.error(_('$confdir does not exist or is not a directory', confdir=confdir))

    if not (confdir/'packages').isdir():
        messages.error(_('$confdir/packages does not exist or is not a directory', confdir=confdir))

    if not (confdir/'cluster.json').isfile():
        messages.error(_('$confdir/cluster.json does not exist or is not a file', confdir=confdir))

#    (confdir/'specfiles').mkdir()
#    (confdir/'specfiles'/'packages').mkdir()
#    (confdir/'specfiles'/'schedulers').mkdir()
#    for specfile in (packagedir/'specfiles'/'packages').listdir():
#        if (confdir/'specfiles'/'packages'/specfile).isfile():
#            if json5_load(packagedir/'specfiles'/'packages'/specfile) != json5_load(confdir/'specfiles'/'packages'/specfile):
#                completer.set_message(_('¿Desea sobrescribir la configuración local del programa $progname?', progname=specfile))
#                if completer.binary_choice():
#                    (packagedir/'specfiles'/'packages'/specfile).copyto(confdir/'specfiles'/'packages')
#        else:
#            (packagedir/'specfiles'/'packages'/specfile).copyto(confdir/'specfiles'/'packages')
#    for specfile in (packagedir/'specfiles'/'schedulers').listdir():
#        if (confdir/'specfiles'/'schedulers'/specfile).isfile():
#            if json5_load(packagedir/'specfiles'/'schedulers'/specfile) != json5_load(confdir/'specfiles'/'schedulers'/specfile):
#                completer.set_message(_('¿Desea sobrescribir la configuración local del gestor de trabajos $queuename?', queuename=specfile))
#                if completer.binary_choice():
#                    (packagedir/'specfiles'/'schedulers'/specfile).copyto(confdir/'specfiles'/'schedulers')
#        else:
#            (packagedir/'specfiles'/'schedulers'/specfile).copyto(confdir/'specfiles'/'schedulers')

    for profile in (confdir/'packages').listdir():
        specdict = json5_load(confdir/'packages'/profile)
        if 'packagename' in specdict:
            name = os.path.splitext(profile)[0]
            packagelist.append(name)
            packagenames[name] = specdict['packagename']

    for package in packagelist:
        if (execdir/package).isfile():
            enabled_packages.append(package)

    if packagelist:
        selector.set_message(_('Seleccione los programas que desea activar/desactivar:'))
        selector.set_options(packagenames)
        selector.set_multiple_defaults(enabled_packages)
        selected_packages = selector.multiple_choices()
    else:
        messages.warning(_('No hay ningún programa configurado todavía'))

#    systemlibs = set()
#    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
#        match = re.fullmatch(r'(\S+):', line)
#        if match:
#            systemlibs.add(match.group(1))
#    pythonlibs = set()
#    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
#        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
#        if match:
#            lib = AbsPath(match.group(1)).parent()
#            if lib not in systemlibs:
#                pythonlibs.add(lib)

    for package in packagelist:
        config = ConfDict(dict(
            load = [],
            source = [],
            export = {},
            versions = {},
            defaults = {},
            conflicts = {},
            optargs = [],
            posargs = [],
            filekeys = {},
            filevars = {},
            fileopts = {},
            inputfiles = [],
            outputfiles = [],
            ignorederrors = [],
            parameteropts = [],
            parameterpaths = [],
            interpolable = [],
            interpolopts = [],
            prescript = [],
            postscript = [],
            onscript = [],
            offscript = [],
        ))
        config.update(json5_load(confdir/'cluster.json'))
        config.update(json5_load(confdir/'packages'/package-'json'))
        config.update(json5_load(packagedir/'specfiles'/'schedulers'/config.schedspecfile))
        config.update(json5_load(packagedir/'specfiles'/'packages'/config.progspecfile))
        dumping = json.dumps(config)
        if (execdir/package).isfile():
            (execdir/package).remove()
        if package in selected_packages:
            with open(execdir/package, 'w') as file:
                file.write(f'#!{sys.executable}\n')
                file.write('import sys\n')
                file.write('from jobq import main\n')
                file.write('sys.path.append(\n')
                file.write(f"r'{site_packages}'\n")
                file.write(')\n')
                file.write('main.submit_jobs(\n')
                file.write(f"r'''{dumping}'''\n")
                file.write(')\n')
            (execdir/package).chmod(0o755)
