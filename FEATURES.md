# Backlog de features y mejoras

Leyenda: `[ ]` pendiente · `[-]` en progreso · `[x]` completado.

## P0 — Fiabilidad inmediata

- [x] Mostrar elementos `QUEUED` en la pestaña Cola.
- [x] Corregir pausa/reanudación sin convertir pausas en cancelaciones.
- [x] Detener cola, workers y procesos al cerrar la aplicación.
- [x] Aplicar inmediatamente el cambio de carpeta de salida.
- [x] Usar el formato predeterminado en el diálogo de añadir.
- [x] Detectar correctamente la ruta final de MP4 fusionado y MP3 extraído.
- [x] Clasificar correctamente éxito total, éxito parcial, cancelación y error.
- [x] Añadir timeout y terminación forzada controlada para yt-dlp.
- [x] Conservar el error real de expansión de playlist.

## P1 — Robustez y escalabilidad

- [x] Sustituir polling y creación manual de hilos por scheduler controlado.
- [x] Evitar iniciar dos veces el mismo item.
- [x] Limpiar workers, progreso y procesos terminados.
- [x] Resolver concurrencia del `download-archive`.
- [x] Hacer expansión de playlist transaccional.
- [x] Implementar recarga que añada y actualice vídeos existentes.
- [x] Añadir índices SQLite y migraciones versionadas.
- [ ] Validar y guardar configuración de forma atómica.
- [ ] Actualizar UI incrementalmente en lugar de reconstruir toda la cola.
- [x] Añadir logging estructurado y errores accionables.

## P2 — Experiencia de usuario

- [x] Estados visuales separados para pendiente, en cola, pausado y parcial.
- [x] Mostrar estado de expansión de playlist.
- [x] Cancelación de expansión.
- [ ] Confirmaciones para borrado y cancelación masiva.
- [ ] Diseño responsive para ventanas pequeñas.
- [x] SnackBars sin acumulación en `page.overlay`.
- [x] Progreso global por playlist.
- [ ] Tamaño estimado y tiempo restante global.
- [x] Filtro y búsqueda dentro de la cola.
- [ ] Ordenación por fecha, estado y título.
- [ ] Exportar/importar cola.

## P3 — Evolución funcional

- [ ] Selección de calidad de vídeo y audio.
- [ ] Plantillas de nombre configurables.
- [ ] Subtítulos y miniaturas configurables.
- [ ] Descarga de vídeos individuales además de playlists.
- [ ] Revisión y actualización de yt-dlp desde la UI.
- [ ] Notificaciones de escritorio al completar una playlist.
- [ ] Modo oscuro configurable.
- [ ] Soporte de múltiples perfiles de configuración.

## Calidad técnica

- [ ] Completar type hints y corregir `mypy --strict`.
- [ ] Aplicar formatter y lint de forma automática.
- [ ] Añadir tests de estados, scheduler y parser.
- [ ] Añadir tests de UI para acciones y estados.
- [ ] Añadir smoke test de PyInstaller.
- [ ] Añadir CI multiplataforma.
- [ ] Ejecutar `pip-audit`.
- [ ] Revisar documentación y comandos de ejecución.

## Criterios para cerrar una feature

- Existe una descripción breve del comportamiento.
- Está implementada sin mezclar UI, dominio e infraestructura innecesariamente.
- Tiene prueba para el camino feliz y al menos un caso de error.
- Actualiza README o documentación si cambia el uso.
- Ha sido validada en una instalación limpia cuando afecta a dependencias o
  empaquetado.
