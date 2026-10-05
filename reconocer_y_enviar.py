"""
================================================================
 ACTIVIDAD 6 - PUNTO 2  |  PC
 Cámara -> preprocesamiento OpenCV -> reconocimiento CNN -> puerto serie
 reconocer_y_enviar.py
================================================================
 Basado en el ejemplo de clase "10) Open_Cv/reconocer_digito.py"
 del repositorio U_Militar. Se agregó:
   - Envío del dígito reconocido por el puerto serie a la ESP-A
     (maestro SPI) con el formato  "DIG:<digito>,<confianza>\n"
     y "DIG:-" cuando ya no hay dígito frente a la cámara.
   - Solo se envía cuando el dígito es ESTABLE (votación) y CAMBIA,
     para no saturar el enlace SPI.
   - Se muestra en la ventana lo que responde la ESP-A
     ("SPI:OK 5" o "SPI:ERROR 5").

 Teclas en la ventana:  q = salir   e = reenviar el dígito actual

 Requisitos:
   pip install opencv-python tensorflow pyserial numpy
   Antes, entrenar el modelo una vez:  python entrenar_modelo.py

 Uso:
   python reconocer_y_enviar.py --puerto COM3
   python reconocer_y_enviar.py --sin-esp        (solo cámara + CNN)
   python reconocer_y_enviar.py --camara 1       (otra cámara)
 IMPORTANTE: cierra Thonny antes de ejecutar (libera el puerto COM).
================================================================
"""

# ------------------------------------------------------------------
# 0. Silenciar mensajes de TensorFlow (deben ir ANTES de importar TF)
# ------------------------------------------------------------------
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import argparse
import time

import cv2
import numpy as np
import tensorflow as tf

try:
    import serial
except ImportError:
    serial = None

CARPETA = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(CARPETA, "modelo_mnist_cnn.h5")
BAUDRATE = 115200

VENTANA = 7              # nº de predicciones para la votación
VOTOS_MIN = 5            # votos iguales necesarios para aceptar un dígito
CONFIANZA_MIN = 80.0     # % mínimo de la CNN
TIEMPO_SIN_DIGITO = 1.5  # s sin dígito para avisar "DIG:-"


# ------------------------------------------------------------------
# 1. Preprocesamiento estilo MNIST (el mismo del ejemplo de clase)
# ------------------------------------------------------------------
def preprocesar_digito(roi):
    """
    Convierte un recorte BGR de la webcam en una imagen 28x28 tipo MNIST:
      - Fondo negro, dígito blanco
      - Centrado por centro de masa
      - Escalado a 20x20 con margen
    Devuelve (imagen_normalizada, caja) o (None, None) si no hay dígito.
    """
    if roi is None or roi.size == 0:
        return None, None

    gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)                  # 1.1 grises
    blur = cv2.GaussianBlur(gris, (5, 5), 0)                      # 1.2 suavizado
    umbral = cv2.adaptiveThreshold(blur, 255,                     # 1.3 umbral adaptativo
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)

    contornos, _ = cv2.findContours(umbral, cv2.RETR_EXTERNAL,   # 1.4 contorno más grande
                                    cv2.CHAIN_APPROX_SIMPLE)
    # Mejora: descartar lo que toca el borde del recuadro (borde de la hoja,
    # dedos, sombras), así solo queda el dígito escrito en el centro.
    alto, ancho = umbral.shape
    def toca_borde(c):
        bx, by, bw, bh = cv2.boundingRect(c)
        return bx <= 2 or by <= 2 or bx + bw >= ancho - 2 or by + bh >= alto - 2
    contornos = [c for c in contornos if not toca_borde(c)]
    if not contornos:
        return None, None
    c = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:                                  # ignorar ruido
        return None, None

    x, y, w, h = cv2.boundingRect(c)                              # 1.5 recortar
    digito = umbral[y:y + h, x:x + w]

    if w > h:                                                     # 1.6 a 20x20
        nuevo_w, nuevo_h = 20, max(1, int(round(20 * h / w)))
    else:
        nuevo_w, nuevo_h = max(1, int(round(20 * w / h))), 20
    digito = cv2.resize(digito, (nuevo_w, nuevo_h), interpolation=cv2.INTER_AREA)

    lienzo = np.zeros((28, 28), dtype=np.uint8)                   # 1.7 centrar por masa
    M = cv2.moments(digito)
    if M["m00"] != 0:
        cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
    else:
        cx, cy = nuevo_w // 2, nuevo_h // 2
    dx, dy = 14 - cx, 14 - cy
    for i in range(nuevo_h):
        for j in range(nuevo_w):
            yi, xj = i + dy, j + dx
            if 0 <= yi < 28 and 0 <= xj < 28:
                lienzo[yi, xj] = digito[i, j]

    return lienzo / 255.0, (x, y, w, h)                           # 1.8 normalizar


# ------------------------------------------------------------------
# 2. Enlace serie con la ESP-A (maestro SPI)
# ------------------------------------------------------------------
class EnlaceESP:
    def __init__(self, puerto):
        self.ser = serial.Serial(puerto, BAUDRATE, timeout=0)
        time.sleep(2)                       # la ESP32 se reinicia al abrir el puerto
        self.ser.reset_input_buffer()
        self.buffer = ""

    def enviar(self, texto):
        self.ser.write((texto + "\n").encode())

    def lineas(self):
        datos = self.ser.read(self.ser.in_waiting or 1)
        if datos:
            self.buffer += datos.decode("utf-8", errors="ignore")
        *completas, self.buffer = self.buffer.replace("\r", "").split("\n")
        return [l.strip() for l in completas if l.strip()]

    def cerrar(self):
        self.ser.close()


# ------------------------------------------------------------------
# 3. Programa principal
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", default="COM3", help="puerto de la ESP-A (maestro)")
    ap.add_argument("--camara", type=int, default=0)
    ap.add_argument("--sin-esp", action="store_true", help="probar sin la ESP32")
    args = ap.parse_args()

    if not os.path.exists(MODELO):
        print(f"No se encontró {MODELO}. Ejecuta primero: python entrenar_modelo.py")
        return
    modelo = tf.keras.models.load_model(MODELO)
    print("Modelo cargado.")

    esp = None
    if not args.sin_esp:
        if serial is None:
            print("pyserial no está instalado: se continúa sin ESP32.")
        else:
            try:
                esp = EnlaceESP(args.puerto)
                print(f"ESP-A conectada en {args.puerto}.")
            except Exception as e:
                print(f"No se pudo abrir {args.puerto} ({e}). Se continúa sin ESP32.")

    # En Windows CAP_DSHOW abre la cámara mucho más rápido
    if os.name == "nt":
        cap = cv2.VideoCapture(args.camara, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(args.camara)
    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return
    print("Presiona 'q' para salir, 'e' para reenviar el dígito.")

    historial = []
    enviado = None                 # último dígito enviado (None = nada, "-" = sin dígito)
    ultimo_visto = time.time()
    estado_esp = "Esperando..." if esp else "Sin ESP32"
    ultimo_estable, ultima_conf = None, 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Región de interés centrada (300x300 o lo que quepa)
            alto, ancho = frame.shape[:2]
            lado = min(300, alto - 20, ancho - 20)
            x1, y1 = (ancho - lado) // 2, (alto - lado) // 2
            x2, y2 = x1 + lado, y1 + lado
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            digito, _ = preprocesar_digito(frame[y1:y2, x1:x2])
            estable = None
            if digito is not None:
                pred = modelo.predict(digito.reshape(1, 28, 28, 1), verbose=0)[0]
                clase, confianza = int(np.argmax(pred)), float(np.max(pred)) * 100
                if confianza >= CONFIANZA_MIN:
                    historial.append(clase)
                    historial = historial[-VENTANA:]
                    candidato = max(set(historial), key=historial.count)
                    if historial.count(candidato) >= VOTOS_MIN:
                        estable = candidato
                        ultima_conf = confianza
                        ultimo_visto = time.time()
                        cv2.putText(frame, f"Numero: {estable} ({confianza:.1f}%)",
                                    (x1, y1 - 15), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                    (0, 255, 0), 2)

                vista = cv2.resize((digito * 255).astype(np.uint8), (200, 200),
                                   interpolation=cv2.INTER_NEAREST)
                cv2.imshow('Digito procesado (28x28 ampliado)', vista)
            else:
                historial.clear()

            # ---- Envío a la ESP-A: solo cuando cambia ----
            if estable is not None:
                ultimo_estable = estable
                if enviado != estable:
                    mensaje = f"DIG:{estable},{int(ultima_conf)}"
                    enviado = estable
                    print("PC  >>", mensaje)
                    if esp:
                        esp.enviar(mensaje)
            elif time.time() - ultimo_visto > TIEMPO_SIN_DIGITO and enviado not in (None, "-"):
                enviado = "-"
                print("PC  >> DIG:-")
                if esp:
                    esp.enviar("DIG:-")

            # ---- Respuestas de la ESP-A ----
            if esp:
                for linea in esp.lineas():
                    print("ESP >>", linea)
                    if linea.startswith("SPI:"):
                        estado_esp = linea

            cv2.putText(frame, f"ESP-A: {estado_esp}", (10, alto - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)
            cv2.imshow('Reconocimiento de digitos', frame)

            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord('q'):
                break
            if tecla == ord('e') and ultimo_estable is not None:
                mensaje = f"DIG:{ultimo_estable},{int(ultima_conf)}"
                print("PC  >>", mensaje, "(reenvío)")
                if esp:
                    esp.enviar(mensaje)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if esp:
            esp.cerrar()


if __name__ == "__main__":
    main()
