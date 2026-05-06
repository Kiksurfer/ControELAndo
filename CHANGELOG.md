# Registro de cambios

Todas las notas relevantes de cada versión se documentan aquí.
El formato sigue las recomendaciones de [Keep a Changelog](https://keepachangelog.com/es-ES/).

## [2.0.0] — [DD de MM de AAAA]

Versión orientada al cumplimiento normativo y a la seguridad. Reescritura del componente de reconocimiento de voz para evitar la dependencia de servicios en la nube.

### Cambios importantes

- **Reconocimiento de voz local con Vosk**. Sustituido el motor anterior basado en la API web de Google. El audio del usuario ya no sale de su ordenador. El programa funciona sin conexión a internet.
- **Pantalla de consentimiento informado** en el primer arranque. Se cumple el deber de información del artículo 13 RGPD y la obligación del artículo 50 del Reglamento (UE) 2024/1689 sobre interacción con sistemas de IA.
- **Cifrado del archivo de configuración local** (`config.json`) cuando contiene fragmentos de voz personalizados.
- **Comando `bloquear`** con palabra de desbloqueo personal del usuario, para mitigar la inyección de comandos por terceros.
- **Confirmación verbal obligatoria** para acciones destructivas (cierre de ventanas con cambios sin guardar, borrado de archivos).

### Seguridad de distribución

- **Firma digital del ejecutable** mediante SignPath Foundation (gratuita para proyectos de código abierto).
- **Suma de verificación SHA-256** publicada junto al ejecutable en GitHub Releases.
- **Eliminadas** las indicaciones que invitaban al usuario a pulsar «Ejecutar de todas formas» en la advertencia de SmartScreen.
- **Política de divulgación responsable** documentada en `SECURITY.md`.

### Documentación

- Reescritura completa del documento legal (`legal.html`) con identificación del prestador conforme al artículo 10 de la LSSI, política de privacidad alineada con el artículo 13 RGPD y aviso legal independiente.
- Actualización del `README.md` con instrucciones de verificación de integridad.
- Nuevo archivo `NOTICE` con el listado de dependencias y sus licencias.
- Nueva pestaña de inicio (`index.html`) con etiquetado claro como sistema de IA y cláusula de no producto sanitario.

### Eliminado

- Eliminada la dependencia `SpeechRecognition` (ya no se utiliza la API web de Google).
- Eliminada la indicación pública de pulsar «Ejecutar de todas formas».
- Eliminada la mención al envío del audio a Google en el documento legal.

## [1.0.0] — [Versión anterior]

Versión inicial.
