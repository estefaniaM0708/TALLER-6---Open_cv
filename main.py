# ================================================================
# Actividad 6 - Punto 1  |  ESP32 + MicroPython (Thonny)
# Teclado matricial 4x4 + LCD 16x2 I2C -> brazo dibujando en PyBullet
#
# Se escribe un número (hasta 4 cifras) en el teclado, se ve en el
# LCD y al presionar '#' se envía por USB (UART) al PC. El script
# "dibujar_brazo_teclado.py" hace que el brazo lo dibuje en una
# pizarra y le devuelve el estado a la ESP32, que lo muestra en el LCD.
#
#   Tecla   Acción
#   0..9    agregar cifra (máx. 4)
#   *       borrar la última cifra
#   #       enviar -> el brazo dibuja el número        (NUM:123)
#   A       repetir el último dibujo                   (CMD:A)
#   B       borrar la pizarra                          (CMD:B)
#   C       brazo a posición de reposo (home)          (CMD:C)
#   D       limpiar lo escrito en el LCD (solo local)
#
# Conexiones
#   LCD I2C :  SDA -> GPIO21   SCL -> GPIO22   VCC -> 5V (VIN)   GND -> GND
#   Teclado :  F1 F2 F3 F4 -> GPIO 13 14 27 26
#              C1 C2 C3 C4 -> GPIO 25 33 32 23
#   (el teclado usa las resistencias pull-up internas, no requiere externas)
#
# Guardar este archivo como main.py en la ESP32 junto con lcd_i2c.py
# ================================================================
from machine import Pin, I2C
import sys
import select
import time

from lcd_i2c import LCD

# ---------------- LCD ----------------
# Si el LCD falla (mal conectado), el programa sigue funcionando sin él
# para que el teclado y la comunicación con el PC se puedan probar igual.
class _SinLCD:
    def linea(self, fila, texto):
        pass


try:
    i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=100000)
    print("I2C encontrado en:", [hex(d) for d in i2c.scan()])
    lcd = LCD(i2c)
except Exception as e:
    print("AVISO: LCD no responde (revisa VCC=5V, GND, SDA=21, SCL=22):", e)
    lcd = _SinLCD()

led = Pin(2, Pin.OUT)      # LED azul de la placa: parpadea con cada tecla

# ---------------- TECLADO 4x4 ----------------
TECLAS = (
    ("1", "2", "3", "A"),
    ("4", "5", "6", "B"),
    ("7", "8", "9", "C"),
    ("*", "0", "#", "D"),
)
FILAS = [Pin(n, Pin.OUT, value=1) for n in (13, 14, 27, 26)]
COLUMNAS = [Pin(n, Pin.IN, Pin.PULL_UP) for n in (25, 33, 32, 23)]


def escanear():
    """Devuelve la tecla presionada o None. Pone una fila en 0 a la vez
    y mira qué columna cae a 0."""
    for f, fila in enumerate(FILAS):
        fila.value(0)
        time.sleep_us(5)
        for c, col in enumerate(COLUMNAS):
            if col.value() == 0:
                fila.value(1)
                return TECLAS[f][c]
        fila.value(1)
    return None


# ---------------- COMUNICACIÓN CON EL PC ----------------
# Lo que la ESP32 imprime con print() viaja por el USB al PC.
# Lo que el PC escribe en el puerto llega por sys.stdin.
lector = select.poll()
lector.register(sys.stdin, select.POLLIN)
buffer_pc = ""


def leer_pc():
    """Lee sin bloquear una línea enviada por el PC (o None)."""
    global buffer_pc
    while lector.poll(0):
        ch = sys.stdin.read(1)
        if ch in ("\n", "\r"):
            if buffer_pc:
                linea, buffer_pc = buffer_pc, ""
                return linea
        else:
            buffer_pc += ch
    return None


# ---------------- PROGRAMA PRINCIPAL ----------------
MAX_CIFRAS = 4
numero = ""
ultima = None
ANTIRREBOTE_MS = 30


def mostrar_numero():
    lcd.linea(0, "Numero: " + numero + ("_" if len(numero) < MAX_CIFRAS else ""))


def estado(texto):
    lcd.linea(1, texto)


mostrar_numero()
estado("#=Dibujar *=Borr")
print("ESP32 lista: teclado + LCD")

while True:
    tecla = escanear()

    if tecla is not None and tecla != ultima:
        time.sleep_ms(ANTIRREBOTE_MS)
        if escanear() == tecla:                 # confirmada (antirrebote)
            print("TECLA:" + tecla)             # diagnóstico (el PC la ignora)
            led.value(1)
            time.sleep_ms(40)
            led.value(0)
            if tecla.isdigit():
                if len(numero) < MAX_CIFRAS:
                    numero += tecla
                    mostrar_numero()
                else:
                    estado("Max 4 cifras")
            elif tecla == "*":
                numero = numero[:-1]
                mostrar_numero()
            elif tecla == "#":
                if numero:
                    print("NUM:" + numero)      # -> PC
                    estado("Enviado: " + numero)
                    numero = ""
                    mostrar_numero()
                else:
                    estado("Escribe un num.")
            elif tecla == "A":
                print("CMD:A")
                estado("Repitiendo...")
            elif tecla == "B":
                print("CMD:B")
                estado("Borrando pizarra")
            elif tecla == "C":
                print("CMD:C")
                estado("Brazo a home")
            elif tecla == "D":
                numero = ""
                mostrar_numero()
                estado("#=Dibujar *=Borr")
    ultima = tecla

    # Mensajes del PC:  "LCD:texto"  -> segunda línea del LCD
    msg = leer_pc()
    if msg and msg.startswith("LCD:"):
        estado(msg[4:])

    time.sleep_ms(10)
