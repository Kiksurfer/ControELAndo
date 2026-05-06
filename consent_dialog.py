"""
consent_dialog.py — Pantalla de consentimiento informado.

Cumple con:
  • Artículo 13 RGPD (información al interesado en el momento de la recogida).
  • Artículo 7 RGPD (consentimiento libre, específico, informado e inequívoco).
  • Artículo 50.1 del Reglamento (UE) 2024/1689 (información de que el usuario
    está interactuando con un sistema de IA).
  • Principio de privacidad desde el diseño (artículo 25 RGPD): el motor de
    reconocimiento es local y el audio NO sale del ordenador del usuario.

El consentimiento se almacena localmente en `consent.json` con marca temporal,
versión del documento aceptado y resultado. El archivo no se sincroniza con
ningún servicio externo.
"""

import json
import os
import sys
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# Versión del texto de consentimiento. Si se modifica el contenido,
# debe incrementarse este número para que se vuelva a solicitar al usuario.
CONSENT_VERSION = "2.0"
CONSENT_FILE = "consent.json"

CONSENT_TEXT = """\
INFORMACIÓN PREVIA AL USO DE TAPUNTO-VOZ

Antes de utilizar el programa, lee atentamente la siguiente información.
Solo si la aceptas se activarán las funciones de reconocimiento de voz.

1. ¿QUÉ ES ESTE PROGRAMA?

tapunto-voz permite manejar el ordenador con la voz. Está pensado especialmente
para personas con esclerosis lateral amiotrófica y otras condiciones que limiten
el uso de las manos.

2. SISTEMA DE INTELIGENCIA ARTIFICIAL

Este programa utiliza un sistema de inteligencia artificial (motor Vosk) para
reconocer tu voz y traducirla a comandos. La transcripción la realiza un modelo
de aprendizaje automático y, por tanto, puede contener errores. Tenlo presente
al utilizar el programa para acciones críticas.

(Información facilitada conforme al artículo 50 del Reglamento (UE) 2024/1689
sobre inteligencia artificial.)

3. TUS DATOS PERSONALES

El reconocimiento de voz se realiza ÍNTEGRAMENTE en tu ordenador. El audio
capturado por el micrófono NO se envía a ningún servidor, NO se almacena en
disco y NO se comparte con ningún tercero. Se procesa en memoria, se traduce
a texto y se descarta de inmediato.

El programa guarda en tu ordenador, en la misma carpeta del ejecutable:
  • config.json (cifrado): tus preferencias de uso y, si activas el aprendizaje
    de comandos personalizados, fragmentos breves de tu voz.
  • consent.json: registro de este consentimiento.

Estos archivos no salen de tu equipo. Si desinstalas el programa o borras la
carpeta, los datos desaparecen.

4. RESPONSABLE DEL PROYECTO

[NOMBRE COMPLETO o DENOMINACIÓN SOCIAL]
NIF: [NIF]
Dirección: [DIRECCIÓN POSTAL]
Correo de privacidad: privacidad@tapunto.app

Para más información sobre tus derechos (acceso, rectificación, supresión,
oposición, limitación, portabilidad, retirada del consentimiento) consulta
la Política de Privacidad completa en https://tapunto.app/legal.html.

5. SIN GARANTÍA Y NO SUSTITUTIVO DE TRATAMIENTO MÉDICO

El programa se ofrece sin garantía de funcionamiento. NO es un producto
sanitario y NO sustituye en ningún caso la atención médica, la terapia
ocupacional, la fisioterapia, la logopedia ni cualquier otro tratamiento.

6. RETIRADA DEL CONSENTIMIENTO

Puedes retirar este consentimiento en cualquier momento desinstalando el
programa o eliminando el archivo `consent.json`. La retirada no afecta a
la licitud del tratamiento basado en el consentimiento previo a su retirada.
"""


def consent_path():
    """Devuelve la ruta absoluta del archivo de consentimiento."""
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(base, CONSENT_FILE)


def has_valid_consent():
    """Comprueba si el usuario ya ha aceptado la versión actual."""
    path = consent_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return (
            data.get("accepted") is True
            and data.get("version") == CONSENT_VERSION
        )
    except (OSError, json.JSONDecodeError):
        return False


def save_consent(accepted: bool):
    """Guarda el resultado del consentimiento con marca temporal."""
    record = {
        "accepted": accepted,
        "version": CONSENT_VERSION,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(consent_path(), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def show_consent_dialog() -> bool:
    """
    Muestra la ventana de consentimiento. Devuelve True si el usuario acepta,
    False si rechaza. Si el usuario cierra la ventana sin pulsar nada,
    se considera rechazo (consentimiento NO inequívoco).
    """
    root = tk.Tk()
    root.title("tapunto-voz — Información y consentimiento")
    root.geometry("720x620")
    root.resizable(True, True)

    accepted = {"value": False}

    # Cabecera
    header = tk.Frame(root, bg="#1565C0", height=70)
    header.pack(fill="x")
    tk.Label(
        header,
        text="Información previa al uso",
        font=("Segoe UI", 16, "bold"),
        fg="white",
        bg="#1565C0",
    ).pack(pady=20)

    # Cuerpo desplazable con el texto
    body = tk.Frame(root)
    body.pack(fill="both", expand=True, padx=20, pady=15)

    text_widget = tk.Text(
        body,
        wrap="word",
        font=("Segoe UI", 10),
        relief="flat",
        bg="#FAFAFA",
        padx=12,
        pady=12,
    )
    scrollbar = ttk.Scrollbar(body, orient="vertical", command=text_widget.yview)
    text_widget.config(yscrollcommand=scrollbar.set)
    text_widget.insert("1.0", CONSENT_TEXT)
    text_widget.config(state="disabled")
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Casilla de aceptación
    chk_frame = tk.Frame(root)
    chk_frame.pack(fill="x", padx=20, pady=(5, 0))
    accepted_var = tk.BooleanVar(value=False)
    chk = ttk.Checkbutton(
        chk_frame,
        text=(
            "He leído la información, comprendo qué hace el programa y "
            "acepto utilizarlo en estas condiciones."
        ),
        variable=accepted_var,
    )
    chk.pack(anchor="w")

    # Botones
    btn_frame = tk.Frame(root)
    btn_frame.pack(fill="x", padx=20, pady=15)

    def on_accept():
        if not accepted_var.get():
            messagebox.showwarning(
                "Consentimiento requerido",
                "Para usar el programa debes marcar la casilla de aceptación.",
            )
            return
        accepted["value"] = True
        save_consent(True)
        root.destroy()

    def on_reject():
        accepted["value"] = False
        save_consent(False)
        root.destroy()

    btn_reject = tk.Button(
        btn_frame, text="No acepto y salgo del programa",
        command=on_reject, font=("Segoe UI", 10), width=28
    )
    btn_reject.pack(side="left")

    btn_accept = tk.Button(
        btn_frame, text="Acepto y continúo",
        command=on_accept, font=("Segoe UI", 10, "bold"),
        bg="#1565C0", fg="white", width=22
    )
    btn_accept.pack(side="right")

    # Cierre por la X = rechazo
    root.protocol("WM_DELETE_WINDOW", on_reject)

    root.mainloop()
    return accepted["value"]


def ensure_consent():
    """
    Punto de entrada. Si no hay consentimiento válido, lo solicita.
    Si el usuario rechaza, sale del programa.
    """
    if has_valid_consent():
        return
    if not show_consent_dialog():
        sys.exit(0)


if __name__ == "__main__":
    ensure_consent()
    print("Consentimiento aceptado, el programa puede continuar.")
