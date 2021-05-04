import sys
assert sys.version_info >= (3, 4)
from job2q import colors
from job2q import console
try:
    console.install()
except KeyboardInterrupt:
    print(colors.red + 'No se completó la instalación' + colors.default)
