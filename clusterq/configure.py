import os
import sys
import re
from string import Template
from subprocess import check_output, DEVNULL
from clinterface import messages, prompts
from .readspec import readspec
from .fileutils import AbsPath, pathjoin, mkdir, copyfile, symlink

selector = prompts.Selector()
completer = prompts.Completer()

def manage_packages():

    pylibs = []
    syslibs = []
    packagelist = []
    packagenames = {}
    enabledpackages = []

    srcdir = AbsPath(__file__).parent

    completer.set_message('Escriba la ruta donde se instalarán los programas')
    rootdir = AbsPath(completer.directory_path(), cwd=os.getcwd())

    bindir = pathjoin(rootdir, 'bin')
    etcdir = pathjoin(rootdir, 'etc')
    cfgdir = pathjoin(rootdir, 'etc', 'clusterq')

    mkdir(bindir)
    mkdir(etcdir)
    mkdir(cfgdir)

    mkdir(pathjoin(cfgdir, 'cluster'))
    mkdir(pathjoin(cfgdir, 'packages'))

    if not os.path.isfile(pathjoin(cfgdir, 'config.json')):
        messages.warning('Aún no se ha configurado el clúster')

    for line in check_output(('ldconfig', '-Nv'), stderr=DEVNULL).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'(\S+):', line)
        if match and match.group(1) not in syslibs:
            syslibs.append(match.group(1))

    for line in check_output(('ldd', sys.executable)).decode(sys.stdout.encoding).splitlines():
        match = re.fullmatch(r'\s*\S+\s+=>\s+(\S+)\s+\(\S+\)', line)
        if match:
            libdir = os.path.dirname(match.group(1))
            if libdir not in syslibs:
                pylibs.append(libdir)

    installation = dict(
        python = sys.executable,
        libpath = os.pathsep.join(pylibs),
        moduledir = os.path.dirname(srcdir),
        cfgdir = cfgdir,
    )

    with open(pathjoin(srcdir, 'templates', 'scripts', 'submit.sh'), 'r') as r, open(pathjoin(cfgdir, 'submit.sh'), 'w') as w:
        w.write(Template(r.read()).substitute(installation))

    os.chmod(pathjoin(cfgdir, 'submit.sh'), 0o755)

    for diritem in os.listdir(pathjoin(cfgdir, 'packages')):
        displayname = readspec(pathjoin(cfgdir, 'packages', diritem, 'config.json')).displayname
        packagelist.append(diritem)
        packagenames[diritem] = displayname

    for diritem in os.listdir(bindir):
        if os.path.islink(pathjoin(bindir, diritem)):
            if os.readlink(pathjoin(bindir, diritem)) == pathjoin(cfgdir, 'submit.sh'):
                enabledpackages.append(diritem)

    if packagelist:
        selector.set_message('Seleccione los programas que desea activar/desactivar')
        selector.set_options(packagenames)
        selector.set_multiple_defaults(enabledpackages)
        selpackages = selector.multiple_choices()
    else:
        messages.warning('No hay ningún programa configurado todavía')

    for package in enabledpackages:
        os.remove(pathjoin(bindir, package))

    for package in packagelist:
        if package in selpackages:
            symlink(pathjoin(cfgdir, 'submit.sh'), pathjoin(bindir, package))


def configure_cluster():

    clusterkeys = {}
    clusternames = {}
    defaultschedulers = {}
    schedulerkeys = {}
    schedulernames = {}

    for diritem in os.listdir(pathjoin(srcdir, 'templates', 'hosts')):
        if not os.path.isfile(pathjoin(srcdir, 'templates', 'hosts', diritem, 'cluster', 'config.json')):
            messages.warning('El directorio', diritem, 'no contiene ningún archivo de configuración')
        clusterconf = readspec(pathjoin(srcdir, 'templates', 'hosts', diritem, 'cluster', 'config.json'))
        clusternames[diritem] = clusterconf.clustername
        clusterkeys[clusterconf.clustername] = diritem
        defaultschedulers[diritem] = clusterconf.scheduler

    for diritem in os.listdir(pathjoin(srcdir, 'schedulers')):
        scheduler = readspec(pathjoin(srcdir, 'schedulers', diritem, 'config.json')).scheduler
        schedulernames[diritem] = scheduler
        schedulerkeys[scheduler] = diritem

    if os.path.isfile(pathjoin(cfgdir, 'cluster', 'config.json')):
        selector.set_message('¿Qué clúster desea configurar?')
        selector.set_options(clusternames)
        clusterconf = readspec(pathjoin(cfgdir, 'cluster', 'config.json'))
        if clusterconf.clustername in clusternames.values():
            selector.set_single_default(clusterkeys[clusterconf.clustername])
        selcluster = selector.single_choice()
        if selcluster != clusterkeys[clusterconf.clustername]:
            if readspec(pathjoin(srcdir, 'templates', 'hosts', selcluster, 'cluster', 'config.json')) != readspec(pathjoin(cfgdir, 'cluster', 'config.json')):
                completer.set_message('Desea sobreescribir la configuración local del sistema?')
                completer.set_truthy_options(['si', 'yes'])
                completer.set_falsy_options(['no'])
                if completer.binary_choice():
                    copyfile(pathjoin(srcdir, 'templates', 'hosts', selcluster, 'cluster', 'config.json'), pathjoin(cfgdir, 'cluster', 'config.json'))
        selector.set_message('Seleccione el gestor de trabajos adecuado')
        selector.set_options(schedulernames)
        selector.set_single_default(schedulerkeys[clusterconf.scheduler])
        selscheduler = selector.single_choice()
        copyfile(pathjoin(srcdir, 'schedulers', selscheduler, 'config.json'), pathjoin(cfgdir, 'config.json'))
    else:
        selector.set_message('¿Qué clúster desea configurar?')
        selector.set_options(clusternames)
        selcluster = selector.single_choice()
        copyfile(pathjoin(srcdir, 'templates', 'hosts', selcluster, 'cluster', 'config.json'), pathjoin(cfgdir, 'cluster', 'config.json'))
        selector.set_message('Seleccione el gestor de trabajos adecuado')
        selector.set_options(schedulernames)
        selector.set_single_default(selcluster)
        selscheduler = selector.single_choice()
        copyfile(pathjoin(srcdir, 'schedulers', selscheduler, 'config.json'), pathjoin(cfgdir, 'config.json'))
