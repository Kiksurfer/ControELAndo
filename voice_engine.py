"""
voice_engine.py — Motor de reconocimiento de voz LOCAL.

Sustituye al uso anterior de la API web de Google. El audio se procesa
ÍNTEGRAMENTE en el ordenador del usuario mediante el motor Vosk.

Implicaciones regulatorias positivas (frente a la versión 1.0):
  • No hay transferencia internacional de datos personales.
  • No hay encargado de tratamiento externo en la cadena del audio.
  • La opción cumple el principio de privacidad desde el diseño (art. 25 RGPD).
  • Permite el uso del programa sin conexión a internet.

Si en el futuro se quisiera ofrecer al usuario la opción de un motor en la
nube (más preciso pero con tratamiento externo), debe implementarse como
una elección explícita en el cuadro de consentimiento, NUNCA por defecto.
"""

import os
import sys
import queue
import json
import sounddevice as sd
import vosk

# Frecuencia de muestreo recomendada por Vosk
SAMPLE_RATE = 16000
BLOCK_SIZE = 8000


def model_path():
    """
    Devuelve la ruta del modelo Vosk.

    En desarrollo: subdirectorio `model/` junto al script.
    En el .exe compilado: PyInstaller lo extrae a sys._MEIPASS/model.
    """
    if getattr(sys, "frozen", False):
        # Estamos dentro de un binario PyInstaller
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "model")


class VoiceEngine:
    """
    Motor de reconocimiento de voz local. Uso típico:

        engine = VoiceEngine()
        engine.start()
        for command in engine.listen():
            handle(command)
        engine.stop()
    """

    def __init__(self):
        path = model_path()
        if not os.path.exists(path):
            raise RuntimeError(
                f"Modelo Vosk no encontrado en: {path}\n"
                "Si compilas localmente, descarga el modelo desde "
                "https://alphacephei.com/vosk/models y descomprímelo "
                "en una carpeta llamada 'model'."
            )
        self._model = vosk.Model(path)
        self._recognizer = vosk.KaldiRecognizer(self._model, SAMPLE_RATE)
        self._queue = queue.Queue()
        self._stream = None
        self._listening = False

    # --- API pública ---------------------------------------------------

    def start(self):
        """Inicia la captura de audio del micrófono."""
        if self._listening:
            return
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype="int16",
            channels=1,
            callback=self._on_audio,
        )
        self._stream.start()
        self._listening = True

    def stop(self):
        """Detiene la captura y libera recursos."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._listening = False

    def listen(self):
        """
        Generador que produce los textos reconocidos a medida que el usuario
        habla. Cada elemento devuelto es una cadena con el texto final
        reconocido para una pausa.
        """
        while self._listening:
            data = self._queue.get()
            if data is None:
                break
            if self._recognizer.AcceptWaveform(data):
                result = json.loads(self._recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    yield text

    def is_listening(self) -> bool:
        return self._listening

    # --- Internos ------------------------------------------------------

    def _on_audio(self, indata, frames, time_info, status):
        """Callback de sounddevice. Encola los bloques de audio."""
        if status:
            # No imprimimos a stdout para no llenar logs en producción
            pass
        self._queue.put(bytes(indata))


# --- Pequeña prueba manual ---------------------------------------------

if __name__ == "__main__":
    print("Habla al micrófono. Pulsa Ctrl+C para salir.")
    eng = VoiceEngine()
    eng.start()
    try:
        for text in eng.listen():
            print(">>", text)
    except KeyboardInterrupt:
        pass
    finally:
        eng.stop()
