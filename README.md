# tapunto-voz

**Control del ordenador por voz para personas con movilidad reducida.**

[![Construir tapunto-voz.exe](https://github.com/USUARIO/REPOSITORIO/actions/workflows/build.yml/badge.svg)](https://github.com/USUARIO/REPOSITORIO/actions/workflows/build.yml)
[![Última versión](https://img.shields.io/github/v/release/USUARIO/REPOSITORIO?label=última%20versión)](https://github.com/USUARIO/REPOSITORIO/releases/latest)
[![Licencia](https://img.shields.io/github/license/USUARIO/REPOSITORIO)](LICENSE)

---

## ¿Qué es?

tapunto-voz es un programa gratuito de código abierto que permite manejar el ordenador completamente con la voz. Mediante una rejilla superpuesta a la pantalla, el usuario puede mover el cursor, hacer clic, escribir texto y ejecutar cualquier acción del sistema operativo sin necesidad de usar las manos.

Diseñado especialmente para personas con esclerosis lateral amiotrófica (ELA) u otras condiciones que limiten el uso de las manos.

> **Funciona sin conexión a internet.** El reconocimiento de voz se realiza localmente en tu ordenador con el motor Vosk. El audio no sale de tu equipo en ningún momento.

## Descarga

👉 **[Descargar tapunto-voz.exe (última versión)](https://github.com/USUARIO/REPOSITORIO/releases/latest/download/tapunto-voz.exe)**

**Requisitos:** Windows 10 / 11 · Micrófono

### Verificación de la descarga

Antes de ejecutar el programa, comprueba que el archivo descargado es auténtico:

**1. Verifica la firma digital.** Haz clic derecho sobre `tapunto-voz.exe` → Propiedades → pestaña «Firmas digitales». La firma debe corresponder al titular indicado en las [condiciones de uso](https://tapunto.app/legal.html).

**2. Verifica el hash SHA-256.** Junto al ejecutable se publica un archivo `tapunto-voz.exe.sha256`. Para comprobarlo, abre PowerShell en la carpeta donde lo hayas descargado y ejecuta:

```powershell
Get-FileHash -Algorithm SHA256 .\tapunto-voz.exe
```

El valor mostrado debe coincidir con el contenido del archivo `.sha256`.

> Si Windows muestra una advertencia de SmartScreen, **NO la ignores**: comprueba primero la firma y el hash. Si todo cuadra, puedes proceder con seguridad. Si algo no cuadra, no ejecutes el archivo y avisa por correo a contacto@tapunto.app.

## Primer uso

La primera vez que abras el programa, aparecerá una pantalla de información y consentimiento que te explicará:

- Que el programa utiliza un sistema de inteligencia artificial para reconocer tu voz.
- Que el reconocimiento se realiza localmente y el audio no sale de tu ordenador.
- Qué datos guarda el programa en tu equipo y dónde.
- Cómo retirar el consentimiento en cualquier momento.

Solo si aceptas esta información el programa se activa.

## Comandos principales

| Di esto | Resultado |
|---|---|
| `rejilla` | Muestra la rejilla sobre la pantalla |
| `A 5` / `B 12` | Mueve el cursor a esa celda |
| `clic A 5` | Mueve y hace clic |
| `zoom A5` | Subdivide la celda en 4 para mayor precisión |
| `texto` | Activa el modo dictado |
| `ayuda` | Muestra todos los comandos disponibles |
| `dormir` / `despierta` | Pausa y reactiva el programa |
| `bloquear` | Bloquea el reconocimiento (requiere palabra de desbloqueo personal) |

## Desarrolladores

- Enrique García Prats
- Jorge García Prats
- Alicia Prats Martínez

## Condiciones de uso, privacidad y contacto

- **[Condiciones de uso](https://tapunto.app/legal.html)** y política de privacidad.
- **Contacto general:** contacto@tapunto.app
- **Privacidad y derechos del interesado:** privacidad@tapunto.app
- **Reportar vulnerabilidades de seguridad:** ver [SECURITY.md](SECURITY.md)

## Licencia

El código fuente se distribuye bajo la licencia indicada en el archivo `LICENSE`. Las dependencias de terceros se listan en `NOTICE` con sus respectivas licencias.

## Compilar desde el código fuente

```bash
git clone https://github.com/USUARIO/REPOSITORIO.git
cd REPOSITORIO
python -m venv .venv
.venv\Scripts\activate     # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python supercapa.py
```

Para generar el `.exe` final, GitHub Actions se encarga automáticamente al crear un tag de versión:

```bash
git tag v2.0
git push origin v2.0
```
