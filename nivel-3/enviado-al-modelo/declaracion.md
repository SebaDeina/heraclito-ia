# Declaración de envíos a modelos externos — nivel 3

En este nivel se usó un modelo externo (Claude, de Anthropic, mediante Claude
Code) como asistente. El OCR y la anonimización se ejecutaron en la
computadora del equipo con los scripts de `../codigo/`.

## Qué recibió el modelo

1. **Texto anonimizado completo** de los diez contratos: los archivos
   `anonimizado-C-3NN.txt` de esta carpeta son exactamente los que generó
   `codigo/anonimizar.py` y que el modelo leyó. Para C-306 a C-310 se le
   mostró ese mismo texto sin los párrafos repetidos del acta de entrega y
   sin los renglones `Bien NN` del inventario.
2. **Salidas de herramientas sin contenido de los documentos**: nombres de
   archivo, cantidad de páginas, tamaño y resolución de las imágenes,
   estadísticas de brillo, ángulo de inclinación estimado, cantidad de
   palabras y confianza media de Tesseract por página, conteos de reemplazos
   del anonimizador y el control de fugas, incluida la forma de las
   secuencias numéricas restantes con los dígitos reemplazados por `d`
   (todas resultaron fechas `dd/dd/dddd`).
3. **Instrucciones del equipo**: el enunciado del nivel y mensajes breves de
   coordinación ("esta es la entrega 3", "apura", "probá subirlo así", "hay
   que llegar a un 70%").
4. **Contexto previo de la conversación**: las Leyes de Calípolis y el
   material y las entregas de los niveles 1 y 2, ya publicados en este
   repositorio.
5. **Código propio**: `codigo/ocr_local.py` y `codigo/anonimizar.py`, escritos
   con el modelo.

## Qué no recibió el modelo

- Los PDF ni ninguna imagen de los contratos.
- El texto crudo del OCR (`../ocr/`): se generó y quedó en la computadora; el
  modelo sólo vio conteos y estadísticas mientras se ajustaba el proceso.

## Salida del modelo

`hallazgos-generado-por-el-modelo.json` es la respuesta generada, idéntica a
`../hallazgos.json`.
