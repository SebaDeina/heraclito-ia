# OCR y anonimización locales — nivel 3

Todo se ejecuta en la computadora del equipo; ningún PDF, imagen ni texto
crudo se envía a servicios externos.

## Requisitos

- Poppler (`pdfimages`) y Tesseract 5: `brew install poppler tesseract`
- Modelo de español `spa.traineddata` (tessdata_best) en la carpeta tessdata
- Python 3 con Pillow y numpy

## 1. OCR (`ocr_local.py`)

```bash
python3 ocr_local.py --pdfs /ruta/a/contratos --salida ../ocr
```

Los PDF son fotos de hojas inclinadas sobre fondo oscuro. Por página: extrae
la imagen, recorta la hoja, estima la inclinación (±20°, hasta tres ángulos
candidatos y giros de 90°/180°/270° si la confianza no alcanza), endereza y
prueba tres variantes de Tesseract. Conserva el texto crudo de la que tiene
más palabras de confianza ≥ 70, sin correcciones. Imprime sólo estadísticas.

## 2. Anonimización (`anonimizar.py`)

```bash
python3 anonimizar.py --ocr ../ocr --salida ../anonimizado \
  --leyes ../../leyes-de-platon.md --referencias ../../nivel-1 ../../nivel-2
```

Enmascara documentos, CUIT, teléfonos, CBU, direcciones, correos, renglones
de identificación de partes y nombres conocidos. Además reemplaza cualquier
palabra con mayúscula inicial que no esté en el vocabulario de las Leyes y
los niveles anteriores. Imprime sólo conteos y un control de fugas.
