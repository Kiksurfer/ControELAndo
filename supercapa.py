"""
supercapa.py — ESQUELETO DE REFERENCIA para tapunto-voz v2.0.

ATENCIÓN
========

Este archivo es un PUNTO DE PARTIDA que muestra cómo integrar las medidas
de seguridad y cumplimiento normativo en el programa. NO es la versión
completa: la lógica de la rejilla, el dictado de texto, los comandos de
zoom y el resto de funcionalidades del programa original deben portarse
desde el supercapa.py existente.

Este esqueleto demuestra:
  • Pantalla de consentimiento informado al primer arranque (RGPD + AI Act).
  • Reconocimiento de voz LOCAL con Vosk (sin tratamiento por terceros).
  • Comando «bloquear» con palabra de desbloqueo personal.
  • Confirmación verbal obligatoria para acciones destructivas.
  • Cifrado del archivo de configuración local.
  • Cierre limpio y registro mínimo en memoria.

Para integrar con el código original, sustituir las llamadas a
`run_command(text)` por la lógica completa de interpretación.
"""

import sys
import logging
import pyautogui
import keyboard
import pyperclip

import consent_dialog
import voice_engine
import secure_config


# Acciones que requieren confirmación verbal por considerarse destructivas
DESTRUCTIVE_KEYWORDS = (
    "borrar", "eliminar", "cerrar sin guardar", "formatear",
    "vaciar papelera", "salir sin guardar"
)

# Comandos de control del propio programa
LOCK_KEYWORD = "bloquear"
UNLOCK_TEMPLATE = "desbloquear {word}"   # se completa con la palabra del usuario
SLEEP_KEYWORD = "dormir"
WAKE_KEYWORD = "despierta"
EXIT_KEYWORD = "salir tapunto"


# Logger en memoria (no se escribe a disco para evitar dejar rastro de comandos)
logger = logging.getLogger("tapunto-voz")
logger.setLevel(logging.INFO)
logger.addHandler(logging.NullHandler())


class TapuntoApp:
    def __init__(self):
        # 1) Migrar configuración antigua si la hay
        secure_config.migrate_legacy_plain_config()

        # 2) Cargar configuración cifrada
        self.config = secure_config.load_config(
            default={
                "step": 10,
                "profile": "normal",
                "unlock_word": "",   # el usuario la define en su primer uso
                "ai_alias": {},
            }
        )

        # 3) Estado interno
        self.locked = False
        self.sleeping = False
        self.command_history = []  # solo en memoria, máx. 12 entradas
        self.engine = None
        self.pending_destructive = None  # comando pendiente de confirmación

    # --- Ciclo de vida ----------------------------------------------------

    def run(self):
        """Punto de entrada principal."""
        # Consentimiento informado (RGPD + AI Act art. 50)
        consent_dialog.ensure_consent()

        # Inicializar motor de voz local
        try:
            self.engine = voice_engine.VoiceEngine()
            self.engine.start()
        except RuntimeError as exc:
            logger.error("Error iniciando el motor de voz: %s", exc)
            sys.exit(1)

        try:
            for text in self.engine.listen():
                self.handle_command(text)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self):
        """Cierre limpio."""
        if self.engine:
            self.engine.stop()
        secure_config.save_config(self.config)
        logger.info("tapunto-voz cerrado correctamente")

    # --- Procesamiento de comandos ---------------------------------------

    def handle_command(self, text: str):
        """Despacha un comando reconocido."""
        text = text.lower().strip()
        if not text:
            return

        # Mantener historial en memoria, máximo 12 (privacidad: no a disco)
        self.command_history.append(text)
        if len(self.command_history) > 12:
            self.command_history.pop(0)

        # 1) Comandos de control del programa que funcionan SIEMPRE
        if text == EXIT_KEYWORD:
            self.shutdown()
            sys.exit(0)

        # 2) Estado de bloqueo: solo se atiende la palabra de desbloqueo
        if self.locked:
            self.try_unlock(text)
            return

        # 3) Estado de sueño: solo «despierta»
        if self.sleeping:
            if text == WAKE_KEYWORD:
                self.sleeping = False
            return

        # 4) Solicitudes de bloqueo y sueño
        if text == LOCK_KEYWORD:
            self.lock()
            return
        if text == SLEEP_KEYWORD:
            self.sleeping = True
            return

        # 5) Confirmación pendiente de acción destructiva
        if self.pending_destructive:
            if text in ("sí", "si", "confirmar", "adelante"):
                self.execute_destructive(self.pending_destructive)
            self.pending_destructive = None
            return

        # 6) Si el comando es destructivo, pedir confirmación
        if any(k in text for k in DESTRUCTIVE_KEYWORDS):
            self.pending_destructive = text
            self.speak_warning(
                f"Has dicho «{text}». Si quieres confirmarlo, di «sí». "
                "Cualquier otra cosa cancelará la acción."
            )
            return

        # 7) Comando normal: ejecutarlo
        self.execute_command(text)

    # --- Operaciones de control ------------------------------------------

    def lock(self):
        """Bloquea el reconocimiento."""
        self.locked = True
        self.speak_warning("Programa bloqueado. Di la palabra de desbloqueo.")

    def try_unlock(self, text: str):
        """Comprueba si el texto contiene la palabra de desbloqueo."""
        word = (self.config.get("unlock_word") or "").lower().strip()
        if not word:
            # Sin palabra configurada: cualquier «desbloquear» vale la primera vez
            if text.startswith("desbloquear "):
                proposed = text.split(" ", 1)[1].strip()
                self.config["unlock_word"] = proposed
                secure_config.save_config(self.config)
                self.locked = False
            return
        if word in text:
            self.locked = False

    def execute_destructive(self, text: str):
        """Ejecuta una acción destructiva tras confirmación."""
        logger.info("Ejecutando acción destructiva confirmada: %s", text)
        # Aquí va la lógica concreta del comando original
        self.execute_command(text)

    def execute_command(self, text: str):
        """
        Despachador del comando reconocido.

        AQUÍ VA LA LÓGICA COMPLETA DEL TAPUNTO-VOZ ORIGINAL:
        rejilla, clic, zoom, dictado, ayuda, dormir, etc.
        """
        # Esqueleto de ejemplo. Sustituir por la implementación completa.
        if text == "ayuda":
            self.show_help()
        elif text == "rejilla":
            self.show_grid()
        # ... (resto de comandos)

    # --- Reproducciones simples (sin síntesis de voz por ahora) ----------

    def speak_warning(self, message: str):
        """
        Muestra un aviso al usuario. La versión actual usa una notificación
        del sistema. Si en el futuro se incorpora síntesis de voz, hay que
        etiquetar la salida como contenido sintético generado por IA
        conforme al artículo 50.2 del Reglamento (UE) 2024/1689.
        """
        try:
            from win10toast_persist import ToastNotifier
            ToastNotifier().show_toast("tapunto-voz", message, duration=4)
        except Exception:
            # Fallback simple: imprimir en consola si no hay GUI
            print("[tapunto-voz]", message)

    def show_help(self):
        """Muestra la lista de comandos disponibles."""
        # Implementación pendiente: una pequeña ventana con la lista
        pass

    def show_grid(self):
        """Activa la rejilla superpuesta a la pantalla."""
        # Implementación pendiente: portar desde la versión original
        pass


def main():
    pyautogui.FAILSAFE = True   # Mover el ratón a la esquina superior izquierda aborta
    app = TapuntoApp()
    app.run()


if __name__ == "__main__":
    main()
