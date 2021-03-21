General
-------
- Move sysinfo attributes to hostspecs
- Add suport for dialog boxes (-X/--xdialog option)
- Restringir los valores permitidos de nhost/hosts
- Usar "template strings" en vez de "format strings" para las interpolaciones
- Mantener la carpeta de salida en el scratch si falla la copia al home
- Ignorar el known_hosts de los usuarios
- Trap para SIGINT y SIGTERM enviados por bkill
- Poner límite de memoria a los trabajos
- Agregar opción para imprimir la versión del programa
- Cambiar el mecanisno de generación de comentarios BSUB/SBATCH/PBS para soportar TORQUE (problemas con nodes/nproc/nhost)
- Terminar la reescritura para la ejecucion remota de trabajos (falta copiar molfile, realfiles)
- Agregar opción para incluir la clave y versión del programa en los nombres de los archivos de salida
- Presentar la lista de parámetros una sola vez (o no preguntar si hay default o se obtienen del filtro)
- Permitir obntener los conjuntos de parámetros del filtro e independizar las rutas de parámetros de los conjuntos de parámetros, por ejemplo: autodock --addpath=$HOME/autodock/{version}/ligands/{ligand}.pdbqt --addpath=$HOME/autodock/{version}/receptors/{receptor} --version 1.1 --ligand=%1 --receptor=%2 --filter '([^_]+)_([^_]+)'
- Considerar quitar el operador '|' de las especificaciones de los archivos de entrada y salida
- Agregar en las especificaciones de los trabajos un diccionario con las condiciones lógicas de los archivos de entrada y el mensaje de error si no se cumplen

console.py
----------
- Seleccionar el scheduler interactivamente
- Listar la opción "Nuevo" siempre al principio
- Mover hostspec.json y queuespec.json dentro del directorio jobspecs y eliminar los links dentro de las carpetas de programa
- Manejar permisos denegados cuando se instalan los programas

queue.py
----------
- Preguntar si se lanza el trabajo en caso de error al consultar su estado
- Checar el error estandar ademas de la salida estandar cuando no hay error

AbsPath
-------
- Considerar no aceptar listas de componentes de path como argumento (usar el método joinpath en su lugar)
- Considerar reemplazar método stekeys con la opción keys= y aceptar listas además de diccionarios para interpolar
- Change slash by comma to set interpolable path components with setkeys

jobsync
-------
- List redundant files with less and ask only once to delete

readspec.py
-----------
- Revisar el método merge de SpecList porque no puede ser igual que el de SpecBunch
