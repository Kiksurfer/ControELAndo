# Registro de cambios

Todas las notas relevantes de cada versión se documentan aquí.
El formato sigue las recomendaciones de [Keep a Changelog](https://keepachangelog.com/es-ES/).

## [1.1.0] — En desarrollo

### Añadido
- Sistema de alias de voz personalizados: cada usuario graba cómo pronuncia cada comando
- Gestor visual de alias ("Grabar Voz") accesible desde la barra flotante
- Zoom de celda con símbolos visuales (◆ ● ▲ ★) para selección precisa dentro de una celda
- Modo dictado con puntuación por voz (punto, coma, interrogación, exclamación…)
- Tres perfiles de micrófono: Voz suave / Normal / Ruidoso
- Confirmación sonora configurable (pitido) con botón de activación/desactivación
- Historial de los últimos 12 comandos ejecutados (comando "historial")
- Ventana de ayuda rápida con todos los comandos (comando "ayuda")
- Reposo automático tras 5 minutos de inactividad
- Scroll con número: "subir página 5", "bajar página 10"
- Página siguiente/anterior con número: "página siguiente 3"
- Comando "centrar barra" para recolocar la barra flotante
- Comando "repetir" / "otra vez" para repetir el último comando
- Comando "deshacer" / "volver atrás" (Ctrl+Z)
- HUD muestra en tiempo real lo que el programa está escuchando
- Rejilla 14×15 (sin columna I, que Google confunde con Y)
- Coordenada sin clic: al decir la celda solo mueve el cursor

### Eliminado
- Teclado virtual (se usa el del sistema operativo)
- Columna I de la rejilla (causa errores de reconocimiento en español)
- Opciones de tamaño de rejilla por voz

## [1.0.0] — Versión inicial

Primera versión pública. Control del ordenador por voz mediante Google Speech
Recognition, rejilla superpuesta, alias de voz y barra flotante.
