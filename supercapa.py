# -*- coding: utf-8 -*-
"""
SuperCapa v4 - Control por voz con cuadricula superpuesta.

NOVEDADES V4:
  Mejoras de prototipo estable:
    * Indicador visual "te estoy escuchando" (punto de color en pantalla)
    * Pausar/reanudar la voz: "dormir" / "despierta"
    * Confirmacion visual del ultimo comando reconocido
    * Detecta caida de internet con aviso en pantalla
    * Configuracion persistente (config.json al lado del .exe)
    * Comprobacion de microfono al arrancar (aviso claro si falla)
    * Comando de emergencia: "socorro" cierra todo

  Peticiones de la companera:
    * Marcar/seleccionar celda sin clicar: "marcar A1"
    * Cooldown de 250ms entre clics para evitar dobles accidentales
    * Barra flotante: arranca minimizada abajo-centro, "ocultar barra"
    * Arrastrar archivos: "coger A1" -> "soltar T15", "cancelar arrastre"
"""

import ctypes
import json
import os
import queue
import re
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk

# DPI awareness - antes de crear ventanas
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

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    from ctypes import POINTER, cast
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02

# ============================================================
#  CONFIGURACION POR DEFECTO (se sobrescribe con config.json)
# ============================================================
COLS = 20
ROWS = 20
LETTERS = "ABCDEFGHIJKLMNOPQRST"
GRID_LINE_COLOR = "#888888"
GRID_TEXT_COLOR = "#FFFFFF"
GRID_TEXT_OUTLINE = "#000000"
HIGHLIGHT_COLOR = "#00FF66"   # verde para celdas marcadas
TRANSPARENT_KEY = "#FF00FF"
LANGUAGE = "es-ES"
TOPMOST_REFRESH_MS = 150

MOUSE_STEP_DEFAULT = 60
MOUSE_STEP_MIN = 10
MOUSE_STEP_MAX = 300
MOUSE_STEP_FACTOR = 1.6

CLICK_COOLDOWN_MS = 250  # tiempo minimo entre clics en la misma celda
HUD_TIMEOUT_MS = 2500    # cuanto dura el cartel de "ultimo comando"


# ============================================================
#  CONFIG PERSISTENTE
# ============================================================
def get_config_path():
    """config.json al lado del .exe / del .py."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")


def load_config():
    defaults = {
        "mouse_step": MOUSE_STEP_DEFAULT,
        "bar_visible": True,
        "bar_minimized": True,
        "bar_x": None,        # None = centrar abajo
        "bar_y": None,
        "grid_visible_on_start": True,
    }
    try:
        with open(get_config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        defaults.update(data)
    except Exception:
        pass
    return defaults


def save_config(cfg):
    try:
        with open(get_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[aviso] no se pudo guardar config: {e}")


# ============================================================
#  DICCIONARIO DE INTENCIONES (NLP por palabras clave)
# ============================================================
INTENTS = {
    # --- emergencia ---
    "EMERGENCY": [
        "socorro", "emergencia", "para todo", "para todo el programa",
        "apaga ya", "ayuda urgente",
    ],
    # --- ciclo de vida ---
    "QUIT": [
        "salir del programa", "cerrar programa", "cerrar supercapa",
        "apagar programa", "apagar supercapa", "adios supercapa",
    ],
    "SLEEP": [
        "dormir", "duermete", "duérmete", "ponte a dormir",
        "deja de escuchar", "para de escuchar", "callate", "cállate",
        "modo dormir",
    ],
    "WAKE": [
        "despierta", "despiertate", "despiértate", "vuelve a escuchar",
        "vuelve a la escucha", "modo despierto", "ya estoy",
    ],
    # --- rejilla ---
    "HIDE_GRID": [
        "ocultar rejilla", "esconder rejilla", "quitar rejilla",
        "quita la rejilla", "quita la cuadricula", "quita la cuadrícula",
        "oculta la rejilla", "ocultar cuadricula", "ocultar cuadrícula",
    ],
    "SHOW_GRID": [
        "mostrar rejilla", "muestra la rejilla", "activar rejilla",
        "activa la rejilla", "rejilla", "cuadricula", "cuadrícula",
        "mostrar capa", "activar capa", "muestra la capa",
    ],
    "CLEAR_HIGHLIGHT": [
        "desmarcar", "desmarca", "quita la marca", "limpia la marca",
        "quitar marca", "limpiar seleccion", "limpiar selección",
    ],
    # --- barra ---
    "HIDE_BAR": [
        "ocultar barra", "oculta la barra", "quita la barra",
        "esconder barra", "esconde la barra",
    ],
    "SHOW_BAR": [
        "mostrar barra", "muestra la barra", "ensena la barra",
        "enseña la barra", "saca la barra", "abrir barra",
    ],
    # --- arrastre ---
    "CANCEL_DRAG": [
        "cancelar arrastre", "cancela el arrastre", "cancelar arrastrar",
        "soltar aqui", "soltar aquí", "olvidalo",
    ],
    # --- teclado ---
    "CLOSE_KEYBOARD": [
        "cerrar teclado", "quitar teclado", "ocultar teclado",
        "quita el teclado", "cierra el teclado",
    ],
    "OPEN_KEYBOARD": [
        "abrir teclado", "teclado en pantalla", "mostrar teclado",
        "muestra el teclado", "activar teclado", "saca el teclado",
        "pon el teclado", "teclado",
    ],
    # --- ventanas ---
    "CLOSE_WINDOW": [
        "cerrar ventana", "cierra ventana", "cierra la ventana",
        "cierra esa ventana", "cierra esta ventana", "cierra esto",
        "cierralo", "ciérralo", "cerrar esto", "quita esto", "quitalo",
        "quítalo",
    ],
    "MAXIMIZE": [
        "maximizar", "maximiza", "maximízalo", "maximizalo",
        "ponlo en grande", "ponlo grande", "pantalla completa",
        "hazlo grande", "agrandalo", "agrándalo",
    ],
    "MINIMIZE": [
        "minimizar", "minimiza", "minimizalo", "minimízalo",
        "ponlo pequeño", "ponlo pequeno", "hazlo pequeño",
        "esconde la ventana", "ocultar ventana", "esconder ventana",
    ],
    "SWITCH_WINDOW": [
        "cambiar ventana", "cambiar de ventana", "siguiente ventana",
        "otra ventana", "cambia de ventana", "pasa a la siguiente ventana",
    ],
    # --- sistema ---
    "OPEN_EXPLORER": [
        "abrir explorador", "abre el explorador", "abre explorador",
        "explorador de archivos", "abrir archivos", "abre los archivos",
        "abre una carpeta", "abrir una carpeta", "mis archivos",
        "mis documentos",
    ],
    "SHOW_DESKTOP": [
        "mostrar escritorio", "muestra el escritorio", "ver escritorio",
        "ir al escritorio", "escritorio", "enseñame el escritorio",
    ],
    "PROJECT": [
        "duplicar pantalla", "extender pantalla", "proyectar pantalla",
        "segunda pantalla", "proyección", "proyeccion",
    ],
    # --- edicion ---
    "SELECT_ALL": [
        "seleccionar todo", "selecciona todo", "selecciónalo todo",
        "seleccionalo todo",
    ],
    "ENTER": [
        "intro", "enter", "buscar", "aceptar", "confirma", "confirmar",
    ],
    "COPY": [
        "copiar", "copia eso", "copia esto", "copialo", "cópialo", "copia",
    ],
    "PASTE": [
        "pegar", "pega eso", "pega esto", "pegalo", "pégalo", "pega",
    ],
    "CUT": [
        "cortar", "corta eso", "corta esto", "cortalo", "córtalo", "corta",
    ],
    "DELETE": [
        "eliminar", "borrar", "suprimir", "elimina eso", "borra eso",
        "elimínalo", "eliminalo", "bórralo", "borralo", "borra", "elimina",
    ],
    # --- raton: tipos de clic (cuando no hay coordenada) ---
    "DOUBLE_CLICK": [
        "doble clic", "doble click", "doble pica", "doble pulsacion",
        "doble pulsación",
    ],
    "RIGHT_CLICK": [
        "clic derecho", "click derecho", "boton derecho", "botón derecho",
        "menu contextual", "menú contextual",
    ],
    "LEFT_CLICK": [
        "clic izquierdo", "click izquierdo", "clic", "click", "pica",
        "pulsa", "pincha", "toca",
    ],
    # --- raton direccional ---
    "MOVE_UP": ["arriba", "sube", "subir"],
    "MOVE_DOWN": ["abajo", "baja", "bajar"],
    "MOVE_LEFT": ["izquierda", "a la izquierda"],
    "MOVE_RIGHT": ["derecha", "a la derecha"],
    "FASTER": ["mas rapido", "más rápido", "mas rápido", "más rapido", "acelerar"],
    "SLOWER": ["mas despacio", "más despacio", "ralentiza", "frena"],
    # --- volumen ---
    "VOL_UP": ["sube el volumen", "subir volumen", "mas volumen", "más volumen"],
    "VOL_DOWN": ["baja el volumen", "bajar volumen", "menos volumen"],
    "VOL_MUTE": ["silencio", "silenciar", "silencia", "mutear", "mute"],
    "VOL_MAX": ["volumen maximo", "volumen máximo", "máximo volumen"],
    # --- dictado ---
    "DICTATE_START": [
        "texto", "modo texto", "empezar dictado", "empieza a dictar",
        "dictar", "dictame", "díctame",
    ],
    "DICTATE_END": [
        "quitar texto", "salir del texto", "fin del texto", "fin texto",
        "terminar dictado", "termina el dictado", "fin dictado",
    ],
    "DICTATE_DEL_WORD": [
        "borrar palabra", "borra la palabra", "borra palabra",
    ],
    "DICTATE_CLEAR": [
        "borrar todo", "borra todo", "limpia todo", "limpiar todo",
    ],
}

INTENT_PRIORITY = [
    "EMERGENCY",
    "QUIT", "SLEEP", "WAKE",
    "DICTATE_END", "DICTATE_DEL_WORD", "DICTATE_CLEAR", "DICTATE_START",
    "CANCEL_DRAG",
    "CLEAR_HIGHLIGHT",
    "HIDE_GRID", "SHOW_GRID",
    "HIDE_BAR", "SHOW_BAR",
    "CLOSE_KEYBOARD", "OPEN_KEYBOARD",
    "CLOSE_WINDOW", "MAXIMIZE", "MINIMIZE", "SWITCH_WINDOW",
    "OPEN_EXPLORER", "SHOW_DESKTOP", "PROJECT",
    "SELECT_ALL", "ENTER",
    "COPY", "PASTE", "CUT", "DELETE",
    "VOL_MUTE", "VOL_MAX", "VOL_UP", "VOL_DOWN",
    "FASTER", "SLOWER",
    "MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT",
    "DOUBLE_CLICK", "RIGHT_CLICK", "LEFT_CLICK",
]


def classify_intent(text):
    t = " " + text.lower().strip() + " "
    t = re.sub(r"\s+", " ", t)
    for intent in INTENT_PRIORITY:
        for trigger in INTENTS[intent]:
            if trigger in t:
                return intent
    return None


# ============================================================
#  PARSEO DE COORDENADAS Y NUMEROS
# ============================================================
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
    "p": "P", "pe": "P", "papa": "P",
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


def extract_number(text, default=1):
    """Saca un numero del texto, en cifra o palabra."""
    m = re.search(r"\b(\d{1,3})\b", text)
    if m:
        return int(m.group(1))
    for w, n in NUMBERS_ES.items():
        if re.search(r"\b" + re.escape(w) + r"\b", text):
            return n
    return default


# ============================================================
#  ACCIONES BASICAS
# ============================================================
def act_left_click():   pyautogui.click()
def act_double_click(): pyautogui.doubleClick()
def act_right_click():  pyautogui.rightClick()

def act_copy():       pyautogui.hotkey("ctrl", "c")
def act_paste():      pyautogui.hotkey("ctrl", "v")
def act_cut():        pyautogui.hotkey("ctrl", "x")
def act_delete():     pyautogui.press("delete")
def act_select_all(): pyautogui.hotkey("ctrl", "a")
def act_enter():      pyautogui.press("enter")

def act_close_window():  pyautogui.hotkey("alt", "f4")
def act_minimize():      pyautogui.hotkey("win", "down")
def act_maximize():      pyautogui.hotkey("win", "up")
def act_switch_window(): pyautogui.hotkey("alt", "tab")

def act_open_explorer(): pyautogui.hotkey("win", "e")
def act_show_desktop():  pyautogui.hotkey("win", "d")
def act_project():       pyautogui.hotkey("win", "p")


def act_open_keyboard():
    paths = [
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                     "Sysnative", "osk.exe"),
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                     "System32", "osk.exe"),
        "osk.exe",
    ]
    for p in paths:
        try:
            subprocess.Popen([p])
            return
        except Exception:
            continue


def act_close_keyboard():
    try:
        subprocess.run(["taskkill", "/IM", "osk.exe", "/F"],
                       capture_output=True, timeout=3)
    except Exception:
        pass


# ============================================================
#  VOLUMEN
# ============================================================
class VolumeController:
    def __init__(self):
        self.iface = None
        if HAS_PYCAW:
            try:
                devs = AudioUtilities.GetSpeakers()
                interface = devs.Activate(IAudioEndpointVolume._iid_,
                                          CLSCTX_ALL, None)
                self.iface = cast(interface, POINTER(IAudioEndpointVolume))
            except Exception:
                self.iface = None

    def up(self):
        if self.iface:
            cur = self.iface.GetMasterVolumeLevelScalar()
            self.iface.SetMasterVolumeLevelScalar(min(1.0, cur + 0.1), None)
        else:
            for _ in range(5):
                pyautogui.press("volumeup")

    def down(self):
        if self.iface:
            cur = self.iface.GetMasterVolumeLevelScalar()
            self.iface.SetMasterVolumeLevelScalar(max(0.0, cur - 0.1), None)
        else:
            for _ in range(5):
                pyautogui.press("volumedown")

    def mute(self):
        if self.iface:
            self.iface.SetMute(1, None)
        else:
            pyautogui.press("volumemute")

    def maximum(self):
        if self.iface:
            self.iface.SetMute(0, None)
            self.iface.SetMasterVolumeLevelScalar(1.0, None)


# ============================================================
#  INTERNET CHECK
# ============================================================
def has_internet(timeout=2):
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False


# ============================================================
#  OVERLAY PRINCIPAL (rejilla + HUDs)
# ============================================================
class GridOverlay:
    def __init__(self, master):
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)

        self.screen_w = self.win.winfo_screenwidth()
        self.screen_h = self.win.winfo_screenheight()
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

        self.cell_w = self.screen_w / COLS
        self.cell_h = self.screen_h / ROWS
        self.visible = False
        self.highlighted = None       # (col, row) o None
        self.highlight_id = None
        self.last_click_time = 0.0
        self.last_click_cell = None

        self._draw()
        self.win.after(300, self._apply_click_through)

    # ---- dibujo ----
    def _draw(self):
        self.canvas.delete("all")
        for i in range(COLS + 1):
            x = i * self.cell_w
            self.canvas.create_line(x, 0, x, self.screen_h,
                                    fill=GRID_LINE_COLOR, width=1)
        for j in range(ROWS + 1):
            y = j * self.cell_h
            self.canvas.create_line(0, y, self.screen_w, y,
                                    fill=GRID_LINE_COLOR, width=1)
        fsize = max(9, int(min(self.cell_w, self.cell_h) / 4.5))
        for i in range(COLS):
            for j in range(ROWS):
                cx = (i + 0.5) * self.cell_w
                cy = (j + 0.5) * self.cell_h
                label = f"{LETTERS[i]}{j + 1}"
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    self.canvas.create_text(
                        cx + dx, cy + dy, text=label,
                        fill=GRID_TEXT_OUTLINE,
                        font=("Arial", fsize, "bold"),
                    )
                self.canvas.create_text(
                    cx, cy, text=label,
                    fill=GRID_TEXT_COLOR,
                    font=("Arial", fsize, "bold"),
                )

    def _apply_click_through(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.win.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            styles |= (WS_EX_LAYERED | WS_EX_TRANSPARENT
                       | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, styles)
        except Exception:
            pass

    # ---- visibilidad ----
    def show(self):
        if not self.visible:
            self.win.deiconify()
            self.win.attributes("-topmost", True)
            self._apply_click_through()
            self.visible = True

    def hide(self):
        if self.visible:
            self.win.withdraw()
            self.visible = False

    def toggle(self):
        self.hide() if self.visible else self.show()

    # ---- marcar/seleccionar celda sin clicar ----
    def highlight_cell(self, col, row):
        self.clear_highlight()
        x1 = col * self.cell_w
        y1 = row * self.cell_h
        x2 = x1 + self.cell_w
        y2 = y1 + self.cell_h
        self.highlight_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=HIGHLIGHT_COLOR, width=4, fill=TRANSPARENT_KEY,
        )
        self.highlighted = (col, row)
        if not self.visible:
            self.show()

    def clear_highlight(self):
        if self.highlight_id is not None:
            self.canvas.delete(self.highlight_id)
            self.highlight_id = None
        self.highlighted = None

    # ---- clic en celda ----
    def _cell_center(self, col, row):
        return (int((col + 0.5) * self.cell_w),
                int((row + 0.5) * self.cell_h))

    def click_cell(self, col, row, mode="left"):
        # cooldown contra dobles accidentales
        now = time.time() * 1000
        if (self.last_click_cell == (col, row) and
                now - self.last_click_time < CLICK_COOLDOWN_MS):
            print(f"[clic] ignorado por cooldown ({col},{row})")
            return False
        self.last_click_time = now
        self.last_click_cell = (col, row)

        x, y = self._cell_center(col, row)
        self.win.update_idletasks()
        time.sleep(0.04)
        if mode == "double":
            pyautogui.doubleClick(x, y)
        elif mode == "right":
            pyautogui.rightClick(x, y)
        else:
            pyautogui.click(x, y)
        print(f"[clic {mode}] {LETTERS[col]}{row + 1} -> ({x}, {y})")
        return True

    # ---- arrastre ----
    def drag_start(self, col, row):
        x, y = self._cell_center(col, row)
        pyautogui.moveTo(x, y, duration=0.05)
        pyautogui.mouseDown()
        print(f"[arrastre] cogido en {LETTERS[col]}{row + 1} ({x},{y})")

    def drag_end(self, col, row):
        x, y = self._cell_center(col, row)
        pyautogui.moveTo(x, y, duration=0.15)
        pyautogui.mouseUp()
        print(f"[arrastre] soltado en {LETTERS[col]}{row + 1} ({x},{y})")

    def drag_cancel(self):
        try:
            pyautogui.mouseUp()
        except Exception:
            pass
        print("[arrastre] cancelado")


# ============================================================
#  HUD: indicador de escucha + ultimo comando + dictado
# ============================================================
class HudOverlay:
    """Pequeño HUD pegado a la esquina superior izquierda con:
       - punto de color (verde/amarillo/rojo/gris) = estado del micro
       - texto pequeno con el ultimo comando reconocido
       - barra de dictado cuando esta activo el modo texto
    """
    def __init__(self, master):
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.85)
        self.win.configure(bg="#101010")

        self.win.geometry("+12+12")

        frm = tk.Frame(self.win, bg="#101010")
        frm.pack(padx=8, pady=4)

        self.dot_canvas = tk.Canvas(frm, width=14, height=14,
                                    bg="#101010", highlightthickness=0)
        self.dot_canvas.pack(side="left", padx=(0, 6))
        self.dot = self.dot_canvas.create_oval(2, 2, 12, 12, fill="#888888",
                                               outline="")
        self.label = tk.Label(frm, text="iniciando...",
                              fg="#FFFFFF", bg="#101010",
                              font=("Segoe UI", 9))
        self.label.pack(side="left")

        self._last_cmd_until = 0
        self._reset_text = "escuchando"
        self._set_dot_color("#888888")

    def _set_dot_color(self, color):
        self.dot_canvas.itemconfig(self.dot, fill=color)

    def state_listening(self):
        self._set_dot_color("#00FF66")  # verde
        self._reset_text = "escuchando"
        if time.time() * 1000 > self._last_cmd_until:
            self.label.config(text=self._reset_text)

    def state_processing(self):
        self._set_dot_color("#FFCC00")  # amarillo

    def state_sleeping(self):
        self._set_dot_color("#888888")  # gris
        self._reset_text = "DORMIDO (di 'despierta')"
        self.label.config(text=self._reset_text)

    def state_no_internet(self):
        self._set_dot_color("#FF3333")  # rojo
        self._reset_text = "sin internet, reintentando..."
        self.label.config(text=self._reset_text)

    def state_no_mic(self):
        self._set_dot_color("#FF3333")
        self._reset_text = "sin microfono"
        self.label.config(text=self._reset_text)

    def show_command(self, cmd, ok=True):
        prefix = "✓ " if ok else "✗ "
        txt = f"{prefix}{cmd[:60]}"
        self.label.config(text=txt)
        self._last_cmd_until = time.time() * 1000 + HUD_TIMEOUT_MS

    def tick(self):
        """Restaura el texto si el ultimo comando ya caduco."""
        if time.time() * 1000 > self._last_cmd_until:
            self.label.config(text=self._reset_text)


# ============================================================
#  HUD DE DICTADO (centro inferior)
# ============================================================
class DictateHud:
    def __init__(self, master):
        self.win = tk.Toplevel(master)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.9)
        self.win.configure(bg="#101010")

        self.label = tk.Label(self.win, text="● DICTANDO",
                              fg="#FF4444", bg="#101010",
                              font=("Segoe UI", 11, "bold"),
                              padx=14, pady=6)
        self.label.pack()
        self.visible = False
        self._blink_state = True

    def show(self):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.update_idletasks()
        w = self.win.winfo_reqwidth()
        x = (sw - w) // 2
        y = sh - 90
        self.win.geometry(f"+{x}+{y}")
        self.win.deiconify()
        self.win.attributes("-topmost", True)
        self.visible = True

    def hide(self):
        self.win.withdraw()
        self.visible = False

    def blink(self):
        if not self.visible:
            return
        self._blink_state = not self._blink_state
        self.label.config(fg="#FF4444" if self._blink_state else "#660000")


# ============================================================
#  BARRA DE ACCIONES (ahora abajo-centro y minimizable)
# ============================================================
class ActionBar:
    """Barra flotante. Por defecto:
       - posicion: abajo, centrada
       - estado: minimizada (solo una pestañita pequeña)
       - se expande con clic en la pestañita o "muestra la barra"
    """
    def __init__(self, master, controller, cfg):
        self.ctrl = controller
        self.cfg = cfg
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", 0.92)
        self.win.configure(bg="#1a1a1a")

        self.expanded_w = 480
        self.expanded_h = 42
        self.collapsed_w = 60
        self.collapsed_h = 22

        # Frame contenedor con todos los botones (se ocultan al colapsar)
        self.full_frame = tk.Frame(self.win, bg="#1a1a1a")
        btn_style = dict(
            bg="#2a2a2a", fg="#FFFFFF", activebackground="#444444",
            activeforeground="#FFFFFF", bd=0, padx=6, pady=3,
            font=("Segoe UI", 9),
        )
        buttons = [
            ("Rejilla",  self.ctrl.toggle_grid),
            ("Texto",    self.ctrl.start_dictation),
            ("Copiar",   act_copy),
            ("Pegar",    act_paste),
            ("Cortar",   act_cut),
            ("Borrar",   act_delete),
            ("Teclado",  self.ctrl.toggle_keyboard),
            ("Dormir",   self.ctrl.toggle_sleep),
            ("▼",        self.collapse),
            ("X",        self.ctrl.quit),
        ]
        for text, cmd in buttons:
            tk.Button(self.full_frame, text=text, command=cmd,
                      **btn_style).pack(side="left", padx=1, pady=2)

        # Pestañita colapsada
        self.tab_frame = tk.Frame(self.win, bg="#1a1a1a")
        tk.Button(self.tab_frame, text="▲ menu",
                  command=self.expand,
                  bg="#2a2a2a", fg="#CCCCCC",
                  activebackground="#444444",
                  bd=0, padx=10, pady=2,
                  font=("Segoe UI", 8)).pack()

        self.minimized = bool(cfg.get("bar_minimized", True))
        self._apply_state()

        # Permitir arrastrar
        for w in (self.full_frame, self.tab_frame):
            w.bind("<Button-1>", self._start_drag)
            w.bind("<B1-Motion>", self._drag)

    def _bottom_center_geom(self, w, h):
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        # Saved? respetar si lo hay
        if self.cfg.get("bar_x") is not None:
            return f"{w}x{h}+{self.cfg['bar_x']}+{self.cfg['bar_y']}"
        x = (sw - w) // 2
        y = sh - h - 50
        return f"{w}x{h}+{x}+{y}"

    def _apply_state(self):
        if self.minimized:
            self.full_frame.pack_forget()
            self.tab_frame.pack(fill="both", expand=True)
            self.win.geometry(self._bottom_center_geom(
                self.collapsed_w, self.collapsed_h))
        else:
            self.tab_frame.pack_forget()
            self.full_frame.pack(fill="both", expand=True)
            self.win.geometry(self._bottom_center_geom(
                self.expanded_w, self.expanded_h))
        self.win.deiconify()
        self.win.attributes("-topmost", True)

    def expand(self):
        self.minimized = False
        self.cfg["bar_minimized"] = False
        save_config(self.cfg)
        self._apply_state()

    def collapse(self):
        self.minimized = True
        self.cfg["bar_minimized"] = True
        save_config(self.cfg)
        self._apply_state()

    def show(self):
        self.win.deiconify()
        self.win.attributes("-topmost", True)

    def hide(self):
        self.win.withdraw()

    def _start_drag(self, e):
        self._dx = e.x_root - self.win.winfo_x()
        self._dy = e.y_root - self.win.winfo_y()

    def _drag(self, e):
        nx = e.x_root - self._dx
        ny = e.y_root - self._dy
        self.win.geometry(f"+{nx}+{ny}")
        self.cfg["bar_x"] = nx
        self.cfg["bar_y"] = ny

    def reassert_topmost(self):
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass


# ============================================================
#  CONTROLADOR PRINCIPAL
# ============================================================
class SuperCapa:
    def __init__(self):
        self.cfg = load_config()
        self.root = tk.Tk()
        self.root.withdraw()

        self.grid = GridOverlay(self.root)
        self.hud = HudOverlay(self.root)
        self.dictate_hud = DictateHud(self.root)
        self.bar = ActionBar(self.root, self, self.cfg)

        self.volume = VolumeController()

        self.keyboard_open = False
        self.command_queue = queue.Queue()
        self.listening = True
        self.sleeping = False
        self.dictating = False
        self.has_net = True

        # estado de arrastre
        self.dragging = False

        # ratón direccional
        self.mouse_step = self.cfg.get("mouse_step", MOUSE_STEP_DEFAULT)

        # Comprobacion de microfono
        self.mic_ok = self._check_microphone()

        # Comprobacion inicial de internet
        self._update_internet_status()

        # Hilo de voz
        self.voice_thread = threading.Thread(
            target=self._voice_loop, daemon=True)
        self.voice_thread.start()

        # Atajos globales
        try:
            keyboard.add_hotkey("f8", lambda: self.command_queue.put("__TOGGLE_GRID__"))
            keyboard.add_hotkey("f9", lambda: self.command_queue.put("__QUIT__"))
            keyboard.add_hotkey("f10", lambda: self.command_queue.put("__TOGGLE_KBD__"))
            keyboard.add_hotkey("f11", lambda: self.command_queue.put("__TOGGLE_SLEEP__"))
        except Exception as e:
            print(f"[aviso] atajos: {e}")

        # Bucles periodicos
        self.root.after(100, self._process_commands)
        self.root.after(TOPMOST_REFRESH_MS, self._refresh_topmost)
        self.root.after(500, self._tick_hud)
        self.root.after(10000, self._check_internet_periodic)
        self.root.after(500, self._blink_dictate_hud)

        if self.cfg.get("grid_visible_on_start", True):
            self.grid.show()

    # ---- comprobaciones ----
    def _check_microphone(self):
        try:
            mic_list = sr.Microphone.list_microphone_names()
            if not mic_list:
                self.hud.state_no_mic()
                print("[ERROR] No hay micrófonos disponibles.")
                return False
            sr.Microphone()
            return True
        except Exception as e:
            print(f"[ERROR] microfono: {e}")
            self.hud.state_no_mic()
            return False

    def _update_internet_status(self):
        self.has_net = has_internet()
        if not self.has_net:
            self.hud.state_no_internet()

    def _check_internet_periodic(self):
        prev = self.has_net
        self.has_net = has_internet(timeout=2)
        if not self.has_net and prev:
            self.hud.state_no_internet()
        elif self.has_net and not prev and not self.sleeping:
            self.hud.state_listening()
        self.root.after(15000, self._check_internet_periodic)

    # ---- helpers UI ----
    def _tick_hud(self):
        self.hud.tick()
        self.root.after(500, self._tick_hud)

    def _blink_dictate_hud(self):
        self.dictate_hud.blink()
        self.root.after(500, self._blink_dictate_hud)

    def _refresh_topmost(self):
        try:
            self.grid.win.attributes("-topmost", True)
            self.hud.win.attributes("-topmost", True)
            self.bar.reassert_topmost()
            if self.dictate_hud.visible:
                self.dictate_hud.win.attributes("-topmost", True)
        except Exception:
            pass
        self.root.after(TOPMOST_REFRESH_MS, self._refresh_topmost)

    # ---- acciones de barra ----
    def toggle_grid(self):
        self.grid.toggle()

    def toggle_keyboard(self):
        if self.keyboard_open:
            act_close_keyboard()
            self.keyboard_open = False
        else:
            act_open_keyboard()
            self.keyboard_open = True

    def toggle_sleep(self):
        if self.sleeping:
            self.wake()
        else:
            self.sleep()

    def sleep(self):
        self.sleeping = True
        self.hud.state_sleeping()
        print("[modo] DORMIDO")

    def wake(self):
        self.sleeping = False
        self.hud.state_listening()
        print("[modo] DESPIERTO")

    def start_dictation(self):
        if not self.dictating:
            self.dictating = True
            self.dictate_hud.show()
            print("[dictado] activado")

    def stop_dictation(self):
        if self.dictating:
            self.dictating = False
            self.dictate_hud.hide()
            print("[dictado] desactivado")

    def emergency_stop(self):
        """Cierra dictado, suelta arrastre, oculta rejilla.
        No mata el programa, solo deja todo en estado seguro."""
        print("[EMERGENCIA] poniendo todo en estado seguro")
        self.stop_dictation()
        if self.dragging:
            self.grid.drag_cancel()
            self.dragging = False
        self.grid.clear_highlight()
        self.sleep()

    def quit(self):
        print("Cerrando SuperCapa...")
        self.cfg["mouse_step"] = self.mouse_step
        save_config(self.cfg)
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

    # ---- voz ----
    def _voice_loop(self):
        if not self.mic_ok:
            return
        r = sr.Recognizer()
        r.pause_threshold = 0.6
        r.dynamic_energy_threshold = True
        r.dynamic_energy_ratio = 1.8

        try:
            mic = sr.Microphone()
        except Exception as e:
            print(f"[ERROR] microfono: {e}")
            return

        with mic as src:
            print("Calibrando micrófono (3s, silencio por favor)...")
            r.adjust_for_ambient_noise(src, duration=3.0)

        self.hud.state_listening()
        print("Listo. Escuchando.")
        recalibrate_in = 60

        while self.listening:
            try:
                with mic as src:
                    audio = r.listen(src, timeout=3, phrase_time_limit=6)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"[aviso] escucha: {e}")
                time.sleep(0.3)
                continue

            self.hud.state_processing()
            try:
                text = r.recognize_google(audio, language=LANGUAGE)
                text = text.lower().strip()
                print(f"[oido] {text!r}")
                self.command_queue.put(text)
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"[aviso] sin conexion: {e}")
                self.has_net = False
                self.hud.state_no_internet()
                time.sleep(1.5)
                continue

            if not self.sleeping:
                self.hud.state_listening()
            else:
                self.hud.state_sleeping()

            recalibrate_in -= 1
            if recalibrate_in <= 0:
                try:
                    with mic as src:
                        r.adjust_for_ambient_noise(src, duration=0.5)
                except Exception:
                    pass
                recalibrate_in = 60

    # ---- procesado de cola ----
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
                if cmd == "__TOGGLE_SLEEP__":
                    self.toggle_sleep(); continue
                self._handle_voice(cmd)
        except queue.Empty:
            pass
        self.root.after(100, self._process_commands)

    def _handle_voice(self, text):
        # 1) emergencia siempre se procesa (incluso dormido)
        if any(t in text for t in INTENTS["EMERGENCY"]):
            self.hud.show_command("EMERGENCIA", ok=True)
            self.emergency_stop()
            return

        # 2) si esta dormido, solo despertar
        if self.sleeping:
            if any(t in text for t in INTENTS["WAKE"]):
                self.wake()
                self.hud.show_command("despierto", ok=True)
            return

        # 3) modo dictado: todo se teclea, salvo comandos especiales
        if self.dictating:
            self._handle_dictation(text)
            return

        # 4) coordenada con marcar/coger/soltar
        coord = parse_coordinate(text)
        if coord:
            tnorm = " " + text + " "

            # MARCAR (solo resaltar)
            if any(k in tnorm for k in (" marcar ", " marca ", " selecciona ",
                                        " seleccionar ", " resalta ",
                                        " resaltar ", " elige ", " elegir ")):
                self.grid.highlight_cell(coord[0], coord[1])
                self.hud.show_command(
                    f"marcado {LETTERS[coord[0]]}{coord[1] + 1}", ok=True)
                return

            # COGER (drag start)
            if any(k in tnorm for k in (" coger ", " coge ", " agarrar ",
                                        " agarra ", " sujeta ", " sujetar ",
                                        " arrastrar desde ")):
                self.grid.drag_start(coord[0], coord[1])
                self.dragging = True
                self.hud.show_command(
                    f"arrastrando desde {LETTERS[coord[0]]}{coord[1] + 1}",
                    ok=True)
                return

            # SOLTAR (drag end)
            if any(k in tnorm for k in (" soltar ", " suelta ", " sueltalo ",
                                        " suéltalo ", " arrastrar hasta ",
                                        " soltar en ")):
                if self.dragging:
                    self.grid.drag_end(coord[0], coord[1])
                    self.dragging = False
                    self.hud.show_command(
                        f"soltado en {LETTERS[coord[0]]}{coord[1] + 1}",
                        ok=True)
                else:
                    # Si no había arrastre, hacemos clic normal en destino
                    self.grid.click_cell(coord[0], coord[1])
                    self.hud.show_command(
                        f"clic {LETTERS[coord[0]]}{coord[1] + 1}", ok=True)
                return

            # CLIC normal con tipo
            mode = "left"
            if any(w in text for w in INTENTS["DOUBLE_CLICK"]):
                mode = "double"
            elif any(w in text for w in INTENTS["RIGHT_CLICK"]):
                mode = "right"
            ok = self.grid.click_cell(coord[0], coord[1], mode=mode)
            self.grid.clear_highlight()
            label = f"{LETTERS[coord[0]]}{coord[1] + 1}"
            modes = {"left": "clic", "double": "doble clic", "right": "clic dcho"}
            self.hud.show_command(f"{modes[mode]} {label}", ok=ok)
            return

        # 5) intencion sin coordenada
        intent = classify_intent(text)
        if intent is None:
            return
        self._dispatch_intent(intent, text)

    def _handle_dictation(self, text):
        # comandos especiales del dictado
        if any(t in text for t in INTENTS["DICTATE_END"]):
            self.stop_dictation()
            self.hud.show_command("dictado off", ok=True)
            return
        if any(t in text for t in INTENTS["DICTATE_DEL_WORD"]):
            pyautogui.hotkey("ctrl", "backspace")
            return
        if any(t in text for t in INTENTS["DICTATE_CLEAR"]):
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyautogui.press("delete")
            return
        # Tecleo via portapapeles para conservar acentos y ñ
        if HAS_PYPERCLIP:
            try:
                old = pyperclip.paste()
            except Exception:
                old = ""
            try:
                pyperclip.copy(text + " ")
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.05)
                pyperclip.copy(old)
            except Exception:
                pyautogui.typewrite(text + " ", interval=0.01)
        else:
            pyautogui.typewrite(text + " ", interval=0.01)

    def _dispatch_intent(self, intent, text):
        print(f"[intent] {intent}")
        ok = True

        if intent == "QUIT":
            self.quit(); return
        if intent == "SLEEP":
            self.sleep(); self.hud.show_command("dormido", ok=True); return

        if intent == "SHOW_GRID": self.grid.show()
        elif intent == "HIDE_GRID": self.grid.hide()
        elif intent == "CLEAR_HIGHLIGHT": self.grid.clear_highlight()

        elif intent == "SHOW_BAR": self.bar.show()
        elif intent == "HIDE_BAR": self.bar.hide()

        elif intent == "OPEN_KEYBOARD":
            if not self.keyboard_open:
                act_open_keyboard(); self.keyboard_open = True
        elif intent == "CLOSE_KEYBOARD":
            if self.keyboard_open:
                act_close_keyboard(); self.keyboard_open = False

        elif intent == "DICTATE_START": self.start_dictation()
        elif intent == "CANCEL_DRAG":
            if self.dragging:
                self.grid.drag_cancel(); self.dragging = False

        elif intent == "MOVE_UP":
            n = max(1, extract_number(text))
            x, y = pyautogui.position()
            pyautogui.moveTo(x, y - self.mouse_step * n, duration=0.05)
        elif intent == "MOVE_DOWN":
            n = max(1, extract_number(text))
            x, y = pyautogui.position()
            pyautogui.moveTo(x, y + self.mouse_step * n, duration=0.05)
        elif intent == "MOVE_LEFT":
            n = max(1, extract_number(text))
            x, y = pyautogui.position()
            pyautogui.moveTo(x - self.mouse_step * n, y, duration=0.05)
        elif intent == "MOVE_RIGHT":
            n = max(1, extract_number(text))
            x, y = pyautogui.position()
            pyautogui.moveTo(x + self.mouse_step * n, y, duration=0.05)
        elif intent == "FASTER":
            self.mouse_step = min(MOUSE_STEP_MAX,
                                  int(self.mouse_step * MOUSE_STEP_FACTOR))
            self.cfg["mouse_step"] = self.mouse_step
        elif intent == "SLOWER":
            self.mouse_step = max(MOUSE_STEP_MIN,
                                  int(self.mouse_step / MOUSE_STEP_FACTOR))
            self.cfg["mouse_step"] = self.mouse_step

        elif intent == "VOL_UP":   self.volume.up()
        elif intent == "VOL_DOWN": self.volume.down()
        elif intent == "VOL_MUTE": self.volume.mute()
        elif intent == "VOL_MAX":  self.volume.maximum()

        elif intent == "LEFT_CLICK":   act_left_click()
        elif intent == "DOUBLE_CLICK": act_double_click()
        elif intent == "RIGHT_CLICK":  act_right_click()

        elif intent == "COPY":         act_copy()
        elif intent == "PASTE":        act_paste()
        elif intent == "CUT":          act_cut()
        elif intent == "DELETE":       act_delete()
        elif intent == "SELECT_ALL":   act_select_all()
        elif intent == "ENTER":        act_enter()

        elif intent == "CLOSE_WINDOW": act_close_window()
        elif intent == "MINIMIZE":     act_minimize()
        elif intent == "MAXIMIZE":     act_maximize()
        elif intent == "SWITCH_WINDOW":act_switch_window()
        elif intent == "OPEN_EXPLORER":act_open_explorer()
        elif intent == "SHOW_DESKTOP": act_show_desktop()
        elif intent == "PROJECT":      act_project()
        else:
            ok = False

        nice_names = {
            "SHOW_GRID": "rejilla on", "HIDE_GRID": "rejilla off",
            "CLEAR_HIGHLIGHT": "marca limpiada",
            "SHOW_BAR": "barra on", "HIDE_BAR": "barra off",
            "OPEN_KEYBOARD": "teclado on", "CLOSE_KEYBOARD": "teclado off",
            "DICTATE_START": "dictado on",
            "CANCEL_DRAG": "arrastre cancelado",
            "FASTER": f"raton x{self.mouse_step}",
            "SLOWER": f"raton x{self.mouse_step}",
            "VOL_UP": "vol +", "VOL_DOWN": "vol -",
            "VOL_MUTE": "silencio", "VOL_MAX": "vol max",
            "LEFT_CLICK": "clic", "DOUBLE_CLICK": "doble clic",
            "RIGHT_CLICK": "clic dcho",
            "COPY": "copiar", "PASTE": "pegar", "CUT": "cortar",
            "DELETE": "borrar", "SELECT_ALL": "seleccionar todo",
            "ENTER": "intro",
            "CLOSE_WINDOW": "cerrar ventana", "MINIMIZE": "minimizar",
            "MAXIMIZE": "maximizar", "SWITCH_WINDOW": "alt+tab",
            "OPEN_EXPLORER": "explorador", "SHOW_DESKTOP": "escritorio",
            "PROJECT": "proyectar",
        }
        self.hud.show_command(nice_names.get(intent, intent.lower()), ok=ok)

    # ---- main ----
    def run(self):
        self.root.mainloop()


def main():
    print("=" * 64)
    print("  SUPERCAPA v4 - prototipo estable")
    print("=" * 64)
    print("Comandos clave (chuleta minima):")
    print("  - rejilla, ocultar")
    print("  - 'A 1'           -> clic")
    print("  - 'marcar A 1'    -> resaltar SIN clicar")
    print("  - 'doble A 1' / 'clic derecho B 5'")
    print("  - 'coger A 1' ... 'soltar T 15'  (arrastrar)")
    print("  - texto / quitar texto")
    print("  - dormir / despierta")
    print("  - socorro          -> parada de emergencia")
    print("  - salir del programa")
    print("Atajos: F8 rejilla  F9 salir  F10 teclado  F11 dormir")
    print("=" * 64)
    SuperCapa().run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
