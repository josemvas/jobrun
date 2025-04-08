import sys
import re
import json
from os.path import abspath
from string import Template
from argparse import ArgumentParser
from clinterface import messages, prompts, _
from subprocess import check_output, DEVNULL
from .fileutils import AbsPath
from .json5 import json5_load
from .utils import ConfDict

install_dir = AbsPath(abspath(sys.argv[0])).parent()
package_dir = AbsPath(__file__).parent()
site_packages_dir = AbsPath(__file__).parent().parent()
package_data = site_packages_dir/package_dir.name%'dat'
selector = prompts.Selector()
completer = prompts.Completer()
truthy_options = ['si', 'yes']
falsy_options = ['no']

def config():
    parser = ArgumentParser(description='Herramienta de configuración.')
    subparsers = parser.add_subparsers()
    setup_parser = subparsers.add_parser('setup')
    install_parser = subparsers.add_parser('rebuild')
    setup_parser.set_defaults(command=setup)
    install_parser.set_defaults(command=rebuild)
    args = parser.parse_args()
    args.command()

def setup():
    prompt = _('Escriba la ruta del directorio de configuración:')
    config_dir = AbsPath(completer.directory_path(prompt))
    with open(package_data, 'w') as f:
        f.write(config_dir)
    if config_dir.exists():
        read_config(config_dir)
    else:
        write_config(config_dir)

def rebuild():
    with open(package_data, 'r') as f:
        config_dir = AbsPath(f.read())
    read_config(config_dir)

def write_config(config_dir):
    messages.error(_('write_config no está implementado aún'))

def read_config(config_dir):
    package_names = {}
    executable_names = {}
    enabled_packages = []

    if not (config_dir).isdir():
        messages.error(_('$config_dir does not exist or is not a directory'), config_dir=config_dir)

    if not (config_dir/'package_profiles').isdir():
        messages.error(_('$config_dir/package_profiles does not exist or is not a directory'), config_dir=config_dir)

    if not (config_dir/'cluster_profile.json').isfile():
        messages.error(_('$config_dir/cluster_profile.json does not exist or is not a file'), config_dir=config_dir)

#    (config_dir/'specfiles').mkdir()
#    (config_dir/'specfiles'/'package_specs').mkdir()
#    (config_dir/'specfiles'/'scheduler_specs').mkdir()
#    for specfile in (package_dir/'specfiles'/'package_specs').listdir():
#        if (config_dir/'specfiles'/'package_specs'/specfile).isfile():
#            if json5_load(package_dir/'specfiles'/'package_specs'/specfile) != json5_load(config_dir/'specfiles'/'package_specs'/specfile):
#                prompt = _('¿Desea sobrescribir el archivo de configuración $specfile?', specfile=specfile)
#                if completer.binary_choice(prompt, truthy_options, falsy_options):
#                    (package_dir/'specfiles'/'package_specs'/specfile).copyto(config_dir/'specfiles'/'package_specs')
#        else:
#            (package_dir/'specfiles'/'package_specs'/specfile).copyto(config_dir/'specfiles'/'package_specs')
#    for specfile in (package_dir/'specfiles'/'scheduler_specs').listdir():
#        if (config_dir/'specfiles'/'scheduler_specs'/specfile).isfile():
#            if json5_load(package_dir/'specfiles'/'scheduler_specs'/specfile) != json5_load(config_dir/'specfiles'/'scheduler_specs'/specfile):
#                prompt = _('¿Desea sobrescribir la configuración local del gestor de trabajos $queuename?', queuename=specfile)
#                if completer.binary_choice(prompt, truthy_options, falsy_options):
#                    (package_dir/'specfiles'/'scheduler_specs'/specfile).copyto(config_dir/'specfiles'/'scheduler_specs')
#        else:
#            (package_dir/'specfiles'/'scheduler_specs'/specfile).copyto(config_dir/'specfiles'/'scheduler_specs')

    for profile in (config_dir/'package_profiles').listdir():
        specdict = json5_load(config_dir/'package_profiles'/profile)
        if 'packagename' in specdict:
            package_names[profile] = specdict['packagename']
            executable_names[profile] = specdict['executablename']

    for package in package_names:
        if (install_dir/executable_names[package]).isfile():
            enabled_packages.append(package)

    if package_names:
        prompt = _('Seleccione los programas que desea instalar/desinstalar:')
        selected_packages = selector.multiple_choices(prompt, package_names, enabled_packages)
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

    for package in package_names:
        if (install_dir/package).isfile():
            (install_dir/package).remove()
        if package in selected_packages:
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
            config.update(json5_load(config_dir/'cluster_profile.json'))
            config.update(json5_load(config_dir/'package_profiles'/package))
            config.update(json5_load(package_dir/'specfiles'/'scheduler_specs'/config.schedspecfile))
            config.update(json5_load(package_dir/'specfiles'/'package_specs'/config.progspecfile))
            dumping = json.dumps(config)
            with open(install_dir/executable_names[package], 'w') as file:
                file.write(f'#!{sys.executable}\n')
                file.write('import sys\n')
                file.write('from jobq import main\n')
                file.write('sys.path.append(\n')
                file.write(f"r'{site_packages_dir}'\n")
                file.write(')\n')
                file.write('main.submit_jobs(\n')
                file.write(f"r'''{dumping}'''\n")
                file.write(')\n')
            (install_dir/executable_names[package]).chmod(0o755)
