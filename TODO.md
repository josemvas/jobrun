Notes
-----
- At least Python 3.2 required for: argparse library
- At least Python 3.3 required for: new IO exception hierarchy
- At least Python 3.4 required for: pathlib library
- At least Python 3.6 required for: formatted string literals, widespread pathlib objects, ordered basic dicts

General
-------
- Usar options.local parar las opciones locales como queue, delay, etc.
- Usar srun/sbcast para correr trabajos multinodo con slurm
- Usar lsrun/lsrcp para correr trabajos multinodo con lsf/openlava
- Usar qrsh/??? para correr trabajos multinodo con pbs/torque
- Usar regexes en lugar de globs para listar los directorios de parametros?
- Mostrar errores apropiados cuando se intenten enviar multiples trabajos con la misma carpeta de salida
- Agregar una opción para poder correr multiples trabajos en la misma carpeta de salida incluyendo el nombre y la versión del programa en los nombres de los archivos de salida
- Crear una conexion maestra para todas las llamadas de ssh y rsync
- Mover names y paths a su propio modulo de espacio de nombres
- Add suport for dialog boxes (-X/--xdialog option)
- Validar los valores de nhost/hosts antes de enviar el trabajo
- Mantener la carpeta de salida en el scratch si falla la copia al home
- Ignorar el known_hosts de los usuarios
- Trap para SIGINT y SIGTERM enviados por bkill
- Poner límite de memoria a los trabajos
- Agregar opción para imprimir la versión del script
- Determinar los conjuntos de parámetros a partir del filtro
- Nombrar la carpeta oculta de jobscripts con el número de trabajo?
- Agregar una opcion para ejecutar todos los archivos de entrada en el mismo trabajo?

scripts.py
----------
- Manejar los permisos denegados cuando se instalan los programas

queue.py
----------
- Preguntar si se lanza un trabajo cuando no se puede consultar su estado
- Checar el error estandar ademas de la salida estandar aunque no haya error?
