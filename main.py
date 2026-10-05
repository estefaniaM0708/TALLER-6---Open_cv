# ================================================================
# Actividad 6 - Punto 2  |  ESP-B  =  ESCLAVO SPI + OLED I2C  (MicroPython)
#
# Recibe por SPI la trama de la ESP-A (maestro):
#     [0xA5, digito, confianza, checksum, relleno]
# verifica el checksum, contesta ACK/NAK por MISO en el 5.º byte y
# muestra el dígito en grande en la pantalla OLED SSD1306 128x64.
#
# MicroPython no trae modo esclavo SPI, así que aquí se implementa el
# protocolo leyendo directamente las líneas del bus (modo 0):
#   - CS en bajo  -> empieza la trama
#   - flanco de subida de SCK -> se lee el bit de MOSI (MSB primero)
#   - flanco de bajada de SCK -> se pone el siguiente bit en MISO
#
# Conexiones
#   SPI (desde la ESP-A):  CS=GPIO5  SCK=GPIO18  MOSI=GPIO23  MISO=GPIO19  GND común
#   OLED I2C:              SDA=GPIO21  SCL=GPIO22  VCC=3V3  GND=GND
#
# Guardar en la ESP-B:  main.py  y  ssd1306.py
# ================================================================
from machine import Pin, I2C
import framebuf
import micropython
import time

from ssd1306 import SSD1306_I2C

# ---------------- Pines SPI (ESP32-S3 esclavo) ----------------
cs = Pin(10, Pin.IN, Pin.PULL_UP)
sck = Pin(12, Pin.IN)
mosi = Pin(11, Pin.IN)
miso = Pin(13, Pin.OUT, value=0)

INICIO, ACK, NAK, SIN_DIGITO = 0xA5, 0x06, 0x15, 0xFF
LARGO_TRAMA = 5
trama = bytearray(LARGO_TRAMA)

# ---------------- OLED ----------------
i2c = I2C(0, sda=Pin(8), scl=Pin(9), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
glifo = framebuf.FrameBuffer(bytearray(8), 8, 8, framebuf.MONO_VLSB)


def texto_grande(txt, x, y, escala):
    """Escribe texto con la fuente 8x8 ampliada 'escala' veces."""
    for k, ch in enumerate(txt):
        glifo.fill(0)
        glifo.text(ch, 0, 0, 1)
        for py in range(8):
            for px in range(8):
                if glifo.pixel(px, py):
                    oled.fill_rect(x + (k * 8 + px) * escala, y + py * escala,
                                   escala, escala, 1)


# Dígitos grandes: fuente propia de 5x7 (más limpia que la 8x8 ampliada)
FUENTE_5x7 = {
    0: (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    1: ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    2: (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    3: ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    4: ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    5: ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    6: ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    7: ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    8: (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    9: (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
}


def digito_grande(d, x, y, escala):
    for fila, patron in enumerate(FUENTE_5x7[d]):
        for col, ch in enumerate(patron):
            if ch == "#":
                oled.fill_rect(x + col * escala, y + fila * escala, escala, escala, 1)


def encabezado():
    oled.fill(0)
    oled.fill_rect(0, 0, 128, 10, 1)
    oled.text("ESCLAVO SPI", 20, 1, 0)


def pantalla_espera():
    encabezado()
    oled.text("Esperando", 28, 26, 1)
    oled.text("al maestro...", 12, 40, 1)
    oled.show()


def mostrar(digito, confianza, n):
    encabezado()
    if digito == SIN_DIGITO:
        oled.text("Sin digito", 24, 26, 1)
        oled.text("frente a la", 20, 38, 1)
        oled.text("camara", 40, 50, 1)
    else:
        oled.rect(2, 13, 54, 50, 1)                 # marco del dígito
        digito_grande(digito, 14, 17, 6)            # dígito de 30x42 píxeles
        oled.text("CNN", 80, 16, 1)
        conf = str(confianza) + "%"
        texto_grande(conf, 64 + (64 - len(conf) * 16) // 2, 28, 2)
        oled.text("#" + str(n), 76, 52, 1)
    oled.show()


# ---------------- Recepción SPI (esclavo por software) ----------------
@micropython.native
def recibir(buf):
    """Recibe una trama mientras CS está en bajo. Devuelve los bytes recibidos."""
    n = 0
    while n < LARGO_TRAMA:
        resp = 0
        if n == LARGO_TRAMA - 1:               # 5.º byte: contestar por MISO
            ok = buf[0] == INICIO and ((buf[0] ^ buf[1] ^ buf[2]) & 0xFF) == buf[3]
            resp = ACK if ok else NAK
        b = 0
        for i in range(8):
            miso.value((resp >> (7 - i)) & 1)  # bit para el maestro (antes de la subida)
            while not sck.value():             # esperar flanco de subida
                if cs.value():
                    return n
            b = (b << 1) | mosi.value()        # leer bit del maestro
            while sck.value():                 # esperar flanco de bajada
                if cs.value():
                    return n
        buf[n] = b
        n += 1
    return n


pantalla_espera()
print("ESP-B lista: esclavo SPI + OLED")
recibidas = 0
cs_anterior = 1

while True:
    cs_actual = cs.value()
    if cs_anterior == 1 and cs_actual == 0:        # flanco de bajada de CS: inicia trama
        n = recibir(trama)
        miso.value(0)
        while not cs.value():                      # esperar fin de la trama
            pass
        cs_actual = 1
        ok = (n == LARGO_TRAMA and trama[0] == INICIO
              and ((trama[0] ^ trama[1] ^ trama[2]) & 0xFF) == trama[3])
        if ok:
            recibidas += 1
            d, c = trama[1], trama[2]
            print("SPI recibido: digito", "-" if d == SIN_DIGITO else d, "conf", c, "%")
            mostrar(d, c, recibidas)
        else:
            print("Trama con error:", n, "bytes", [hex(x) for x in trama])
    cs_anterior = cs_actual
