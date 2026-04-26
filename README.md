# ControELAndo · SuperCapa

Capa de accesibilidad por voz para Windows. Pensada para personas con
movilidad reducida que conservan el habla: superpone una cuadrícula
sobre la pantalla y permite controlar el cursor, dictar texto, abrir
programas y manejar ventanas hablando.

## Descargar

**Para usuarios:** [última versión publicada (Releases)](../../releases/latest)

Descarga `SuperCapa.exe`, doble clic y va. No hay que instalar Python
ni nada.

> Si Windows muestra un aviso azul de SmartScreen al abrir el .exe:
> **Más información** → **Ejecutar de todas formas**. Solo la primera
> vez.

## Funciones principales

- **Cuadrícula superpuesta 20×20** (A1 … T20). Decir una coordenada
  hace clic en esa casilla.
- **Lenguaje natural** para comandos de sistema: *"cierra esto"*,
  *"ponlo en grande"*, *"abre una carpeta"*, *"cambia de ventana"*…
- **Modo dictado**: di *"texto"* y todo lo que digas se teclea en la
  app activa.
- **Control direccional del ratón por voz**: *"arriba tres"*,
  *"derecha"*, *"más rápido"*…
- **Control de volumen** y teclado en pantalla por voz.
- **Click-through**: la capa no bloquea los clics del ratón.

## Comandos de voz (resumen)

| Categoría | Ejemplos |
|-----------|----------|
| Cuadrícula | "rejilla", "ocultar", "A uno", "be 7", "doble a 3" |
| Edición | "copiar", "pegar", "cortar", "borrar", "intro" |
| Ventanas | "cierra esto", "ponlo en grande", "minimiza", "cambia de ventana" |
| Sistema | "abre una carpeta", "muestra el escritorio", "teclado" |
| Dictado | "texto", "borrar palabra", "borrar todo", "quitar texto" |
| Ratón | "arriba", "abajo", "izquierda", "derecha", "clic", "doble clic" |
| Volumen | "sube el volumen", "silencio", "volumen máximo" |
| Cerrar | "salir del programa" |

Atajos de teclado: **F7** moto · **F8** rejilla · **F9** salir · **F10** teclado

## Para desarrolladores

El `.exe` se compila automáticamente en GitHub Actions cada vez que se
sube código. Para probar en local:

```bash
pip install pyautogui SpeechRecognition keyboard pyaudio pyperclip pycaw comtypes
python supercapa.py
```

Para publicar una nueva versión:

```bash
git tag v1.2.0
git push origin v1.2.0
```

GitHub compila los `.exe` y publica una Release automáticamente.

## Licencia

Ver [LICENSE](LICENSE).
