# ================================================================
# prueba_teclado.py  |  Diagnóstico del teclado 4x4 y del LCD I2C
# Ejecutar en Thonny con el botón ▶ (NO hace falta guardarlo en la ESP32).
# Muestra en la consola de Thonny:
#   1) Qué dispositivos I2C encuentra (el LCD debe salir como 0x27 o 0x3f)
#   2) El estado de las columnas en reposo (deben estar todas en 1)
#   3) Fila, columna y tecla cada vez que presionas algo
# Detener con el botón rojo ■ (Stop) de Thonny.
# ================================================================
from machine import Pin, I2C
import time

PINES_FILAS = (13, 14, 27, 26)
PINES_COLUMNAS = (25, 33, 32, 23)
TECLAS = (
    ("1", "2", "3", "A"),
    ("4", "5", "6", "B"),
    ("7", "8", "9", "C"),
    ("*", "0", "#", "D"),
)

# ---------- 1) LCD / I2C ----------
i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=100000)
encontrados = i2c.scan()
print("Dispositivos I2C:", [hex(d) for d in encontrados])
if not encontrados:
    print("  -> No hay nada en el bus I2C: revisa VCC (5V), GND, SDA=21 y SCL=22")

# ---------- 2) Columnas en reposo ----------
filas = [Pin(n, Pin.OUT, value=1) for n in PINES_FILAS]
columnas = [Pin(n, Pin.IN, Pin.PULL_UP) for n in PINES_COLUMNAS]
reposo = [c.value() for c in columnas]
print("Columnas en reposo (deben ser 1 1 1 1):", *reposo)
for i, v in enumerate(reposo):
    if v == 0:
        print("  -> La columna C%d (GPIO%d) está en 0 sin presionar: corto o pin equivocado"
              % (i + 1, PINES_COLUMNAS[i]))

# ---------- 3) Escaneo ----------
print("\nPresiona teclas...  (si no aparece nada, revisa los 8 cables del teclado)")
anterior = None
while True:
    actual = None
    for f, fila in enumerate(filas):
        fila.value(0)
        time.sleep_us(5)
        for c, col in enumerate(columnas):
            if col.value() == 0:
                actual = (f, c)
        fila.value(1)
    if actual != anterior and actual is not None:
        f, c = actual
        print("Fila F%d (GPIO%d)  Columna C%d (GPIO%d)  ->  tecla '%s'"
              % (f + 1, PINES_FILAS[f], c + 1, PINES_COLUMNAS[c], TECLAS[f][c]))
    anterior = actual
    time.sleep_ms(20)
