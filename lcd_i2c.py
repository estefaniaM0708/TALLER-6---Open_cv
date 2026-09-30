# ================================================================
# lcd_i2c.py  |  Driver mínimo para LCD 16x2 (HD44780) con módulo
# I2C PCF8574 (el "backpack" azul/negro que viene soldado al LCD).
#
# Mapeo del PCF8574 (el más común):
#   P0=RS  P1=RW  P2=E  P3=Luz de fondo  P4..P7 = D4..D7
#
# Uso:
#   from machine import I2C, Pin
#   from lcd_i2c import LCD
#   lcd = LCD(I2C(0, sda=Pin(21), scl=Pin(22), freq=100000))
#   lcd.linea(0, "Hola")
# ================================================================
import time

_RS = 0x01
_EN = 0x04
_LUZ = 0x08


class LCD:
    def __init__(self, i2c, direccion=None, columnas=16, filas=2):
        self.i2c = i2c
        self.columnas = columnas
        self.filas = filas
        if direccion is None:
            encontrados = i2c.scan()
            # 0x27 (PCF8574) o 0x3F (PCF8574A) son las direcciones típicas
            direccion = 0x27
            for d in (0x27, 0x3F):
                if d in encontrados:
                    direccion = d
                    break
            else:
                if encontrados:
                    direccion = encontrados[0]
        self.dir = direccion

        time.sleep_ms(50)
        # Secuencia de inicialización en modo 4 bits (datasheet HD44780)
        for _ in range(3):
            self._nibble(0x30)
            time.sleep_ms(5)
        self._nibble(0x20)
        self.comando(0x28)   # 4 bits, 2 líneas, fuente 5x8
        self.comando(0x0C)   # display ON, cursor OFF
        self.comando(0x06)   # el cursor avanza a la derecha
        self.limpiar()

    # ---------- bajo nivel ----------
    def _escribir(self, dato):
        self.i2c.writeto(self.dir, bytes([dato | _LUZ]))

    def _nibble(self, dato):
        self._escribir(dato | _EN)
        time.sleep_us(1)
        self._escribir(dato & ~_EN)
        time.sleep_us(50)

    def _enviar(self, valor, rs):
        self._nibble((valor & 0xF0) | rs)
        self._nibble(((valor << 4) & 0xF0) | rs)

    # ---------- alto nivel ----------
    def comando(self, c):
        self._enviar(c, 0)
        if c in (0x01, 0x02):
            time.sleep_ms(2)

    def limpiar(self):
        self.comando(0x01)

    def mover(self, col, fila):
        offsets = (0x00, 0x40, 0x14, 0x54)
        self.comando(0x80 | (col + offsets[fila]))

    def escribir(self, texto):
        for ch in texto:
            self._enviar(ord(ch), _RS)

    def linea(self, fila, texto):
        """Escribe una línea completa (rellena con espacios lo que sobra)."""
        texto = texto[:self.columnas]
        texto = texto + " " * (self.columnas - len(texto))
        self.mover(0, fila)
        self.escribir(texto)
