# -*- coding: utf-8 -*-
"""
SuperCapa v3 - Control por voz con cuadricula superpuesta.

Mejoras v3 sobre v2:
  * Cuadricula solo en lateral superior izquierdo (zona compacta),
    texto gris con borde negro, fuente mas pequeña, casillas transparentes.
  * Comando TEXTO: activa modo dictado directo en la aplicacion activa.
    - Todo lo que se dice se teclea directamente donde este el cursor.
    - "borrar palabra" / "borrar todo" / "QUITAR TEXTO".
  * Puntero moto negra de competicion.
  * Rejilla sobre barra de tareas: SetWindowPos con HWND_TOPMOST
    reforzado cada 150 ms + tecnica Shell_TrayWnd para colarse encima.
  * Control del raton por voz (respaldo cuando la barra tapa la rejilla):
    "arriba/abajo/izquierda/derecha [N pasos]"
    "mas rapido" / "mas despacio"   ajusta el paso
    "clic" / "doble clic" / "clic derecho"
"""

import ctypes
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

# DPI awareness - debe ejecutarse ANTES de crear ventanas
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pyautogui
import speech_recognition as sr
import keyboard

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# =====================================================================
#  CONFIGURACION
# =====================================================================
COLS = 20
ROWS = 20
LETTERS = "ABCDEFGHIJKLMNOPQRST"
GRID_LINE_COLOR  = "#888888"       # gris para las lineas
GRID_TEXT_COLOR  = "#FFFFFF"       # blanco para las letras
GRID_TEXT_OUTLINE = "#000000"      # contorno negro
TRANSPARENT_KEY = "#FF00FF"
LANGUAGE = "es-ES"
TOPMOST_REFRESH_MS = 150   # refuerzo agresivo para superar la barra de tareas

# Paso inicial del raton en modo direccional (pixeles por comando)
MOUSE_STEP_DEFAULT = 60
MOUSE_STEP_MIN     = 10
MOUSE_STEP_MAX     = 300
MOUSE_STEP_FACTOR  = 1.6   # multiplicador para "mas rapido" / "mas despacio"

# =====================================================================
#  DICCIONARIO DE INTENCIONES
# =====================================================================
INTENTS = {
    "QUIT": [
        "salir del programa", "cerrar programa", "cerrar supercapa",
        "apagar programa", "apagar supercapa", "adios supercapa",
    ],
    "HIDE_GRID": [
        "ocultar rejilla", "esconder rejilla", "quitar rejilla",
        "quita la rejilla", "quita la cuadricula", "quita la cuadrícula",
        "oculta la rejilla", "ocultar cuadricula", "ocultar cuadrícula",
        "esconder cuadricula", "esconder cuadrícula",
    ],
    "SHOW_GRID": [
        "mostrar rejilla", "muestra la rejilla", "activar rejilla",
        "activa la rejilla", "rejilla", "cuadricula", "cuadrícula",
        "mostrar capa", "activar capa", "muestra la capa",
    ],
    "CLOSE_KEYBOARD": [
        "cerrar teclado", "quitar teclado", "ocultar teclado",
        "quita el teclado", "cierra el teclado",
    ],
    "OPEN_KEYBOARD": [
        "abrir teclado", "teclado en pantalla", "mostrar teclado",
        "muestra el teclado", "activar teclado", "saca el teclado",
        "pon el teclado", "teclado",
    ],
    "CLOSE_WINDOW": [
        "cerrar ventana", "cierra ventana", "cierra la ventana",
        "cierra esa ventana", "cierra esta ventana", "cierra esto",
        "cierralo", "ciérralo", "cierralo todo", "cerrar esto",
        "quita esto", "quitalo", "quítalo",
    ],
    "MAXIMIZE": [
        "maximizar", "maximiza", "maximízalo", "maximizalo",
        "ponlo en grande", "ponlo grande", "pantalla completa",
        "hazlo grande", "agrandalo", "agrándalo", "agranda la ventana",
    ],
    "MINIMIZE": [
        "minimizar", "minimiza", "minimizalo", "minimízalo",
        "ponlo pequeño", "ponlo pequeno", "hazlo pequeño",
        "esconde la ventana", "ocultar ventana",
    ],
    "SWITCH_WINDOW": [
        "cambiar ventana", "cambiar de ventana", "siguiente ventana",
        "otra ventana", "cambia de ventana",
    ],
    "OPEN_EXPLORER": [
        "abrir explorador", "abre el explorador", "abre explorador",
        "explorador de archivos", "abrir archivos", "abre los archivos",
        "abre una carpeta", "abrir una carpeta", "mis archivos",
    ],
    "SHOW_DESKTOP": [
        "mostrar escritorio", "muestra el escritorio", "ver escritorio",
        "ir al escritorio", "escritorio",
    ],
    "PROJECT": [
        "duplicar pantalla", "extender pantalla", "proyectar pantalla",
        "segunda pantalla", "proyección", "proyeccion",
    ],
    "COPY":   ["copiar", "copia eso", "copia esto", "copialo", "cópialo", "copia"],
    "PASTE":  ["pegar", "pega eso", "pega esto", "pegalo", "pégalo", "pega"],
    "CUT":    ["cortar", "corta eso", "corta esto", "cortalo", "córtalo", "corta"],
    "DELETE": ["eliminar", "borrar", "suprimir", "elimina eso", "borra eso",
               "eliminalo", "bórralo", "borralo", "borra", "elimina"],
    "SELECT_ALL": [
        "seleccionar todo", "selecciona todo", "seleccionar todos",
        "selecciona todos", "ctrl a", "control a",
    ],
    "ENTER": [
        "enter", "intro", "confirmar", "confirma", "aceptar", "acepta",
        "enviar", "envía", "envía", "buscar", "busca",
        "ir", "navegar", "abrir dirección", "abrir pagina",
    ],
    "DOUBLE_CLICK": [
        "doble clic", "doble click", "doble pica", "doble pulsacion",
    ],
    "RIGHT_CLICK": [
        "clic derecho", "click derecho", "boton derecho", "botón derecho",
        "menu contextual", "menú contextual", "menu", "menú",
    ],
    "LEFT_CLICK": [
        "clic izquierdo", "click izquierdo", "clic", "click",
        "pica", "pulsa", "pincha", "toca",
    ],
    # NUEVO: Dictado de texto
    "START_DICTATION": [
        "texto", "iniciar texto", "empieza texto", "modo texto",
        "escribe texto", "dictado",
    ],
    "STOP_DICTATION": [
        "quitar texto", "detener texto", "parar texto", "cerrar texto",
        "fin texto", "salir texto", "quita el texto", "para el texto",
    ],
    "DELETE_WORD": [
        "borrar palabra", "borra la palabra", "borra palabra",
        "quitar palabra", "eliminar palabra",
    ],
    "CLEAR_TEXT": [
        "borrar todo", "borra todo", "limpiar todo", "limpia todo",
        "eliminar todo", "elimina todo", "borra el texto",
    ],
    # Control direccional del raton
    "MOUSE_UP": [
        "arriba", "sube", "subir", "hacia arriba", "mueve arriba",
        "mueve el raton arriba", "puntero arriba",
    ],
    "MOUSE_DOWN": [
        "abajo", "baja", "bajar", "hacia abajo", "mueve abajo",
        "mueve el raton abajo", "puntero abajo",
    ],
    "MOUSE_LEFT": [
        "izquierda", "mueve izquierda", "hacia la izquierda",
        "mueve el raton izquierda", "puntero izquierda",
    ],
    "MOUSE_RIGHT": [
        "derecha", "mueve derecha", "hacia la derecha",
        "mueve el raton derecha", "puntero derecha",
    ],
    "MOUSE_FASTER": [
        "mas rapido", "más rápido", "mas velocidad", "aumenta velocidad",
        "acelera", "paso grande", "paso rapido",
    ],
    "MOUSE_SLOWER": [
        "mas despacio", "más despacio", "menos velocidad", "reduce velocidad",
        "decelera", "paso pequeño", "paso lento",
    ],
}

INTENT_PRIORITY = [
    "QUIT",
    "STOP_DICTATION", "DELETE_WORD", "CLEAR_TEXT",
    "HIDE_GRID", "SHOW_GRID",
    "CLOSE_KEYBOARD", "OPEN_KEYBOARD",
    "CLOSE_WINDOW", "MAXIMIZE", "MINIMIZE", "SWITCH_WINDOW",
    "OPEN_EXPLORER", "SHOW_DESKTOP", "PROJECT",
    "COPY", "PASTE", "CUT", "DELETE", "SELECT_ALL", "ENTER",
    "MOUSE_FASTER", "MOUSE_SLOWER",
    "MOUSE_UP", "MOUSE_DOWN", "MOUSE_LEFT", "MOUSE_RIGHT",
    "DOUBLE_CLICK", "RIGHT_CLICK", "LEFT_CLICK",
    "START_DICTATION",
]


def classify_intent(text):
    t = " " + text.lower().strip() + " "
    t = re.sub(r"\s+", " ", t)
    for intent in INTENT_PRIORITY:
        for trigger in INTENTS[intent]:
            if f" {trigger} " in t or t.strip() == trigger \
               or t.startswith(f" {trigger} ") or t.endswith(f" {trigger} ") \
               or trigger in t:
                return intent
    return None


# =====================================================================
#  PARSEO DE COORDENADAS
# =====================================================================
NUMBERS_ES = {
    "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciséis": 16, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19, "veinte": 20,
}
LETTERS_ES = {
    "a": "A", "alfa": "A", "alpha": "A",
    "b": "B", "be": "B", "bravo": "B",
    "c": "C", "ce": "C", "se": "C", "charlie": "C",
    "d": "D", "de": "D", "delta": "D",
    "e": "E", "echo": "E",
    "f": "F", "efe": "F", "foxtrot": "F",
    "g": "G", "ge": "G", "je": "G", "golf": "G",
    "h": "H", "hache": "H", "ache": "H", "hotel": "H",
    "i": "I", "india": "I",
    "j": "J", "jota": "J", "juliet": "J",
    "k": "K", "ka": "K", "kilo": "K",
    "l": "L", "ele": "L", "lima": "L",
    "m": "M", "eme": "M", "mike": "M",
    "n": "N", "ene": "N", "november": "N",
    "o": "O", "oscar": "O",
    "p": "P", "pe": "P", "papa": "P", "papá": "P",
    "q": "Q", "cu": "Q", "ku": "Q", "quebec": "Q",
    "r": "R", "erre": "R", "ere": "R", "romeo": "R",
    "s": "S", "ese": "S", "sierra": "S",
    "t": "T", "te": "T", "té": "T", "tango": "T",
}


def parse_coordinate(text):
    t = text.lower()
    m = re.search(
        r"\b(alfa|alpha|bravo|charlie|delta|echo|foxtrot|golf|hotel|india|"
        r"juliet|kilo|lima|mike|november|oscar|papa|quebec|romeo|sierra|tango|"
        r"hache|ache|jota|efe|erre|ere|eme|ene|ele|ese|"
        r"[a-t]|be|ce|se|de|ge|je|ka|cu|ku|pe|te)\s*(\d{1,2})\b",
        t,
    )
    if m:
        lw = m.group(1)
        letter = LETTERS_ES.get(lw)
        if letter is None and len(lw) == 1:
            letter = lw.upper()
        number = int(m.group(2))
        if letter in LETTERS and 1 <= number <= ROWS:
            return (LETTERS.index(letter), number - 1)

    words = re.findall(r"[a-záéíóúñü]+|\d+", t)
    letter = None
    number = None
    for w in words:
        if letter is None:
            if w in LETTERS_ES:
                letter = LETTERS_ES[w]
            elif len(w) == 1 and w.upper() in LETTERS:
                letter = w.upper()
        if number is None:
            if w in NUMBERS_ES and 1 <= NUMBERS_ES[w] <= ROWS:
                number = NUMBERS_ES[w]
            elif w.isdigit():
                n = int(w)
                if 1 <= n <= ROWS:
                    number = n
    if letter and number:
        return (LETTERS.index(letter), number - 1)
    return None


# =====================================================================
#  ACCIONES DEL SISTEMA
# =====================================================================
def act_left_click():    pyautogui.click()
def act_double_click():  pyautogui.doubleClick()
def act_right_click():   pyautogui.rightClick()
def act_copy():          pyautogui.hotkey("ctrl", "c")
def act_paste():         pyautogui.hotkey("ctrl", "v")
def act_cut():           pyautogui.hotkey("ctrl", "x")
def act_delete():        pyautogui.press("delete")
def act_select_all():    pyautogui.hotkey("ctrl", "a")
def act_enter():         pyautogui.press("enter")
def act_close_window():  pyautogui.hotkey("alt", "f4")
def act_minimize():      pyautogui.hotkey("win", "down")
def act_maximize():      pyautogui.hotkey("win", "up")
def act_switch_window(): pyautogui.hotkey("alt", "tab")
def act_open_explorer(): pyautogui.hotkey("win", "e")
def act_show_desktop():  pyautogui.hotkey("win", "d")
def act_project():       pyautogui.hotkey("win", "p")


def act_open_keyboard():
    try:
        paths = [
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Sysnative", "osk.exe"),
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "osk.exe"),
            "osk.exe",
        ]
        for p in paths:
            try:
                subprocess.Popen([p]); return
            except Exception:
                continue
    except Exception as e:
        print(f"[aviso] no se pudo abrir osk.exe: {e}")


def act_close_keyboard():
    try:
        subprocess.run(["taskkill", "/IM", "osk.exe", "/F"], capture_output=True, timeout=3)
    except Exception as e:
        print(f"[aviso] no se pudo cerrar osk.exe: {e}")


INTENT_ACTIONS = {
    "LEFT_CLICK":    act_left_click,
    "DOUBLE_CLICK":  act_double_click,
    "RIGHT_CLICK":   act_right_click,
    "COPY":          act_copy,
    "PASTE":         act_paste,
    "CUT":           act_cut,
    "DELETE":        act_delete,
    "SELECT_ALL":    act_select_all,
    "ENTER":         act_enter,
    "CLOSE_WINDOW":  act_close_window,
    "MINIMIZE":      act_minimize,
    "MAXIMIZE":      act_maximize,
    "SWITCH_WINDOW": act_switch_window,
    "OPEN_EXPLORER": act_open_explorer,
    "SHOW_DESKTOP":  act_show_desktop,
    "PROJECT":       act_project,
    "OPEN_KEYBOARD": act_open_keyboard,
    "CLOSE_KEYBOARD":act_close_keyboard,
}


# =====================================================================
#  PUNTERO MOTO DE COMPETICION
# =====================================================================
class MotoCursor:
    """Ventana con imagen de moto que sigue al raton."""

    # SVG path simplificado de una moto de competicion vista de lado
    # Lo dibujamos en un canvas de 48x28 pixels
    MOTO_POINTS = {
        # (x, y) normalizados 0..1 para escalar
    }

    def __init__(self, master):
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=TRANSPARENT_KEY)
        try:
            self.win.attributes("-transparentcolor", TRANSPARENT_KEY)
        except Exception:
            self.win.attributes("-alpha", 0.95)

        self.W = 64
        self.H = 36
        self.canvas = tk.Canvas(
            self.win, width=self.W, height=self.H,
            bg=TRANSPARENT_KEY, highlightthickness=0, bd=0,
        )
        self.canvas.pack()
        self.win.geometry(f"{self.W}x{self.H}+0+0")

        self._draw_moto()
        self._apply_click_through()
        self._tracking = False

    def _draw_moto(self):
        """Dibuja una moto de competicion en negro con detalles."""
        c = self.canvas
        c.delete("all")
        W, H = self.W, self.H

        # === Ruedas ===
        # Rueda trasera
        c.create_oval(2, H-14, 18, H-1,   fill="#111111", outline="#333333", width=1)
        c.create_oval(5, H-11, 15, H-4,   fill="#222222", outline="")  # aro interior
        # Rueda delantera
        c.create_oval(W-20, H-14, W-4, H-1, fill="#111111", outline="#333333", width=1)
        c.create_oval(W-17, H-11, W-7, H-4, fill="#222222", outline="")

        # === Chasis / carroceria ===
        # Cuerpo bajo (bastidor)
        c.create_polygon(
            10, H-3,   14, H-12,  W-14, H-12,  W-10, H-3,
            fill="#1a1a1a", outline="#444444", width=1,
        )

        # Carenado lateral superior (forma aerodinámica)
        c.create_polygon(
            14, H-12,
            18, H-22,
            32, H-24,
            W-16, H-18,
            W-14, H-12,
            fill="#0d0d0d", outline="#555555", width=1,
        )

        # Carenado frontal (proa)
        c.create_polygon(
            W-20, H-22,
            W-14, H-12,
            W-10, H-14,
            W-16, H-24,
            fill="#1a1a1a", outline="#444444", width=1,
        )

        # Cola trasera
        c.create_polygon(
            12, H-16,
            14, H-24,
            20, H-22,
            18, H-14,
            fill="#111111", outline="#444444", width=1,
        )

        # === Piloto (casco + cuerpo agachado) ===
        # Cuerpo agachado
        c.create_polygon(
            20, H-22,
            28, H-28,
            38, H-26,
            W-18, H-22,
            W-16, H-18,
            30, H-20,
            fill="#0a0a0a", outline="#555555", width=1,
        )
        # Casco
        c.create_oval(20, H-30, 32, H-20, fill="#1a1a1a", outline="#666666", width=1)
        # Visor del casco
        c.create_arc(22, H-29, 30, H-22, start=20, extent=100,
                     style="chord", fill="#333333", outline="#888888", width=1)

        # === Detalles ===
        # Escape (tubo de escape)
        c.create_line(10, H-8, 6, H-6, 4, H-7, fill="#555555", width=2)
        c.create_line(4, H-7, 3, H-5, fill="#777777", width=1)

        # Horquilla delantera
        c.create_line(W-18, H-14, W-16, H-2, fill="#444444", width=2)
        c.create_line(W-16, H-14, W-14, H-2, fill="#333333", width=1)

        # Manillar
        c.create_line(W-20, H-22, W-17, H-20, fill="#555555", width=2)

        # Linea roja de decoracion (carena)
        c.create_line(18, H-19, W-17, H-19, fill="#CC0000", width=1)

        # Punto punta delantera (faro)
        c.create_oval(W-8, H-17, W-5, H-14, fill="#FFFF88", outline="")

    def _apply_click_through(self):
        self.win.update_idletasks()
        try:
            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED    = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE  = 0x08000000
            WS_EX_TOOLWINDOW  = 0x00000080
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            styles |= (WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles)
        except Exception as e:
            print(f"[aviso] moto click-through: {e}")

    def show(self):
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        self._tracking = True
        self._track()

    def hide(self):
        self._tracking = False
        self.win.withdraw()

    def _track(self):
        if not self._tracking:
            return
        try:
            x, y = pyautogui.position()
            # Offset: el punto de la rueda delantera es la punta del cursor
            self.win.geometry(f"+{x - self.W + 6}+{y - self.H + 4}")
            self.win.attributes("-topmost", True)
        except Exception:
            pass
        self.win.after(16, self._track)  # ~60 fps


def parse_step_count(text: str) -> int:
    """
    Extrae un numero de pasos de un comando direccional.
    Ej: 'arriba tres' -> 3,  'abajo 10' -> 10,  'derecha' -> 1
    """
    words = text.lower().split()
    for w in words:
        if w in NUMBERS_ES and NUMBERS_ES[w] > 0:
            return min(NUMBERS_ES[w], 20)
        if w.isdigit():
            return min(int(w), 20)
    return 1


# =====================================================================
#  UTILIDAD: FORZAR VENTANA ENCIMA DE LA BARRA DE TAREAS
# =====================================================================
_user32  = ctypes.windll.user32
_HWND_TOPMOST   = ctypes.c_void_p(-1)
_SWP_NOMOVE     = 0x0002
_SWP_NOSIZE     = 0x0001
_SWP_NOACTIVATE = 0x0010
_SWP_SHOWWINDOW = 0x0040


def _get_real_hwnd(tk_window) -> int:
    """Devuelve el HWND real de Windows para una ventana Tk."""
    # GetParent() devuelve el contenedor Win32 que Tk crea
    return _user32.GetParent(tk_window.winfo_id())


def force_topmost_over_taskbar(hwnd: int):
    """
    Llama a SetWindowPos con HWND_TOPMOST de forma directa (no a traves de Tk)
    para que la ventana quede por encima de la Shell, incluida la taskbar.
    """
    if not hwnd:
        return
    try:
        ctypes.windll.user32.SetWindowPos(
            hwnd,
            _HWND_TOPMOST,
            0, 0, 0, 0,
            _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOACTIVATE | _SWP_SHOWWINDOW,
        )
    except Exception:
        pass


# =====================================================================
#  CONTROL DEL RATON POR VOZ (modo direccional)
# =====================================================================
class VoiceMouseController:
    """
    Mueve el cursor del raton mediante comandos de voz direccionales.
    Util cuando la barra de tareas impide ver la cuadricula o como
    metodo complementario de navegacion fina.

    Comandos:
      "arriba [N]"      mueve N*paso pixeles hacia arriba
      "abajo [N]"       mueve N*paso pixeles hacia abajo
      "izquierda [N]"   mueve N*paso pixeles a la izquierda
      "derecha [N]"     mueve N*paso pixeles a la derecha
      "mas rapido"      aumenta el paso (x1.6)
      "mas despacio"    reduce el paso  (/1.6)

    N es opcional (1 si no se indica). Maximo 20 pasos por comando.
    """

    def __init__(self):
        self.step = MOUSE_STEP_DEFAULT

    def move(self, dx: int, dy: int):
        x, y = pyautogui.position()
        sw = pyautogui.size().width
        sh = pyautogui.size().height
        nx = max(0, min(sw - 1, x + dx))
        ny = max(0, min(sh - 1, y + dy))
        pyautogui.moveTo(nx, ny, duration=0.05)

    def up(self, n: int = 1):
        self.move(0, -self.step * n)

    def down(self, n: int = 1):
        self.move(0, self.step * n)

    def left(self, n: int = 1):
        self.move(-self.step * n, 0)

    def right(self, n: int = 1):
        self.move(self.step * n, 0)

    def faster(self):
        self.step = min(MOUSE_STEP_MAX, int(self.step * MOUSE_STEP_FACTOR))
        print(f"[raton] paso -> {self.step} px")

    def slower(self):
        self.step = max(MOUSE_STEP_MIN, int(self.step / MOUSE_STEP_FACTOR))
        print(f"[raton] paso -> {self.step} px")



class GridOverlay:
    def __init__(self, master):
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)

        self.screen_w = self.win.winfo_screenwidth()
        self.screen_h = self.win.winfo_screenheight()

        # Celda: pantalla completa dividida en COLS x ROWS
        self.cell_w = self.screen_w / COLS
        self.cell_h = self.screen_h / ROWS

        # La ventana ocupa TODA la pantalla para que los clics funcionen igual
        # pero solo dibujamos en la zona superior izquierda
        self.win.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.win.configure(bg=TRANSPARENT_KEY)
        try:
            self.win.attributes("-transparentcolor", TRANSPARENT_KEY)
        except tk.TclError:
            self.win.attributes("-alpha", 0.25)

        self.canvas = tk.Canvas(
            self.win, width=self.screen_w, height=self.screen_h,
            bg=TRANSPARENT_KEY, highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.visible = False
        self._draw()
        self.win.after(300, self._apply_click_through)

    def _draw(self):
        self.canvas.delete("all")

        # Cuadricula completa: todas las columnas y filas
        for i in range(COLS + 1):
            x = i * self.cell_w
            self.canvas.create_line(
                x, 0, x, self.screen_h,
                fill=GRID_LINE_COLOR, width=1,
            )
        for j in range(ROWS + 1):
            y = j * self.cell_h
            self.canvas.create_line(
                0, y, self.screen_w, y,
                fill=GRID_LINE_COLOR, width=1,
            )

        # Tamaño de fuente adaptativo segun tamaño de celda
        fsize = max(7, int(min(self.cell_w, self.cell_h) / 4.5))

        for i in range(COLS):
            for j in range(ROWS):
                cx = (i + 0.5) * self.cell_w
                cy = (j + 0.5) * self.cell_h
                label = f"{LETTERS[i]}{j + 1}"
                # Contorno negro (halo en 8 direcciones)
                for dx, dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)):
                    self.canvas.create_text(
                        cx + dx, cy + dy, text=label,
                        fill=GRID_TEXT_OUTLINE,
                        font=("Arial", fsize, "bold"),
                    )
                # Letra blanca encima
                self.canvas.create_text(
                    cx, cy, text=label,
                    fill=GRID_TEXT_COLOR,
                    font=("Arial", fsize, "bold"),
                )

    def _apply_click_through(self):
        try:
            hwnd = _get_real_hwnd(self.win)
            GWL_EXSTYLE       = -20
            WS_EX_LAYERED     = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE  = 0x08000000
            WS_EX_TOOLWINDOW  = 0x00000080
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            styles |= (WS_EX_LAYERED | WS_EX_TRANSPARENT
                       | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles)
            # Forzar encima de todo, incluida la barra de tareas
            force_topmost_over_taskbar(hwnd)
        except Exception as e:
            print(f"[aviso] click-through: {e}")

    def show(self):
        if not self.visible:
            self.win.deiconify()
            self._apply_click_through()
            self.visible = True

    def force_front(self):
        """Llamado periodicamente para mantenerse encima de la barra de tareas."""
        if self.visible:
            try:
                hwnd = _get_real_hwnd(self.win)
                force_topmost_over_taskbar(hwnd)
            except Exception:
                pass

    def hide(self):
        if self.visible:
            self.win.withdraw()
            self.visible = False

    def toggle(self):
        self.hide() if self.visible else self.show()

    def click_cell(self, col, row, mode="left"):
        x = int((col + 0.5) * self.cell_w)
        y = int((row + 0.5) * self.cell_h)
        self.win.update_idletasks()
        time.sleep(0.04)
        if mode == "double":
            pyautogui.doubleClick(x, y)
        elif mode == "right":
            pyautogui.rightClick(x, y)
        else:
            pyautogui.click(x, y)
        print(f"[clic {mode}] {LETTERS[col]}{row + 1} -> ({x}, {y})")


# =====================================================================
#  HUD DE DICTADO - indicador flotante (NO roba el foco)
# =====================================================================
class DictationHUD:
    """
    Pequeno indicador flotante que muestra lo que se esta dictando.
    Es solo visual: click-through activado, nunca roba el foco.
    El texto se escribe DIRECTAMENTE en la app activa con pyautogui.
    """

    def __init__(self, master):
        self.master = master
        self.win = None
        self.text_var = None
        self.status_var = None
        self.visible = False
        self._blink_state = True

    def _build(self):
        if self.win is not None:
            return
        self.win = tk.Toplevel(self.master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        # Sin foco: nunca interrumpe la app activa
        self.win.attributes("-alpha", 0.88)
        self.win.configure(bg="#0d0d1a")

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        w, h = 520, 72
        x = (sw - w) // 2
        y = sh - h - 60
        self.win.geometry(f"{w}x{h}+{x}+{y}")

        # Fila superior: estado
        top = tk.Frame(self.win, bg="#0d0d1a")
        top.pack(fill="x", padx=8, pady=(5, 0))

        self.status_var = tk.StringVar(value="● DICTANDO")
        tk.Label(top, textvariable=self.status_var,
                 bg="#0d0d1a", fg="#e74c3c",
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        tk.Label(top,
                 text="  'borrar palabra'  ·  'borrar todo'  ·  'quitar texto'",
                 bg="#0d0d1a", fg="#666688",
                 font=("Segoe UI", 7)).pack(side="left")

        # Fila inferior: texto dictado
        self.text_var = tk.StringVar(value="")
        tk.Label(self.win, textvariable=self.text_var,
                 bg="#0d0d1a", fg="#e8e8ff",
                 font=("Segoe UI", 12, "bold"),
                 anchor="w", padx=8).pack(fill="x", pady=(2, 4))

        # Arrastrable
        self.win.bind("<Button-1>", self._start_drag)
        self.win.bind("<B1-Motion>", self._drag)

        # Click-through para que no bloquee clics debajo
        self.win.after(200, self._apply_click_through)

    def _apply_click_through(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
            GWL_EXSTYLE      = -20
            WS_EX_LAYERED    = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE  = 0x08000000
            WS_EX_TOOLWINDOW  = 0x00000080
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            styles |= (WS_EX_LAYERED | WS_EX_TRANSPARENT
                       | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles)
        except Exception as e:
            print(f"[aviso] hud click-through: {e}")

    def _start_drag(self, e):
        self._dx = e.x_root - self.win.winfo_x()
        self._dy = e.y_root - self.win.winfo_y()

    def _drag(self, e):
        self.win.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def show(self):
        self._build()
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        self.visible = True
        self.text_var.set("")
        self._blink()

    def hide(self):
        self.visible = False
        if self.win:
            self.win.withdraw()

    def update_text(self, text):
        if self.text_var:
            # Truncar si es muy largo para que quepa en el HUD
            display = text if len(text) <= 55 else "..." + text[-52:]
            self.text_var.set(display)

    def _blink(self):
        if not self.visible or self.win is None:
            return
        try:
            self._blink_state = not self._blink_state
            dot = "● DICTANDO" if self._blink_state else "○ DICTANDO"
            self.status_var.set(dot)
        except Exception:
            pass
        self.win.after(700, self._blink)

    def reassert_topmost(self):
        if self.win and self.visible:
            try:
                self.win.attributes("-topmost", True)
            except Exception:
                pass


# =====================================================================
#  MOTOR DE DICTADO DIRECTO
# =====================================================================
class DirectDictation:
    """
    Gestiona el dictado directo: escucha voz y teclea inmediatamente
    en la aplicacion activa (campo de busqueda, formulario, documento...).

    Lleva un historial de palabras escritas en esta sesion para poder
    borrar con Backspace de forma precisa.
    """

    def __init__(self, hud: DictationHUD):
        self.hud = hud
        self._words: list[str] = []   # palabras escritas en esta sesion
        self._active = False

    # ---- estado ----
    @property
    def active(self):
        return self._active

    def start(self):
        self._active = True
        self._words = []
        self.hud.show()
        print("[dictado] Modo texto ON — habla para escribir")

    def stop(self):
        self._active = False
        self.hud.hide()
        print("[dictado] Modo texto OFF")

    # ---- acciones ----
    def type_phrase(self, phrase: str):
        """
        Teclea 'phrase' directamente en la app activa y la añade al historial.
        Se añade un espacio antes si ya habia texto previo.
        """
        if not phrase:
            return

        # Decidir si hay que añadir espacio separador
        prefix = " " if self._words else ""
        to_type = prefix + phrase

        # Escribir en la app activa usando pyautogui
        # typewrite no admite acentos/ñ bien; usamos pyperclip+paste si disponible,
        # si no, hotkey ctrl+shift+u en Linux o simplemente write() en Windows.
        self._type_unicode(to_type)

        # Guardar en historial (lista de palabras para poder borrar)
        self._words.extend(phrase.split())

        # Actualizar HUD
        self.hud.update_text(" ".join(self._words))
        print(f"[dictado] escrito: {to_type!r}")

    def delete_last_word(self):
        """Borra la ultima palabra escrita con Backspace."""
        if not self._words:
            return
        last = self._words[-1]
        # Calcular cuantos caracteres borrar:
        # la palabra + el espacio que la precede (si no es la primera)
        chars_to_delete = len(last) + (1 if len(self._words) > 1 else 0)
        for _ in range(chars_to_delete):
            pyautogui.press("backspace")
            time.sleep(0.02)
        self._words.pop()
        self.hud.update_text(" ".join(self._words))
        print(f"[dictado] borrada palabra '{last}'")

    def delete_all(self):
        """Borra todo lo dictado en esta sesion con Backspace."""
        if not self._words:
            return
        # Total de caracteres: suma de longitudes + espacios entre palabras
        total_chars = sum(len(w) for w in self._words) + max(0, len(self._words) - 1)
        for _ in range(total_chars):
            pyautogui.press("backspace")
            time.sleep(0.015)
        self._words = []
        self.hud.update_text("")
        print("[dictado] borrado todo")

    # ---- escritura unicode ----
    @staticmethod
    def _type_unicode(text: str):
        """
        Escribe texto con caracteres especiales (acentos, ñ...) en Windows.
        Usa el portapapeles para garantizar compatibilidad.
        """
        try:
            import pyperclip
            # Guardar portapapeles actual
            try:
                old_clip = pyperclip.paste()
            except Exception:
                old_clip = ""
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.08)
            # Restaurar portapapeles original
            try:
                pyperclip.copy(old_clip)
            except Exception:
                pass
        except ImportError:
            # Sin pyperclip: fallback a pyautogui.write (pierde acentos)
            safe = text.encode("ascii", "ignore").decode()
            pyautogui.write(safe, interval=0.03)


# =====================================================================
#  BARRA DE ACCIONES FLOTANTE
# =====================================================================
class ActionBar:
    def __init__(self, master, controller):
        self.ctrl = controller
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#222222")

        sw = self.win.winfo_screenwidth()
        self.w = 400
        self.h = 44
        x = sw - self.w - 20
        y = 20
        self.win.geometry(f"{self.w}x{self.h}+{x}+{y}")

        btn_style = dict(
            bg="#333333", fg="#FFFFFF", activebackground="#555555",
            activeforeground="#FFFFFF", bd=0, padx=8, pady=4,
            font=("Segoe UI", 9, "bold"),
        )
        buttons = [
            ("Rejilla",  self.ctrl.toggle_grid),
            ("Texto",    self.ctrl.start_dictation),
            ("Copiar",   lambda: INTENT_ACTIONS["COPY"]()),
            ("Pegar",    lambda: INTENT_ACTIONS["PASTE"]()),
            ("Cortar",   lambda: INTENT_ACTIONS["CUT"]()),
            ("Borrar",   lambda: INTENT_ACTIONS["DELETE"]()),
            ("Teclado",  self.ctrl.toggle_keyboard),
            ("X",        self.ctrl.quit),
        ]
        for text, cmd in buttons:
            b = tk.Button(self.win, text=text, command=cmd, **btn_style)
            b.pack(side="left", fill="y", padx=1, pady=2)

        self.win.bind("<Button-1>", self._start_drag)
        self.win.bind("<B1-Motion>", self._drag)

    def _start_drag(self, e):
        self._dx = e.x_root - self.win.winfo_x()
        self._dy = e.y_root - self.win.winfo_y()

    def _drag(self, e):
        self.win.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def reassert_topmost(self):
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass


# =====================================================================
#  CONTROLADOR PRINCIPAL
# =====================================================================
class SuperCapa:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.grid = GridOverlay(self.root)
        self.bar = ActionBar(self.root, self)
        self.moto = MotoCursor(self.root)
        self.hud = DictationHUD(self.root)
        self.dictation = DirectDictation(self.hud)
        self.mouse_ctrl = VoiceMouseController()

        self.keyboard_open = False
        self.command_queue = queue.Queue()
        self.listening = True

        # Hilo de voz
        self.voice_thread = threading.Thread(target=self._voice_loop, daemon=True)
        self.voice_thread.start()

        # Atajos globales
        try:
            keyboard.add_hotkey("f8",  lambda: self.command_queue.put("__TOGGLE_GRID__"))
            keyboard.add_hotkey("f9",  lambda: self.command_queue.put("__QUIT__"))
            keyboard.add_hotkey("f10", lambda: self.command_queue.put("__TOGGLE_KBD__"))
            keyboard.add_hotkey("f7",  lambda: self.command_queue.put("__TOGGLE_MOTO__"))
        except Exception as e:
            print(f"[aviso] atajos globales: {e}")

        self.root.after(100, self._process_commands)
        self.root.after(TOPMOST_REFRESH_MS, self._refresh_topmost)

        # Arranca con rejilla y moto visibles
        self.grid.show()
        self.moto.show()

    # ----- acciones -----
    def toggle_grid(self):
        self.grid.toggle()

    def toggle_keyboard(self):
        if self.keyboard_open:
            act_close_keyboard(); self.keyboard_open = False
        else:
            act_open_keyboard(); self.keyboard_open = True

    def start_dictation(self):
        self.dictation.start()

    def stop_dictation(self):
        self.dictation.stop()

    def quit(self):
        print("Cerrando SuperCapa...")
        self.listening = False
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            act_close_keyboard()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    # ----- loops -----
    def _refresh_topmost(self):
        # Forzar la rejilla encima de la barra de tareas en cada ciclo
        self.grid.force_front()
        try:
            self.bar.reassert_topmost()
            if self.dictation.active:
                self.hud.reassert_topmost()
        except Exception:
            pass
        self.root.after(TOPMOST_REFRESH_MS, self._refresh_topmost)

    def _process_commands(self):
        try:
            while True:
                cmd = self.command_queue.get_nowait()
                if cmd == "__QUIT__":
                    self.quit(); return
                if cmd == "__TOGGLE_GRID__":
                    self.toggle_grid(); continue
                if cmd == "__TOGGLE_KBD__":
                    self.toggle_keyboard(); continue
                if cmd == "__TOGGLE_MOTO__":
                    if self.moto._tracking:
                        self.moto.hide()
                    else:
                        self.moto.show()
                    continue
                self._handle_voice(cmd)
        except queue.Empty:
            pass
        self.root.after(100, self._process_commands)

    # ----- voz -----
    def _voice_loop(self):
        r = sr.Recognizer()
        r.pause_threshold = 0.6
        try:
            mic = sr.Microphone()
        except Exception as e:
            print(f"[ERROR] microfono: {e}"); return
        with mic as src:
            print("Calibrando microfono...")
            r.adjust_for_ambient_noise(src, duration=1.0)
            print("Escuchando. Di 'TEXTO' para dictar, 'QUITAR TEXTO' para cerrar.")

        while self.listening:
            try:
                with mic as src:
                    audio = r.listen(src, timeout=3, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"[aviso] escuchando: {e}")
                time.sleep(0.3)
                continue
            try:
                text = r.recognize_google(audio, language=LANGUAGE).lower().strip()
                print(f"[oido] {text!r}")
                self.command_queue.put(text)
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"[aviso] motor de voz: {e}")
                time.sleep(1.0)

    def _handle_voice(self, text):
        # --- Modo dictado activo: primero revisar comandos de control ---
        if self.dictation.active:
            intent = classify_intent(text)
            if intent == "STOP_DICTATION":
                self.stop_dictation(); return
            if intent == "DELETE_WORD":
                self.dictation.delete_last_word(); return
            if intent == "CLEAR_TEXT":
                self.dictation.delete_all(); return
            if intent == "QUIT":
                self.quit(); return
            # No es un comando -> teclear directamente en la app activa
            self.dictation.type_phrase(text)
            return

        # --- Modo normal ---
        coord = parse_coordinate(text)
        if coord:
            mode = "left"
            if any(w in text for w in INTENTS["DOUBLE_CLICK"]):
                mode = "double"
            elif any(w in text for w in INTENTS["RIGHT_CLICK"]):
                mode = "right"
            self.grid.click_cell(coord[0], coord[1], mode=mode)
            return

        intent = classify_intent(text)
        if intent is None:
            return
        print(f"[intent] {intent}")

        if intent == "QUIT":           self.quit(); return
        if intent == "SHOW_GRID":      self.grid.show(); return
        if intent == "HIDE_GRID":      self.grid.hide(); return
        if intent == "START_DICTATION": self.start_dictation(); return
        if intent == "STOP_DICTATION":  self.stop_dictation(); return

        # Control direccional del raton
        if intent == "MOUSE_UP":
            self.mouse_ctrl.up(parse_step_count(text)); return
        if intent == "MOUSE_DOWN":
            self.mouse_ctrl.down(parse_step_count(text)); return
        if intent == "MOUSE_LEFT":
            self.mouse_ctrl.left(parse_step_count(text)); return
        if intent == "MOUSE_RIGHT":
            self.mouse_ctrl.right(parse_step_count(text)); return
        if intent == "MOUSE_FASTER":
            self.mouse_ctrl.faster(); return
        if intent == "MOUSE_SLOWER":
            self.mouse_ctrl.slower(); return

        if intent == "OPEN_KEYBOARD":
            if not self.keyboard_open:
                act_open_keyboard(); self.keyboard_open = True
            return
        if intent == "CLOSE_KEYBOARD":
            if self.keyboard_open:
                act_close_keyboard(); self.keyboard_open = False
            return

        action = INTENT_ACTIONS.get(intent)
        if action:
            try:
                action()
            except Exception as e:
                print(f"[aviso] accion {intent} fallo: {e}")

    def run(self):
        self.root.mainloop()


# =====================================================================
#  ENTRY POINT
# =====================================================================
def main():
    print("=" * 62)
    print("  SUPERCAPA v3 - control por voz + puntero moto 🏍️")
    print("=" * 62)
    print("Voz - Comandos generales:")
    print("  'rejilla' / 'ocultar rejilla'     mostrar/ocultar cuadricula")
    print("  'A uno', 'be 7', 't 20'           clic en celda")
    print("  'doble a 3', 'clic derecho b5'    doble clic / menu")
    print("  'copiar', 'pegar', 'cortar'       edicion")
    print("  'cierra esto', 'ponlo en grande'  ventanas")
    print("  'teclado' / 'cerrar teclado'      teclado en pantalla")
    print("  'salir del programa'              cerrar SuperCapa")
    print()
    print("Voz - MODO TEXTO:")
    print("  'texto'          -> activa dictado (escribe en la app activa)")
    print("  <hablar>         -> teclea lo que digas directamente")
    print("  'borrar palabra' -> borra la ultima palabra (Backspace)")
    print("  'borrar todo'    -> borra todo lo dictado")
    print("  'quitar texto'   -> desactiva el modo texto")
    print()
    print("Voz - CONTROL DIRECCIONAL DEL RATON (para barra de tareas etc.):")
    print("  'arriba [N]'     -> sube N pasos  (ej: 'arriba tres')")
    print("  'abajo [N]'      -> baja N pasos")
    print("  'izquierda [N]'  -> mueve izquierda N pasos")
    print("  'derecha [N]'    -> mueve derecha N pasos")
    print("  'mas rapido'     -> aumenta el paso de movimiento")
    print("  'mas despacio'   -> reduce el paso de movimiento")
    print("  'clic'           -> clic izquierdo en posicion actual")
    print("  'doble clic'     -> doble clic en posicion actual")
    print("  'clic derecho'   -> menu contextual en posicion actual")
    print()
    print("Teclas:  F7=moto   F8=rejilla   F9=salir   F10=teclado")
    print("=" * 62)
    SuperCapa().run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
