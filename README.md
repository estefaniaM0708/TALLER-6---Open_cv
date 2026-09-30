# Actividad 6.1 — Control de brazo robótico mediante ESP32-S3, teclado matricial y PyBullet

## Descripción del proyecto

En esta actividad se desarrolló un sistema de interacción entre una **ESP32-S3** y un computador para controlar una simulación robótica utilizando **PyBullet**.

El sistema permite ingresar un número mediante un teclado matricial 4x4 conectado a la ESP32-S3. El valor seleccionado es mostrado en una pantalla LCD 16x2 mediante comunicación I2C y posteriormente enviado al computador mediante comunicación serial USB.

El computador recibe el número enviado, carga un brazo robótico mediante un archivo URDF y ejecuta una trayectoria dentro del entorno de simulación PyBullet para representar el número seleccionado.

El proyecto integra:

- Programación embebida con MicroPython.
- Lectura de teclado matricial 4x4 mediante GPIO.
- Comunicación I2C con pantalla LCD 16x2.
- Comunicación serial UART entre ESP32-S3 y computador.
- Simulación robótica mediante PyBullet.
- Modelo del robot en formato URDF.

---

# Arquitectura del sistema

```text
                 TECLADO 4x4
                      |
                      |
                      v
                 ESP32-S3
              (MicroPython)
                      |
          -------------------------
          |                       |
          v                       v
       LCD 16x2              USB Serial
          I2C                    |
                                 |
                                 v
                           Computador
                              Python
                                 |
                                 v
                              PyBullet
                                 |
                                 v
                          Brazo robótico
                              URDF
```

---

# Hardware utilizado

## ESP32-S3

La ESP32-S3 funciona como unidad de adquisición y comunicación del sistema.

Sus funciones principales son:

- Leer las teclas ingresadas por el usuario.
- Mostrar información en la pantalla LCD.
- Enviar el número seleccionado al computador.

---

# Teclado matricial 4x4

El teclado matricial permite seleccionar el número que será enviado al sistema de simulación.

## Conexión del teclado

| Teclado | ESP32-S3 |
|---|---|
| F1 | GPIO 4 |
| F2 | GPIO 5 |
| F3 | GPIO 6 |
| F4 | GPIO 7 |
| C1 | GPIO 10 |
| C2 | GPIO 11 |
| C3 | GPIO 12 |
| C4 | GPIO 13 |

El funcionamiento del teclado se basa en un escaneo matricial:

1. La ESP32 activa una fila.
2. Lee el estado de las columnas.
3. Determina la posición de la tecla.
4. Convierte la posición en un valor numérico.

---

# Pantalla LCD 16x2 I2C

La pantalla LCD utiliza un módulo adaptador basado en el expansor PCF8574.

## Conexión LCD

| LCD | ESP32-S3 |
|---|---|
| SDA | GPIO 8 |
| SCL | GPIO 9 |
| VCC | 5V |
| GND | GND |

Dirección I2C utilizada:

```text
0x27
```

La comunicación permite controlar la pantalla utilizando únicamente las líneas:

- SDA
- SCL

---

# Software utilizado

## ESP32-S3

Lenguaje:

```text
MicroPython
```

Archivos utilizados:

```text
ESP32/

├── main.py
└── lcd_i2c.py
```

### main.py

Contiene:

- Configuración del teclado matricial.
- Lectura de teclas.
- Control de la pantalla LCD.
- Comunicación serial hacia el computador.

### lcd_i2c.py

Contiene las funciones necesarias para manejar la pantalla LCD mediante el protocolo I2C.

---

# Computador

Lenguaje utilizado:

```text
Python 3.10
```

Librerías utilizadas:

```text
pybullet
numpy
pyserial
opencv-python
```

Instalación:

```bash
pip install -r requisitos.txt
```

---

# Funcionamiento del sistema

## 1. Lectura del teclado

La ESP32-S3 realiza un escaneo del teclado matricial.

Cuando el usuario presiona una tecla:

- Se activa una fila.
- Se revisan las columnas.
- Se identifica la tecla presionada.

Ejemplo:

```text
Fila 1 + Columna 1 = número 1
```

---

## 2. Visualización en LCD

El número seleccionado se muestra en la pantalla LCD.

Ejemplo:

```text
Numero:
5
```

Esto permite verificar localmente la entrada ingresada.

---

## 3. Comunicación serial

Después de seleccionar el número, la ESP32-S3 envía la información al computador mediante USB.

Ejemplo de dato enviado:

```text
NUM:5
```

La comunicación utiliza:

```text
UART Serial
115200 baudios
```

---

# Simulación del brazo robótico

El computador recibe el número enviado desde la ESP32-S3 y ejecuta la simulación del robot.

El entorno utilizado es:

```text
PyBullet
```

El modelo del brazo se carga mediante:

```python
p.loadURDF("brazo.urdf")
```

El archivo URDF contiene:

- Geometría del robot.
- Enlaces mecánicos.
- Articulaciones.
- Parámetros físicos.

---

# Organización del repositorio

```text
Actividad_6.1/

│
├── ESP32/
│   │
│   ├── main.py
│   └── lcd_i2c.py
│
├── PC_PyBullet/
│   │
│   ├── boot.py
│   ├── brazo.urdf
│   └── requisitos.txt
│
└── README.md
```

---

# Ejecución del proyecto

## Programación ESP32-S3

Primero se identifica el puerto de comunicación:

```bash
python -m serial.tools.list_ports
```

Ejemplo:

```text
COM3
```

Luego se cargan los archivos en la ESP32:

Subir controlador LCD:

```bash
mpremote connect COM3 fs cp lcd_i2c.py :
```

Subir programa principal:

```bash
mpremote connect COM3 fs cp main.py :
```

Reiniciar la placa:

```bash
mpremote connect COM3 reset
```

---

# Ejecución de PyBullet

Ingresar a la carpeta:

```text
PC_PyBullet
```

Instalar dependencias:

```bash
pip install -r requisitos.txt
```

Ejecutar:

```bash
python boot.py
```

---

# Secuencia de operación

1. El usuario presiona un número en el teclado matricial.
2. La ESP32-S3 identifica la tecla.
3. La LCD muestra el valor seleccionado.
4. La ESP32 envía el número mediante comunicación serial.
5. El computador recibe la información.
6. PyBullet carga el brazo robótico.
7. El brazo ejecuta la trayectoria correspondiente.

---

# Comunicaciones utilizadas

| Comunicación | Función |
|---|---|
| GPIO | Lectura del teclado matricial |
| I2C | Control de pantalla LCD |
| UART Serial | Comunicación ESP32-S3 - computador |
| URDF | Modelo del brazo robótico |
| PyBullet | Simulación física |

---

# Resultados esperados

El sistema permite:

- Seleccionar números mediante una interfaz física.
- Visualizar la selección en una pantalla LCD.
- Comunicar un sistema embebido con un entorno virtual.
- Controlar un brazo robótico simulado mediante entradas reales.

---

# Conclusión

El desarrollo permitió integrar una plataforma embebida basada en ESP32-S3 con un entorno de simulación robótica en Python.

La ESP32-S3 funciona como interfaz física para la adquisición del dato mediante el teclado matricial, mientras que el computador ejecuta la simulación del brazo robótico mediante PyBullet y un modelo URDF.

Este sistema demuestra la comunicación entre hardware real y ambientes virtuales, permitiendo controlar una simulación robótica mediante una interfaz electrónica externa.
