# Actividad 6 — Sistemas embebidos con ESP32-S3, comunicación serial, I2C, SPI y visión por computador

Este repositorio contiene el desarrollo de los dos puntos de la Actividad 6:

| Punto | Tema | Hardware principal | Software en el PC |
|---|---|---|---|
| **6.1** | Control de brazo robótico mediante teclado matricial | 1 × ESP32-S3, teclado 4x4, LCD 16x2 I2C | PyBullet + URDF |
| **6.2** | Reconocimiento de dígitos escritos a mano con OpenCV + OLED I2C + comunicación SPI | 2 × ESP32-S3, OLED SSD1306 I2C | OpenCV + TensorFlow (CNN) |

---

## Contenido

- [Punto 6.1 — Control de brazo robótico mediante ESP32-S3, teclado matricial y PyBullet](#punto-61--control-de-brazo-robótico-mediante-esp32-s3-teclado-matricial-y-pybullet)
- [Punto 6.2 — Reconocimiento de dígitos con OpenCV, comunicación SPI y pantalla OLED I2C](#punto-62--reconocimiento-de-dígitos-con-opencv-comunicación-spi-y-pantalla-oled-i2c)
- [Organización del repositorio](#organización-del-repositorio)
- [Requisitos generales](#requisitos-generales)
- [Solución de problemas](#solución-de-problemas)
- [Evidencias](#evidencias)
- [Conclusiones](#conclusiones)

---

# Punto 6.1 — Control de brazo robótico mediante ESP32-S3, teclado matricial y PyBullet

## Descripción

En este punto se desarrolló un sistema de interacción entre una **ESP32-S3** y un computador para controlar una simulación robótica utilizando **PyBullet**.

El sistema permite ingresar un número mediante un teclado matricial 4x4 conectado a la ESP32-S3. El valor seleccionado se muestra en una pantalla LCD 16x2 mediante comunicación I2C y luego se envía al computador por comunicación serial USB.

El computador recibe el número, carga un brazo robótico desde un archivo URDF y ejecuta una trayectoria dentro del entorno de simulación PyBullet para representar el número seleccionado.

El proyecto integra:

- Programación embebida con MicroPython.
- Lectura de teclado matricial 4x4 mediante GPIO.
- Comunicación I2C con pantalla LCD 16x2.
- Comunicación serial UART entre ESP32-S3 y computador.
- Simulación robótica mediante PyBullet.
- Modelo del robot en formato URDF.

## Arquitectura del sistema

```text
                 TECLADO 4x4
                      |
                      v
                 ESP32-S3
              (MicroPython)
                      |
          -------------------------
          |                       |
          v                       v
       LCD 16x2              USB Serial
          I2C                     |
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

## Hardware utilizado

### ESP32-S3

La ESP32-S3 funciona como unidad de adquisición y comunicación del sistema. Sus funciones principales son:

- Leer las teclas ingresadas por el usuario.
- Mostrar información en la pantalla LCD.
- Enviar el número seleccionado al computador.

### Teclado matricial 4x4

El teclado matricial permite seleccionar el número que será enviado al sistema de simulación.

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

### Pantalla LCD 16x2 I2C

La pantalla LCD utiliza un módulo adaptador basado en el expansor PCF8574.

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

La comunicación permite controlar la pantalla utilizando únicamente las líneas SDA y SCL.

## Software utilizado

### ESP32-S3

Lenguaje: **MicroPython**

```text
Punto_6.1/ESP32/
├── main.py
└── lcd_i2c.py
```

- **main.py**: configuración del teclado matricial, lectura de teclas, control de la pantalla LCD y comunicación serial hacia el computador.
- **lcd_i2c.py**: funciones necesarias para manejar la pantalla LCD mediante el protocolo I2C.

### Computador

Lenguaje: **Python 3.10**

Librerías utilizadas:

```text
pybullet
numpy
pyserial
opencv-python
```

## Funcionamiento del sistema

### 1. Lectura del teclado

La ESP32-S3 realiza un escaneo del teclado matricial. Cuando el usuario presiona una tecla, se activa una fila, se revisan las columnas y se identifica la tecla presionada.

```text
Fila 1 + Columna 1 = número 1
```

### 2. Visualización en LCD

El número seleccionado se muestra en la pantalla LCD, lo que permite verificar localmente la entrada:

```text
Numero:
5
```

### 3. Comunicación serial

Después de seleccionar el número, la ESP32-S3 lo envía al computador por USB:

```text
NUM:5
```

Parámetros de la comunicación:

```text
UART Serial
115200 baudios
```

### 4. Simulación del brazo robótico

El computador recibe el número enviado desde la ESP32-S3 y ejecuta la simulación del robot en **PyBullet**. El modelo del brazo se carga mediante:

```python
p.loadURDF("brazo.urdf")
```

El archivo URDF contiene la geometría del robot, los enlaces mecánicos, las articulaciones y los parámetros físicos.

## Ejecución del Punto 6.1

### Programación de la ESP32-S3

Identificar el puerto de comunicación:

```bash
python -m serial.tools.list_ports
```

o bien:

```bash
python -m mpremote connect list
```

Desde la carpeta `Punto_6.1/ESP32`, cargar los archivos (reemplazar `COM3` por el puerto real):

```bash
python -m mpremote connect COM3 fs cp lcd_i2c.py :lcd_i2c.py
python -m mpremote connect COM3 fs cp main.py :main.py
python -m mpremote connect COM3 reset
```

### Ejecución de PyBullet

```bash
cd Punto_6.1/PC_PyBullet
pip install -r requisitos.txt
python boot.py
```

> Antes de ejecutar `boot.py`, cerrar cualquier consola serie o REPL abierto sobre el puerto de la ESP32-S3.

## Secuencia de operación

1. El usuario presiona un número en el teclado matricial.
2. La ESP32-S3 identifica la tecla.
3. La LCD muestra el valor seleccionado.
4. La ESP32-S3 envía el número mediante comunicación serial.
5. El computador recibe la información.
6. PyBullet carga el brazo robótico.
7. El brazo ejecuta la trayectoria correspondiente.

## Comunicaciones utilizadas

| Comunicación | Función |
|---|---|
| GPIO | Lectura del teclado matricial |
| I2C | Control de pantalla LCD |
| UART Serial | Comunicación ESP32-S3 – computador |
| URDF | Modelo del brazo robótico |
| PyBullet | Simulación física |

## Resultados

El sistema permite:

- Seleccionar números mediante una interfaz física.
- Visualizar la selección en una pantalla LCD.
- Comunicar un sistema embebido con un entorno virtual.
- Controlar un brazo robótico simulado mediante entradas reales.

---

# Punto 6.2 — Reconocimiento de dígitos con OpenCV, comunicación SPI y pantalla OLED I2C

## Descripción

En este punto se desarrolló un sistema que reconoce **dígitos escritos a mano** usando la cámara del computador, **OpenCV** y una **red neuronal convolucional (CNN)** entrenada con el conjunto de datos MNIST.

El dígito reconocido se envía por USB serie a una **ESP32-S3 maestra**, que lo retransmite mediante **comunicación SPI** a una **ESP32-S3 esclava**. La esclava muestra el número y su nivel de confianza en una **pantalla OLED SSD1306** conectada por **I2C**.

El proyecto integra:

- Captura de video con la cámara del PC.
- Preprocesamiento de imágenes con OpenCV.
- Reconocimiento de dígitos con una CNN (TensorFlow/Keras).
- Comunicación serial USB entre el PC y la ESP32-S3 maestra.
- Comunicación SPI entre dos ESP32-S3 (maestro – esclavo).
- Comunicación I2C entre la ESP32-S3 esclava y la pantalla OLED.

## Esquema de desarrollo

```text
Cámara PC → Preprocesamiento OpenCV → Reconocimiento CNN → Envío por puerto serie
                                                                  |
                                                                  v
                                                       ESP-A (MAESTRO SPI)
                                                                  |
                                                                  v
                                                    Envío de información por SPI
                                                                  |
                                                                  v
                                                       ESP-B (ESCLAVO SPI)
                                                                  |
                                                                  v
                                                          Mostrar en OLED I2C
```

## Arquitectura del sistema

```text
        Cámara del PC
              |
              v
      Computador (Python)
   OpenCV + CNN (MNIST)
              |
         USB Serial
          (COM7)
              |
              v
     ESP32-S3 A — MAESTRO
         (MicroPython)
              |
             SPI
  (CS, SCK, MOSI, MISO, GND)
              |
              v
     ESP32-S3 B — ESCLAVO
         (MicroPython)
              |
             I2C
              |
              v
     OLED SSD1306 128x64
```

## Hardware utilizado

- 2 × ESP32-S3 DevKit con firmware MicroPython.
- 1 × Pantalla OLED SSD1306 I2C de 128 × 64 píxeles (alimentación de 3,3 V).
- Cables Dupont y protoboard.
- 2 × cables USB de datos.
- Computador con cámara, Python y Visual Studio Code.

| Placa | Rol | Puerto usado |
|---|---|---|
| ESP32-S3 A | Maestro SPI, recibe el dígito del PC | COM7 |
| ESP32-S3 B | Esclavo SPI, controla la OLED | COM8 |

> Los números de puerto COM pueden cambiar según el computador y el puerto USB usado. Verificarlos con `python -m mpremote connect list`.

## Conexiones

### SPI entre las dos ESP32-S3

Ambas placas usan los mismos pines, por lo que cada pin se conecta con el del mismo número en la otra placa.

| Señal | ESP32-S3 A (maestro) | ESP32-S3 B (esclavo) | Función |
|---|---|---|---|
| CS | GPIO 10 | GPIO 10 | Selección del esclavo |
| SCK | GPIO 12 | GPIO 12 | Reloj generado por el maestro |
| MOSI | GPIO 11 | GPIO 11 | Datos del maestro al esclavo |
| MISO | GPIO 13 | GPIO 13 | Datos del esclavo al maestro |
| GND | GND | GND | Referencia común |

### Pantalla OLED (solo en la ESP32-S3 esclava)

| OLED | ESP32-S3 B |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO 8 |
| SCL | GPIO 9 |

Dirección I2C de la OLED:

```text
0x3C (60 en decimal)
```

### Recomendaciones de montaje

- Cada placa se alimenta por su propio cable USB.
- Se unen los **GND** de ambas placas, pero **no** los pines 3V3.
- Si la ESP32-S3 tiene dos puertos USB-C (USB nativo y UART), usar siempre el mismo, porque el número de COM cambia según el puerto.
- Verificar que los GPIO 8 a 13 estén expuestos y libres en el modelo exacto de la placa.

## Software utilizado

### ESP32-S3 A — Maestro

```text
Punto_2_Digitos_OLED_SPI/esp_a_maestro/
└── main.py
```

Recibe por USB serie el mensaje del PC y lo envía por SPI al esclavo. Configuración de pines:

```python
# Pines SPI (ESP32-S3 maestro)
spi = SoftSPI(baudrate=2000, polarity=0, phase=0,
              sck=Pin(12), mosi=Pin(11), miso=Pin(13))
cs = Pin(10, Pin.OUT, value=1)
```

### ESP32-S3 B — Esclavo

```text
Punto_2_Digitos_OLED_SPI/esp_b_esclavo/
├── main.py
└── ssd1306.py
```

Recibe el dato por SPI mediante lectura de GPIO y lo muestra en la OLED. Configuración de pines:

```python
# Pines SPI (ESP32-S3 esclavo)
cs = Pin(10, Pin.IN, Pin.PULL_UP)
sck = Pin(12, Pin.IN)
mosi = Pin(11, Pin.IN)
miso = Pin(13, Pin.OUT, value=0)

# OLED: ESP32-S3
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
```

- **ssd1306.py**: controlador de la pantalla OLED para MicroPython.

### Computador

```text
Punto_2_Digitos_OLED_SPI/pc/
├── entrenar_modelo.py
├── reconocer_y_enviar.py
└── modelo_mnist_cnn.h5   (se genera al entrenar)
```

- **entrenar_modelo.py**: entrena la CNN con MNIST y guarda `modelo_mnist_cnn.h5`.
- **reconocer_y_enviar.py**: abre la cámara, preprocesa la imagen, predice el dígito y lo envía a la ESP32-S3 maestra.

Librerías utilizadas:

```text
opencv-python
tensorflow
pyserial
numpy
mpremote
```

## Funcionamiento del sistema

### 1. Captura y preprocesamiento (OpenCV)

En cada imagen de la cámara, el programa:

1. Convierte la imagen a escala de grises y aplica un suavizado para reducir el ruido.
2. Aplica un **umbral invertido**: la tinta queda blanca y el papel negro, igual que en las imágenes de MNIST.
3. Busca el **contorno** más grande, que corresponde al número, y lo recorta.
4. Redimensiona el recorte a **28 × 28 píxeles** y normaliza los valores entre 0 y 1.

### 2. Reconocimiento (CNN)

La CNN entrega 10 probabilidades, una por cada dígito del 0 al 9. El programa toma la de mayor valor como dígito reconocido y su probabilidad como nivel de confianza.

> La red siempre devuelve uno de los 10 dígitos, incluso si no hay nada escrito frente a la cámara. Por eso se recomienda enviar el dato solo cuando la confianza supera un umbral (por ejemplo, 80 %) y el contorno tiene un área mínima.

### 3. Comunicación serial PC → maestro

El PC envía el dígito y la confianza por USB a la ESP32-S3 maestra (COM7):

```text
DIG:5,90
```

### 4. Comunicación SPI maestro → esclavo

La ESP32-S3 maestra activa la línea CS, genera el reloj en SCK y transmite el dígito por MOSI. Si la transmisión es correcta, responde al PC:

```text
SPI:OK 5
```

### 5. Visualización en la OLED

La ESP32-S3 esclava recibe el dato y lo muestra en la pantalla OLED junto con el porcentaje de confianza.

## Ejecución del Punto 6.2

Todos los comandos se ejecutan en la terminal de Visual Studio Code (PowerShell), desde la carpeta `Punto_2_Digitos_OLED_SPI`.

### 1. Instalar dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install mpremote esptool opencv-python tensorflow pyserial numpy
```

### 2. Identificar los puertos COM

Conectar una placa a la vez y anotar el puerto de cada una:

```powershell
python -m mpremote connect list
```

### 3. Instalar MicroPython en las ESP32-S3 (si no lo tienen)

Descargar el firmware **ESP32_GENERIC_S3** desde [micropython.org](https://micropython.org/download/ESP32_GENERIC_S3/) y ejecutar (cambiar `COM7` y el nombre del archivo según corresponda):

```powershell
python -m esptool --chip esp32s3 --port COM7 erase_flash
python -m esptool --chip esp32s3 --port COM7 --baud 460800 write_flash -z 0x0 ESP32_GENERIC_S3-xxxx.bin
```

> En la ESP32-S3 el firmware se graba en la dirección **0x0**. Si `esptool` no conecta, mantener presionado **BOOT**, pulsar y soltar **RST**, y luego soltar **BOOT**.

### 4. Cargar el código en la ESP32-S3 esclava (COM8)

```powershell
python -m mpremote connect COM8 fs cp .\esp_b_esclavo\ssd1306.py :ssd1306.py
python -m mpremote connect COM8 fs cp .\esp_b_esclavo\main.py :main.py
python -m mpremote connect COM8 reset
```

### 5. Cargar el código en la ESP32-S3 maestra (COM7)

```powershell
python -m mpremote connect COM7 fs cp .\esp_a_maestro\main.py :main.py
python -m mpremote connect COM7 reset
```

### 6. Ejecutar el sistema completo

```powershell
# Reiniciar primero el esclavo y luego el maestro
python -m mpremote connect COM8 reset
Start-Sleep -Seconds 2
python -m mpremote connect COM7 reset
Start-Sleep -Seconds 2

# Entrar a la carpeta del PC
cd .\pc

# Entrenar el modelo solo si no existe
if (-not (Test-Path .\modelo_mnist_cnn.h5)) { python entrenar_modelo.py }

# Cámara + reconocimiento + envío al maestro
python reconocer_y_enviar.py --puerto COM7
```

Para probar solo la cámara, sin las ESP32-S3:

```powershell
python reconocer_y_enviar.py --sin-esp
```

### 7. Monitorear la ESP32-S3 esclava (opcional)

En una segunda terminal:

```powershell
python -m mpremote connect COM8 resume repl
```

`resume` conecta sin reiniciar el programa. Para salir se usa **Ctrl + ]**.

> No abrir un monitor serie en COM7 mientras se ejecuta `reconocer_y_enviar.py`, porque el puerto quedaría ocupado.

### Verificación de la OLED

Para comprobar que la ESP32-S3 esclava detecta la pantalla:

```python
from machine import Pin, I2C
i2c = I2C(0, sda=Pin(8), scl=Pin(9))
print(i2c.scan())
```

Si devuelve `[60]`, la OLED está conectada en la dirección `0x3C`.

## Secuencia de operación

1. El usuario escribe un número en una hoja y lo pone frente a la cámara.
2. OpenCV captura y preprocesa la imagen.
3. La CNN predice el dígito y su confianza.
4. El PC envía el dato a la ESP32-S3 maestra por USB serie.
5. La ESP32-S3 maestra transmite el dígito por SPI a la ESP32-S3 esclava.
6. La ESP32-S3 esclava muestra el dígito en la pantalla OLED.

## Recomendaciones para un buen reconocimiento

- Escribir con marcador negro grueso sobre hoja blanca.
- Escribir el número grande y centrado.
- Cerrar bien los trazos (por ejemplo, el 0 sin cruces que lo hagan parecer un 8).
- Usar iluminación pareja, sin sombras sobre la hoja.

## Comunicaciones utilizadas

| Comunicación | Función |
|---|---|
| USB Serial | Envío del dígito del PC a la ESP32-S3 maestra |
| SPI | Transmisión del dígito entre maestro y esclavo |
| I2C | Control de la pantalla OLED |
| OpenCV | Captura y preprocesamiento de imagen |
| CNN (TensorFlow) | Reconocimiento del dígito |

---

# Organización del repositorio

```text
Actividad_6/
│
├── Punto_6.1/
│   ├── ESP32/
│   │   ├── main.py
│   │   └── lcd_i2c.py
│   │
│   └── PC_PyBullet/
│       ├── boot.py
│       ├── brazo.urdf
│       └── requisitos.txt
│
├── Punto_2_Digitos_OLED_SPI/          (Punto 6.2)
│   ├── esp_a_maestro/
│   │   └── main.py
│   │
│   ├── esp_b_esclavo/
│   │   ├── main.py
│   │   └── ssd1306.py
│   │
│   └── pc/
│       ├── entrenar_modelo.py
│       ├── reconocer_y_enviar.py
│       └── modelo_mnist_cnn.h5
│
├── evidencias/
│   └── punto6_1.mp4
│
└── README.md
```

---

# Requisitos generales

| Elemento | Punto 6.1 | Punto 6.2 |
|---|---|---|
| Placas | 1 × ESP32-S3 | 2 × ESP32-S3 |
| Firmware | MicroPython | MicroPython (ESP32_GENERIC_S3) |
| Periféricos | Teclado 4x4, LCD 16x2 I2C | OLED SSD1306 I2C, cámara del PC |
| Python | 3.10 o superior | 3.10 o superior |
| Librerías | pybullet, numpy, pyserial, opencv-python | opencv-python, tensorflow, pyserial, numpy |
| Herramientas | mpremote | mpremote, esptool |

---

# Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| `could not enter raw repl` y respuesta `b''` | La placa no tiene MicroPython o un `main.py` bloquea el REPL | Reinstalar MicroPython con `esptool` (borra también el `main.py`) |
| Error de puerto ocupado | Otra terminal, Thonny o monitor serie usa el COM | Cerrar las demás aplicaciones que usen ese puerto |
| La OLED no enciende | Cableado de VCC, GND, SDA o SCL | Revisar conexiones y ejecutar `i2c.scan()` |
| `ImportError: ssd1306` | Falta el controlador en la esclava | Copiar `ssd1306.py` a la ESP32-S3 esclava |
| `SPI:ERROR` | Falta GND común, pines cruzados o una placa sin programa | Revisar CS, SCK, MOSI, MISO y GND; reiniciar primero el esclavo |
| La OLED muestra un número sin que haya nada escrito | La CNN siempre predice un dígito | Usar umbral de confianza y área mínima de contorno |
| Un 0 se reconoce como 8 | Ruido o deformación del recorte | Recorte cuadrado con margen, mejor iluminación y trazo más grueso |
| Falta `modelo_mnist_cnn.h5` | El modelo no se ha entrenado | Ejecutar `python entrenar_modelo.py` |
| El COM cambió | Se usó otro puerto USB o se regrabó el firmware | Volver a ejecutar `python -m mpremote connect list` |

---

# Evidencias

## Punto 6.1

[▶️ Video demostrativo Punto 6.1](evidencias/punto6_1.mp4)

## Punto 6.2

[▶️ Video demostrativo Punto 6.2](https://drive.google.com/file/d/1uuml7eOXimRJBuatf_v_C6xNtUrNwvLP/view?usp=sharing)

---

# Conclusiones

**Punto 6.1.** Se integró una plataforma embebida basada en ESP32-S3 con un entorno de simulación robótica en Python. La ESP32-S3 funciona como interfaz física para adquirir el dato mediante el teclado matricial, mientras que el computador ejecuta la simulación del brazo robótico con PyBullet y un modelo URDF. Esto demuestra la comunicación entre hardware real y ambientes virtuales.

**Punto 6.2.** Se construyó un sistema que combina visión por computador e inteligencia artificial con comunicación entre microcontroladores. El computador reconoce dígitos escritos a mano con OpenCV y una CNN, y la información recorre tres protocolos distintos: USB serie (PC → maestro), SPI (maestro → esclavo) e I2C (esclavo → OLED). Esto permitió aplicar la arquitectura maestro–esclavo de SPI y evidenciar la importancia del preprocesamiento de imagen para la precisión del reconocimiento.

En conjunto, ambos puntos muestran cómo la ESP32-S3 puede actuar como puente entre el mundo físico y aplicaciones de software en el computador, usando distintos protocolos de comunicación según la necesidad de cada sistema.
