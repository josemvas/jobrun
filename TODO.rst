console.py
Seleccionar el scheduler interactivamente y renombrar Generic -> Nuevo

queue.py
Preguntar si se lanza el trabajo en caso de error al consultar su estado
Checar el error estandar ademas de la salida estandar cuando no hay error

progspec.json
Unificar la llave y el numero de las versiones de los programas en los archivos de configuración
Cambiar el mecanisno de generación de comentarios BSUB/SBATCH/PBS para soportar TORQUE
Separar los archivos de instalacion en bin/ y etc/

Mantener la carpeta de salida en el scratch si falla la copia al home

Ignorar el known_hosts de los usuarios

Trap para SIGINT y SIGTERM enviados por bkill

Poner límite de memoria a los trabajos

Agregar opción para imprimir la versión del programa
