"""
secure_config.py — Almacenamiento cifrado de la configuración local.

Cifra el archivo `config.json` con AES (a través de Fernet) usando una clave
derivada del nombre del usuario del sistema operativo. Esto protege los
fragmentos de voz personalizados (alias) que el usuario haya grabado en el
caso de que un tercero acceda al archivo.

NOTA: el cifrado por nombre de usuario no es una protección frente a un
atacante con acceso completo al equipo, sino una medida razonable para
evitar la lectura accidental por personas que copian el archivo a otro
ordenador. La frase de paso real puede sustituirse por una solicitada al
usuario en el primer arranque para mayor seguridad.
"""

import os
import json
import getpass
import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken

CONFIG_PLAIN_NAME = "config.json"
CONFIG_ENCRYPTED_NAME = "config.json.enc"

# Constante de aplicación. NO es una contraseña por sí sola; se combina con
# el nombre del usuario del sistema para derivar la clave.
APP_SALT = b"tapunto-voz/v2/secure-config"


def _config_dir():
    base = os.path.dirname(os.path.abspath(__file__))
    return base


def _derive_key() -> bytes:
    """Deriva una clave Fernet a partir del usuario actual y la sal de la app."""
    user = getpass.getuser().encode("utf-8")
    raw = hashlib.pbkdf2_hmac("sha256", user, APP_SALT, iterations=200_000)
    return base64.urlsafe_b64encode(raw)


def load_config(default: dict | None = None) -> dict:
    """Lee y descifra el archivo de configuración. Devuelve un dict."""
    path = os.path.join(_config_dir(), CONFIG_ENCRYPTED_NAME)
    if not os.path.exists(path):
        return dict(default or {})

    with open(path, "rb") as f:
        token = f.read()

    try:
        plaintext = Fernet(_derive_key()).decrypt(token)
        return json.loads(plaintext.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError):
        # Archivo corrupto o de otro usuario: se ignora y se vuelve al default
        return dict(default or {})


def save_config(data: dict) -> None:
    """Cifra y guarda la configuración."""
    path = os.path.join(_config_dir(), CONFIG_ENCRYPTED_NAME)
    plaintext = json.dumps(data, ensure_ascii=False).encode("utf-8")
    token = Fernet(_derive_key()).encrypt(plaintext)
    with open(path, "wb") as f:
        f.write(token)


def migrate_legacy_plain_config():
    """
    Si existe un config.json en texto plano (versión 1.0), lo cifra y
    elimina el archivo plano. Compatibilidad con la versión anterior.
    """
    plain_path = os.path.join(_config_dir(), CONFIG_PLAIN_NAME)
    if not os.path.exists(plain_path):
        return
    try:
        with open(plain_path, encoding="utf-8") as f:
            data = json.load(f)
        save_config(data)
        os.remove(plain_path)
    except (OSError, json.JSONDecodeError):
        pass


if __name__ == "__main__":
    migrate_legacy_plain_config()
    cfg = load_config({"step": 10, "profile": "normal"})
    print("Configuración actual:", cfg)
    cfg["last_run"] = "manual-test"
    save_config(cfg)
    print("Guardado y vuelto a leer:", load_config())
