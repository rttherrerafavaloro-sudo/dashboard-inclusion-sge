# Configuración de sincronización Trello → GitHub Pages

El dashboard conserva la página existente y utiliza GitHub Actions para regenerar `data/trello.json` cada seis horas.

## 1. Guardar las credenciales de Trello

1. Abrí la [página de claves de Trello](https://trello.com/app-key) con la cuenta que tiene acceso al tablero.
2. Copiá la API Key y generá un token con acceso de lectura al tablero.
3. En GitHub, abrí este repositorio y entrá en **Settings → Secrets and variables → Actions**.
4. Creá estos dos *Repository secrets*:
   - `TRELLO_KEY`: la API Key.
   - `TRELLO_TOKEN`: el token de lectura.
5. No pegues estas credenciales en archivos, mensajes, HTML ni en el tablero.

## 2. Autorizar qué contenido se publica

Creá estas etiquetas en el tablero Trello con estos nombres exactos:

- `PUBLICAR`: autoriza que se muestren el título, enlace, área, estado y fechas de esa tarjeta.
- `PUBLICAR-DETALLE`: además de PUBLICAR, autoriza mostrar la descripción.
- `PUBLICAR-IMAGENES`: además de PUBLICAR, autoriza mostrar imágenes adjuntas.

Las dos etiquetas adicionales no publican nada por sí solas: siempre deben acompañar a `PUBLICAR`.

**Antes de etiquetar una tarjeta**, revisá que su título, descripción y adjuntos no contengan nombres completos de estudiantes, datos de contacto, calificaciones, documentos, información de familias u otros datos confidenciales. No se sincronizan comentarios ni nombres de integrantes.

## 3. Ejecutar la primera sincronización

1. Abrí la pestaña **Actions** del repositorio.
2. Seleccioná **Actualizar dashboard desde Trello**.
3. Presioná **Run workflow**.
4. Cuando finalice correctamente, revisá el dashboard publicado.

Luego se actualizará automáticamente cada seis horas. También podés ejecutar el flujo manualmente cuando lo necesites.

## 4. Qué datos se muestran

- Indicadores globales y cantidades por lista.
- Tarjetas autorizadas mediante la etiqueta PUBLICAR.
- Descripciones e imágenes únicamente con sus etiquetas adicionales.
- Historial de creación, movimientos entre listas, adjuntos y checklist de tarjetas autorizadas, sin comentarios ni identidades.

El dashboard es público. La autorización de publicación debe hacerse tarjeta por tarjeta.
