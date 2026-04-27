# ControELAndo · SuperCapa

Capa de accesibilidad por voz para Windows. Pensada para personas con
movilidad reducida que conservan el habla: superpone una cuadrícula sobre
la pantalla y permite controlar el cursor, dictar texto, abrir programas
y manejar ventanas hablando.

## Descargar

**Para usuarios:** [última versión publicada (Releases)](../../releases/latest)

Descarga `SuperCapa.exe`, doble clic y va. No hay que instalar Python ni
nada.

> Si Windows muestra un aviso azul de SmartScreen al abrir el .exe:
> **Más información** → **Ejecutar de todas formas**. Solo la primera vez.

## Novedades v4

- **Indicador de escucha** en pantalla (verde = oyendo, amarillo =
  procesando, gris = dormido, rojo = sin micro o sin internet).
- **Confirmación visual** del último comando reconocido.
- **Modo dormir/despertar**: di *"dormir"* y deja de actuar; *"despierta"*
  y vuelve.
- **Comando de emergencia** *"socorro"* que deja todo en estado seguro.
- **Configuración persistente** (`config.json` recuerda preferencias).
- **Marcar celda sin clicar**: *"marcar A1"* la resalta en verde.
- **Arrastrar archivos por voz**: *"coger A1"* … *"soltar T15"*.
- **Cooldown anti-doble-clic**.
- **Barra flotante** ahora abajo-centro y minimizada por defecto.

## Comandos de voz (resumen)

| Categoría | Ejemplos |
|-----------|----------|
| Cuadrícula | "rejilla", "ocultar", "marcar A1", "desmarcar" |
| Clic | "A uno", "be 7", "doble a 3", "clic derecho b 5" |
| Arrastrar | "coger A1" → "soltar T15", "cancelar arrastre" |
| Edición | "copiar", "pegar", "cortar", "borrar", "seleccionar todo", "intro" |
| Ventanas | "cierra esto", "ponlo en grande", "minimiza", "cambia de ventana" |
| Sistema | "abre una carpeta", "muestra el escritorio", "teclado" |
| Dictado | "texto", "borrar palabra", "borrar todo", "quitar texto" |
| Ratón | "arriba", "abajo 3", "izquierda", "derecha", "más rápido" |
| Volumen | "sube el volumen", "silencio", "volumen máximo" |
| Estado | "dormir", "despierta", "socorro" |
| Cerrar | "salir del programa" |

Atajos de teclado: **F8** rejilla · **F9** salir · **F10** teclado · **F11** dormir

## Para desarrolladores

El `.exe` se compila automáticamente en GitHub Actions cada vez que se
sube código. Para probar en local:

```bash
pip install pyautogui SpeechRecognition keyboard pyaudio pyperclip pycaw comtypes
python supercapa.py
```

Para publicar una nueva versión pública:

```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub compila los `.exe` y publica una Release automáticamente.

## Licencia

Ver [LICENSE](LICENSE).
