General
-------
- Usar srun/sbcast para correr trabajos multinodo con slurm
- Usar lsrun/lsrcp para correr trabajos multinodo con lsf/openlava
- Usar qrsh/??? para correr trabajos multinodo con pbs/torque
- Usar regexes en lugar de globs para listar los directorios de parámetros
- Usar el nombre del conjunto de parámetros en vez del nombre del directorio que contiene los archivos de parámetros
- Preguntar por la versión del programa y parámetros después de revisar que la carpeta de salida esté vacía, y usar esas opciones para todos los argumentos
- Mostrar errores apropiados cuando se intenten enviar multiples trabajos con la misma carpeta de salida
- Alertar cuando la configuracion exista y difiera de la configuracion actual
- Agregar soporte para ejecutar todos los archivos de entrada en el mismo trabajo (--chain?)
- Definir el esqueleto de las especificaciones para eliminar la necesidad de details.py
- Permitir leer los archivos de entrada de un directorio diferente al de salida y crear opción para eliminarlos
- Usar diccionarios de dos vias para agrupar mas facilmente las opciones
- Implementar una conexxiona maestra para todas las llamadas de ssh y rsync
- Mover names y paths a su propio modulo de espacio de nombres
- Usar el modulo runutils en vez de bulletin
- Usar JSON5 en los archivos de especificaciones
- Add suport for dialog boxes (-X/--xdialog option)
- Validar los valores de nhost/hosts antes de enviar el trabajo
- Mantener la carpeta de salida en el scratch si falla la copia al home
- Ignorar el known_hosts de los usuarios
- Trap para SIGINT y SIGTERM enviados por bkill
- Poner límite de memoria a los trabajos
- Agregar opción para imprimir la versión del script
- Determinar los conjuntos de parámetros a partir del filtro, por ejemplo: autodock --addpath=$HOME/docklib/{release}/ligands/{ligand} --addpath=$HOME/docklib/{release}/receptors/{receptor} --release 1.1 --ligand=%1.pdbqt --receptor=%2 --filter '([^_]+)_([^_]+)'
- Agregar en las especificaciones de los trabajos un diccionario con las condiciones lógicas de los archivos de entrada y el mensaje de error si no se cumplen
- Nombrar la carpeta oculta de jobscripts con el número de trabajo
- Agregar una opción para incluir la clave y versión del programa en los nombres de los archivos de salida
- Considerar usar template strings para interpolar las opciones y especificaciones

Python 3.6
----------
- dict conserva el orden de las entradas (ya no es necesario usar OrderedDict)
- Las bibliotecas pyjson5 requieren python 3.6
- Se pueden usar f-strings en vez de format

console.py
----------
- Usar diccionarios de dos vias para relacionar los nombres y las llaves de los archivos de specificaciones
- Usar un menú interactivo para seleccionar el scheduler (y todas las demás opciones de configuración)
- Mover hostspec.json y queuespec.json dentro del directorio jobspecs y eliminar los links dentro de las carpetas de programa
- Manejar los permisos denegados cuando se instalan los programas

queue.py
----------
- Preguntar si se lanza el trabajo en caso de error al consultar su estado
- Checar el error estandar ademas de la salida estandar aunque no haya error

AbsPath
------------------
- No aceptar listas de componentes de path como argumento
- Mover los métodos setkeys y validate de Abspath a joinpath
- Convertir los metodos parts y parent de AbsPath en atributos como en Pathlib
- No admitir componentes de ruta parcialmente interpolables

readspec.py
-----------
- Revisar el método merge de SpecList

run.py
------
- line 92: Manejar excepción cuando no está definida la ruta del conjunto de parámetros
