import sys
assert sys.version_info >= (3, 3)
from clusterq import scripts
try:
    scripts.setup()
except KeyboardInterrupt:
    print('No se completó la instalación')
