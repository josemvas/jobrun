import sys
assert sys.version_info >= (3, 3)
from clusterq import configure
try:
    configure.manage_packages()
except KeyboardInterrupt:
    print('No se completó la instalación')
