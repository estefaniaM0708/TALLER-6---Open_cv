"""
================================================================
 ACTIVIDAD 6 - PUNTO 1
 Teclado + LCD I2C (ESP32)  ->  brazo robótico dibujando en PyBullet
 dibujar_brazo_teclado.py
================================================================
 Flujo:
   1. La ESP32 envía "NUM:123" cuando se presiona '#' en el teclado.
   2. OpenCV "escribe" el número en una imagen y saca su CONTORNO
      (cv2.putText + cv2.findContours)  -> número "hueco", como en
      el ejemplo de la guía.
   3. Cada punto del contorno se pasa a coordenadas de la pizarra y,
      con la cinemática inversa del brazo (brazo.urdf), se calculan
      los ángulos de joint_1, joint_2 y la extensión de joint_gripper.
   4. El brazo recorre el contorno apoyando la pinza en la pizarra;
      el trazo se dibuja en PyBullet y en una ventana de OpenCV
      ("Lienzo"), que al final se guarda como dibujo_<numero>.png.
   5. El PC le responde a la ESP32 "LCD:..." para mostrar el estado.

 Si la ESP32 no está conectada se activa el MODO DEMO: se escribe
 en la ventana "Lienzo" con el teclado del PC (mismas teclas que el
 teclado 4x4: dígitos, '#'/Enter = dibujar, '*'/Retroceso = borrar,
 a = repetir, b = borrar pizarra, c = home, q = salir).

 Requisitos:
   pip install pybullet pyserial opencv-python numpy

 Uso:
   python dibujar_brazo_teclado.py                 (ESP32 en PUERTO_SERIE)
   python dibujar_brazo_teclado.py --puerto COM5
   python dibujar_brazo_teclado.py --demo          (sin ESP32)
   python dibujar_brazo_teclado.py --numero 2026   (dibuja y termina)

 IMPORTANTE: cierra Thonny antes de ejecutar (libera el puerto COM).
================================================================
"""

import argparse
import math
import os
import time

import cv2
import numpy as np
import pybullet as p
import pybullet_data

try:
    import serial
except ImportError:
    serial = None

# ------------------------------------------------------------------
# CONFIGURACIÓN
# ------------------------------------------------------------------
PUERTO_SERIE = "COM3"
BAUDRATE = 115200
CARPETA = os.path.dirname(os.path.abspath(__file__))

# ---- Geometría tomada de brazo.urdf ----
BASE_Z = 0.15                                # el robot se carga en z = 0.15
HOMBRO = np.array([0.0, 0.0, BASE_Z + 0.15 + 0.35])   # eje de joint_2 (z = 0.65)
L_BRAZO2 = 0.30                              # longitud del brazo superior
L_PUNTA = 0.12                               # base de la pinza -> punta de los dedos
L0 = L_BRAZO2 + L_PUNTA                      # alcance con la pinza recogida
LIM_J1 = (-2.5, 2.5)
LIM_J2 = (-2.0, 2.0)
LIM_EXT = (0.0, 0.15)                        # joint_gripper (prismático)
FUERZA = {"joint_1": 100, "joint_2": 80, "joint_gripper": 30,
          "joint_dedo_izq": 20, "joint_dedo_der": 20}
VEL_MAX = {"joint_1": 1.5, "joint_2": 1.2, "joint_gripper": 0.5,     # <limit velocity>
           "joint_dedo_izq": 0.5, "joint_dedo_der": 0.5}

# ---- Pizarra (plano vertical x = X_PIZARRA, frente al brazo) ----
X_PIZARRA = 0.48          # distancia horizontal del hombro a la pizarra
LEVANTE = 0.03            # cuánto se aleja la punta para "levantar el lápiz"
PIZ_ANCHO, PIZ_ALTO = 0.40, 0.28     # zona blanca
MARCO = 0.03                          # marco negro
ANCHO_UTIL, ALTO_UTIL = 0.30, 0.17    # tamaño máximo del número
PASO = 0.004              # distancia entre puntos del trazo (m)
TOL = 0.0015              # error aceptado para pasar al siguiente punto (m)
MAX_PASOS_PUNTO = 40      # pasos de simulación máximos por punto

# ---- Lienzo OpenCV ----
LZ_W, LZ_H, LZ_M = 640, 480, 40       # ancho, alto y marco en píxeles
COLOR_TRAZO_PB = [0.05, 0.15, 0.7]    # azul (PyBullet, 0..1)
COLOR_TRAZO_CV = (160, 40, 10)        # azul (OpenCV, BGR)

# True  -> la pizarra se borra sola antes de cada número nuevo
# False -> los números se van acumulando (se borra con la tecla B)
BORRAR_ANTES_DE_DIBUJAR = True


def recortar(v, lim):
    return max(lim[0], min(lim[1], v))


# ------------------------------------------------------------------
# 1. CINEMÁTICA DEL BRAZO (R-R-P, tipo esférico)
#    punta = HOMBRO + (L0 + d) * (sen q2 cos q1, sen q2 sen q1, cos q2)
# ------------------------------------------------------------------
def cinematica_inversa(punto):
    """Punto (x, y, z) del mundo -> (q1, q2, d, alcanzable)."""
    v = np.asarray(punto) - HOMBRO
    r = float(np.linalg.norm(v))
    q1 = math.atan2(v[1], v[0])
    q2 = math.atan2(math.hypot(v[0], v[1]), v[2])
    d = r - L0
    ok = (LIM_J1[0] <= q1 <= LIM_J1[1] and LIM_J2[0] <= q2 <= LIM_J2[1]
          and LIM_EXT[0] <= d <= LIM_EXT[1])
    return recortar(q1, LIM_J1), recortar(q2, LIM_J2), recortar(d, LIM_EXT), ok


def pizarra_a_mundo(u, v, separacion=0.0):
    """(u, v) en la pizarra [m] (u a la derecha, v hacia arriba, vistos
    desde detrás del brazo) -> punto 3D. separacion > 0 aleja la punta."""
    return np.array([X_PIZARRA - separacion, -u, HOMBRO[2] + v])


def mundo_a_lienzo(pt):
    """Punto 3D sobre la pizarra -> píxel del lienzo OpenCV."""
    u, v = -pt[1], pt[2] - HOMBRO[2]
    iw, ih = LZ_W - 2 * LZ_M, LZ_H - 2 * LZ_M
    px = LZ_M + (u / PIZ_ANCHO + 0.5) * iw
    py = LZ_M + (0.5 - v / PIZ_ALTO) * ih
    return int(round(px)), int(round(py))


# ------------------------------------------------------------------
# 2. VISIÓN (OpenCV): número -> contornos -> trazos en metros
# ------------------------------------------------------------------
def remuestrear(puntos, paso):
    """Reparte los puntos de un contorno cada 'paso' metros."""
    seg = np.linalg.norm(np.diff(puntos, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < paso:
        return puntos
    n = int(s[-1] / paso) + 1
    si = np.linspace(0, s[-1], n)
    return np.column_stack([np.interp(si, s, puntos[:, 0]),
                            np.interp(si, s, puntos[:, 1])])


def trazos_del_numero(texto):
    """Devuelve una lista de trazos (arrays Nx2 en metros, coordenadas
    de pizarra) con el contorno del número, como en la guía."""
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    escala, grosor = 8, 42
    (tw, th), base = cv2.getTextSize(texto, fuente, escala, grosor)
    m = grosor + 20
    img = np.zeros((th + base + 2 * m, tw + 2 * m), np.uint8)
    cv2.putText(img, texto, (m, m + th), fuente, escala, 255, grosor, cv2.LINE_AA)
    _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

    # RETR_CCOMP: contornos externos + huecos internos (0, 4, 6, 8, 9)
    contornos, _ = cv2.findContours(img, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    contornos = [c for c in contornos if cv2.contourArea(c) > 150]
    todos = np.vstack([c[:, 0, :] for c in contornos]).astype(float)
    x0, y0 = todos.min(axis=0)
    x1, y1 = todos.max(axis=0)
    s = min(ANCHO_UTIL / (x1 - x0), ALTO_UTIL / (y1 - y0))   # px -> m
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    trazos = []
    for c in contornos:
        c = cv2.approxPolyDP(c, 1.5, True)[:, 0, :].astype(float)   # suaviza escalones
        pts = np.column_stack([(c[:, 0] - cx) * s, -(c[:, 1] - cy) * s])
        pts = np.vstack([pts, pts[:1]])                             # cerrar contorno
        trazos.append(remuestrear(pts, PASO))

    # Orden: empezar por el trazo más a la izquierda y luego el más cercano
    ordenados = [trazos.pop(int(np.argmin([t[:, 0].min() for t in trazos])))]
    while trazos:
        fin = ordenados[-1][-1]
        k = int(np.argmin([np.linalg.norm(t[0] - fin) for t in trazos]))
        ordenados.append(trazos.pop(k))
    return ordenados


def puntos_de_trayectoria(trazos):
    """Convierte los trazos en la ruta del brazo. Cada elemento es
    ("P", punto3D)        -> ir a ese punto en el espacio (cinemática inversa)
    ("Q", (q1, q2, d))    -> ir a esos ángulos (movimientos seguros)
    Para llegar/salir de la pizarra la pinza se recoge (d = 0): así la
    punta gira en una esfera de radio L0 que nunca toca la pizarra."""
    ruta = []
    u0, v0 = trazos[0][0]
    q1, q2, _, _ = cinematica_inversa(pizarra_a_mundo(u0, v0, LEVANTE))
    ruta.append(("Q", (q1, q2, 0.0)))                       # orientar con la pinza recogida
    for t in trazos:
        u0, v0 = t[0]
        ruta.append(("P", pizarra_a_mundo(u0, v0, LEVANTE)))   # encima del inicio
        for k in range(1, 6):                                  # bajar el lápiz despacio
            ruta.append(("P", pizarra_a_mundo(u0, v0, LEVANTE * (1 - k / 5))))
        for u, v in t[1:]:
            ruta.append(("P", pizarra_a_mundo(u, v)))
        uf, vf = t[-1]
        ruta.append(("P", pizarra_a_mundo(uf, vf, LEVANTE)))   # levantar
    q1, q2, _, _ = cinematica_inversa(ruta[-1][1])
    ruta.append(("Q", (q1, q2, 0.0)))                       # recoger la pinza
    ruta.append(("Q", (0.0, 0.0, 0.0)))                     # volver a reposo
    return ruta


# ------------------------------------------------------------------
# 3. SIMULACIÓN
# ------------------------------------------------------------------
class Simulacion:
    def __init__(self, con_gui=True):
        self.con_gui = con_gui
        p.connect(p.GUI if con_gui else p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.8)
        if con_gui:
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
            p.resetDebugVisualizerCamera(cameraDistance=1.2, cameraYaw=-40,
                                         cameraPitch=-22,
                                         cameraTargetPosition=[0.25, 0, 0.6])
        p.loadURDF("plane.urdf")
        self.robot = p.loadURDF(os.path.join(CARPETA, "brazo.urdf"),
                                [0, 0, BASE_Z], useFixedBase=True)
        self.jidx = {p.getJointInfo(self.robot, i)[1].decode(): i
                     for i in range(p.getNumJoints(self.robot))}
        self.link_pinza = self.jidx["joint_gripper"]   # link = gripper_base
        self._crear_pizarra()

        self.lineas = []
        self.lienzo = self._lienzo_vacio()
        self.ruta, self.i_ruta, self.pasos_punto = [], 0, 0
        self.ultimo_contacto = None
        self.numero_actual = None
        self.ultimo_numero = None
        self.volviendo_home = False
        self.mover(0.0, 0.0, 0.0)
        for _ in range(240):
            p.stepSimulation()

    def _crear_pizarra(self):
        """Pizarra blanca con marco negro (solo visual, sin colisión)."""
        esp = 0.01
        cx = X_PIZARRA + esp / 2
        blanco = p.createVisualShape(p.GEOM_BOX, halfExtents=[esp / 2, PIZ_ANCHO / 2, PIZ_ALTO / 2],
                                     rgbaColor=[1, 1, 1, 1])
        negro = p.createVisualShape(p.GEOM_BOX,
                                    halfExtents=[esp / 2, PIZ_ANCHO / 2 + MARCO, PIZ_ALTO / 2 + MARCO],
                                    rgbaColor=[0.05, 0.05, 0.05, 1])
        p.createMultiBody(0, -1, blanco, [cx, 0, HOMBRO[2]])
        p.createMultiBody(0, -1, negro, [cx + 0.006, 0, HOMBRO[2]])
        # patas de la pizarra
        pata = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.01, 0.01, (HOMBRO[2] - PIZ_ALTO / 2) / 2],
                                   rgbaColor=[0.4, 0.4, 0.4, 1])
        for y in (-PIZ_ANCHO / 2, PIZ_ANCHO / 2):
            p.createMultiBody(0, -1, pata, [cx + 0.02, y, (HOMBRO[2] - PIZ_ALTO / 2) / 2])

    def _lienzo_vacio(self):
        img = np.zeros((LZ_H, LZ_W, 3), np.uint8)
        cv2.rectangle(img, (LZ_M, LZ_M), (LZ_W - LZ_M, LZ_H - LZ_M), (255, 255, 255), -1)
        return img

    # ---------- control ----------
    def mover(self, q1, q2, d):
        objetivos = {"joint_1": q1, "joint_2": q2, "joint_gripper": d,
                     "joint_dedo_izq": 0.0, "joint_dedo_der": 0.0}   # pinza cerrada = "lápiz"
        for nombre, q in objetivos.items():
            p.setJointMotorControl2(self.robot, self.jidx[nombre], p.POSITION_CONTROL,
                                    targetPosition=q, force=FUERZA[nombre],
                                    maxVelocity=VEL_MAX[nombre],
                                    positionGain=0.4, velocityGain=1.0)

    def punta(self):
        """Posición real de la punta de la pinza (cinemática directa de PyBullet)."""
        est = p.getLinkState(self.robot, self.link_pinza, computeForwardKinematics=True)
        pos, _ = p.multiplyTransforms(est[4], est[5], [0, 0, L_PUNTA], [0, 0, 0, 1])
        return np.array(pos)

    # ---------- órdenes ----------
    def dibujar(self, numero):
        trazos = trazos_del_numero(numero)
        ruta = puntos_de_trayectoria(trazos)
        fuera = sum(not cinematica_inversa(x)[3] for tipo, x in ruta if tipo == "P")
        if fuera:
            print(f"Aviso: {fuera} puntos fuera del alcance (se recortan).")
        self.ruta, self.i_ruta, self.pasos_punto = ruta, 0, 0
        self.numero_actual = numero
        self.ultimo_numero = numero
        self.volviendo_home = False
        print(f"Dibujando {numero}: {len(trazos)} trazos, {len(ruta)} puntos")

    def borrar(self):
        for i in self.lineas:
            p.removeUserDebugItem(i)
        self.lineas = []
        self.lienzo = self._lienzo_vacio()

    def home(self):
        q1, q2, _ = self.articulaciones()
        self.ruta = [("Q", (q1, q2, 0.0)), ("Q", (0.0, 0.0, 0.0))]
        self.i_ruta, self.pasos_punto = 0, 0
        self.numero_actual = None

    def ocupado(self):
        return self.i_ruta < len(self.ruta)

    # ---------- un paso de simulación ----------
    def paso(self):
        """Avanza la simulación. Devuelve el número recién terminado o None."""
        terminado = None
        if self.ocupado():
            tipo, obj = self.ruta[self.i_ruta]
            if tipo == "P":
                q1, q2, d, _ = cinematica_inversa(obj)
            else:
                q1, q2, d = obj
            self.mover(q1, q2, d)

        p.stepSimulation()

        # ¿La punta está apoyada en la pizarra (y dentro de la zona blanca)? -> tinta
        tip = self.punta()
        u, v = -tip[1], tip[2] - HOMBRO[2]
        tocando = (abs(tip[0] - X_PIZARRA) < 0.003 and abs(u) < PIZ_ANCHO / 2
                   and abs(v) < PIZ_ALTO / 2)
        if tocando:
            if self.ultimo_contacto is not None:
                if np.linalg.norm(tip - self.ultimo_contacto) > 0.002:
                    a = self.ultimo_contacto.copy(); a[0] = X_PIZARRA - 0.002
                    b = tip.copy(); b[0] = X_PIZARRA - 0.002
                    if self.con_gui:
                        self.lineas.append(p.addUserDebugLine(a, b, COLOR_TRAZO_PB, 3, 0))
                    cv2.line(self.lienzo, mundo_a_lienzo(a), mundo_a_lienzo(b),
                             COLOR_TRAZO_CV, 2, cv2.LINE_AA)
                    self.ultimo_contacto = tip
            else:
                self.ultimo_contacto = tip
        else:
            self.ultimo_contacto = None

        # ¿Llegó al objetivo?
        if self.ocupado():
            tipo, obj = self.ruta[self.i_ruta]
            self.pasos_punto += 1
            if tipo == "P":
                llego = np.linalg.norm(tip - obj) < TOL
                limite = MAX_PASOS_PUNTO
            else:
                llego = max(abs(a - b) for a, b in zip(self.articulaciones(), obj)) < 0.01
                limite = 1200
            if llego or self.pasos_punto >= limite:
                self.i_ruta += 1
                self.pasos_punto = 0
                if not self.ocupado():
                    terminado = self.numero_actual
                    self.numero_actual = None
        return terminado

    def articulaciones(self):
        return [p.getJointState(self.robot, self.jidx[n])[0]
                for n in ("joint_1", "joint_2", "joint_gripper")]


# ------------------------------------------------------------------
# 4. COMUNICACIÓN CON LA ESP32
# ------------------------------------------------------------------
class EnlaceESP32:
    def __init__(self, puerto):
        self.ser = serial.Serial(puerto, BAUDRATE, timeout=0)
        time.sleep(2)                       # la ESP32 se reinicia al abrir el puerto
        self.ser.reset_input_buffer()
        self.buffer = ""

    def lineas(self):
        """Lee sin bloquear las líneas completas que llegaron."""
        datos = self.ser.read(self.ser.in_waiting or 1)
        if datos:
            self.buffer += datos.decode("utf-8", errors="ignore")
        *completas, self.buffer = self.buffer.replace("\r", "").split("\n")
        return [l.strip() for l in completas if l.strip()]

    def lcd(self, texto):
        self.ser.write(("LCD:" + texto[:16] + "\n").encode())

    def cerrar(self):
        self.ser.close()


# ------------------------------------------------------------------
# 5. PROGRAMA PRINCIPAL
# ------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", default=PUERTO_SERIE)
    ap.add_argument("--demo", action="store_true", help="sin ESP32 (teclado del PC)")
    ap.add_argument("--numero", help="dibuja este número, guarda la imagen y termina")
    ap.add_argument("--sin-gui", action="store_true", help="PyBullet en modo DIRECT")
    args = ap.parse_args()

    esp = None
    if not args.demo and not args.numero:
        if serial is None:
            print("pyserial no está instalado -> MODO DEMO")
        else:
            try:
                print(f"Conectando a la ESP32 en {args.puerto}...")
                esp = EnlaceESP32(args.puerto)
                print("ESP32 conectada.")
            except Exception as e:
                print(f"No se pudo abrir {args.puerto} ({e}) -> MODO DEMO")

    sim = Simulacion(con_gui=not args.sin_gui)
    mostrar_lienzo = not args.sin_gui
    pendientes = []                 # órdenes en cola: ("NUM", "12"), ("CMD", "B")...
    entrada_demo = ""
    if args.numero:
        pendientes.append(("NUM", args.numero))
    if esp:
        esp.lcd("PC listo")
    elif not args.numero:
        print("\nMODO DEMO: haz clic en la ventana 'Lienzo' y escribe un número,")
        print("luego Enter (o #). *=borrar cifra, a=repetir, b=borrar pizarra, c=home, q=salir\n")

    def avisar(txt):
        print(txt)
        if esp:
            esp.lcd(txt)

    paso = 0
    try:
        while True:
            # ---- órdenes de la ESP32 ----
            if esp:
                for linea in esp.lineas():
                    print(f"  ESP32 >> {linea}")          # ver todo lo que llega (diagnóstico)
                    if linea.startswith("NUM:"):
                        pendientes.append(("NUM", linea[4:]))
                    elif linea.startswith("CMD:"):
                        pendientes.append(("CMD", linea[4:]))

            # ---- ejecutar la siguiente orden cuando el brazo esté libre ----
            if pendientes and not sim.ocupado():
                tipo, valor = pendientes.pop(0)
                if tipo == "NUM" and valor.isdigit():
                    if BORRAR_ANTES_DE_DIBUJAR:
                        sim.borrar()                      # pizarra y lienzo limpios
                    sim.dibujar(valor)
                    avisar(f"Dibujando {valor}")
                elif tipo == "CMD" and valor == "A":
                    if sim.ultimo_numero:
                        sim.borrar()
                        sim.dibujar(sim.ultimo_numero)
                        avisar(f"Repite {sim.ultimo_numero}")
                    else:
                        avisar("Nada que repetir")
                elif tipo == "CMD" and valor == "B":
                    sim.borrar()
                    avisar("Pizarra limpia")
                elif tipo == "CMD" and valor == "C":
                    sim.home()
                    avisar("Brazo en home")

            # ---- simulación ----
            terminado = sim.paso()
            if terminado:
                ruta_img = os.path.join(CARPETA, f"dibujo_{terminado}.png")
                cv2.imwrite(ruta_img, sim.lienzo)
                avisar(f"Listo! {terminado}")
                print(f"  lienzo guardado en {ruta_img}")
                if args.numero:
                    for _ in range(240):      # deja que vuelva a home
                        p.stepSimulation()
                    break

            # ---- ventana del lienzo (y teclado virtual en modo demo) ----
            paso += 1
            if mostrar_lienzo and paso % 4 == 0:
                vista = sim.lienzo.copy()
                texto = (f"Dibujando: {sim.numero_actual}" if sim.numero_actual
                         else (f"Numero: {entrada_demo}_" if not esp else "Esperando teclado..."))
                cv2.putText(vista, texto, (LZ_M, 28), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.imshow("Lienzo", vista)
                k = cv2.waitKey(1) & 0xFF
                if k != 255 and not esp:
                    ch = chr(k).lower()
                    if ch.isdigit() and len(entrada_demo) < 4:
                        entrada_demo += ch
                    elif ch in ("*", "\b") or k == 127:
                        entrada_demo = entrada_demo[:-1]
                    elif ch in ("#", "\r", "\n") and entrada_demo:
                        pendientes.append(("NUM", entrada_demo))
                        entrada_demo = ""
                    elif ch in "abc":
                        pendientes.append(("CMD", ch.upper()))
                    elif ch == "q":
                        break

            if not args.sin_gui:
                time.sleep(1 / 240)
                if not p.isConnected():
                    break
    except KeyboardInterrupt:
        print("\nDetenido por el usuario.")
    except p.error:
        print("\nSe cerró la ventana de PyBullet.")
    finally:
        if esp:
            esp.cerrar()
        if p.isConnected():
            p.disconnect()
        if mostrar_lienzo:
            cv2.destroyAllWindows()
        print("Conexiones cerradas.")


if __name__ == "__main__":
    main()
