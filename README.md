# tapunto-voz

**Control del ordenador por voz para personas con movilidad reducida.**

[![Construir tapunto-voz.exe](https://github.com/Kiksurfer/ControELAndo/actions/workflows/build.yml/badge.svg)](https://github.com/Kiksurfer/ControELAndo/actions/workflows/build.yml)
[![Última versión](https://img.shields.io/github/v/release/Kiksurfer/ControELAndo?label=última%20versión)](https://github.com/Kiksurfer/ControELAndo/releases/latest)
[![Licencia](https://img.shields.io/github/license/Kiksurfer/ControELAndo)](LICENSE)

---

## ¿Qué es?

tapunto-voz es un programa gratuito de código abierto que permite manejar el ordenador completamente con la voz. Mediante una rejilla superpuesta a la pantalla, el usuario puede mover el cursor, hacer clic, escribir texto y ejecutar cualquier acción del sistema operativo sin necesidad de usar las manos.

Diseñado especialmente para personas con **Esclerosis Lateral Amiotrófica (ELA)** u otras condiciones que limiten el uso de las manos.

> **Requiere conexión a internet.** El reconocimiento de voz se realiza mediante Google Speech Recognition. El audio se envía a los servidores de Google para su transcripción. Consulta la [política de privacidad](https://tapunto.app/legal.html) para más información.

## Descarga

👉 **[Descargar tapunto-voz.exe (última versión)](https://github.com/Kiksurfer/ControELAndo/releases/latest/download/tapunto-voz.exe)**

**Requisitos:** Windows 10 / 11 · Micrófono · Conexión a internet

> Al ejecutar por primera vez, Windows puede mostrar una advertencia de seguridad.
> Haz clic en **"Más información"** y luego en **"Ejecutar de todas formas"** para continuar.

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
| `pitido on` / `pitido off` | Activa o desactiva el sonido de confirmación |
| `historial` | Muestra los últimos 12 comandos ejecutados |
| `centrar barra` | Recoloca la barra flotante en pantalla |

## Desarrolladores

- **Enrique García Prats**
- **Jorge García Prats**
- **Alicia Prats Martínez**

## Condiciones de uso y privacidad

Lee las [condiciones de uso y política de privacidad](https://tapunto.app/legal.html) antes de instalar el programa.

- **Contacto general:** contacto@tapunto.app
- **Privacidad:** privacidad@tapunto.app

## Compilar desde el código fuente

```bash
git clone https://github.com/Kiksurfer/ControELAndo.git
cd ControELAndo
pip install -r requirements.txt
python supercapa.py
```

Para generar el `.exe` automáticamente mediante GitHub Actions:

```bash
git tag v1.0
git push origin v1.0
```

## Licencia

Ver archivo `LICENSE` para los términos completos.
