#!/usr/bin/env python3
"""OCR local de los contratos del nivel 3.

Todo corre en la computadora del equipo. Ningún PDF, imagen ni texto crudo
sale de la máquina, y el script sólo imprime estadísticas (ángulo, palabras,
confianza), nunca el texto reconocido.

Los PDF son fotografías de hojas inclinadas sobre fondo oscuro. Por página:
  1. extrae la imagen original con pdfimages (Poppler), sin re-muestrear;
  2. recorta la hoja (región clara) y estima la inclinación por perfil de
     proyección entre -20 y +20 grados;
  3. endereza y prueba tres variantes con Tesseract 5 (modelo `spa`,
     tessdata_best): umbral adaptativo con segmentación automática (psm 3),
     escala de grises con psm 3 y escala de grises con bloque único (psm 6);
  4. conserva el texto crudo de la variante con más palabras de confianza
     >= 70. No se corrige ni reconstruye nada.

Salida: ocr/<ID>.txt en UTF-8, páginas en orden, separadas por el salto de
página (\\f) que emite Tesseract.

Requisitos: poppler (pdfimages), tesseract + spa.traineddata, Pillow, numpy.
Uso:
  python3 ocr_local.py --pdfs /ruta/a/contratos --salida ../ocr
"""
import argparse
import csv
import glob
import io
import os
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def tesseract(img, psm):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    out = subprocess.run(
        ["tesseract", "stdin", "stdout", "-l", "spa", "--psm", psm, "txt", "tsv"],
        input=buf.getvalue(), capture_output=True, check=True,
    ).stdout.decode("utf-8")
    # con dos configs, Tesseract escribe primero el TSV y luego el texto
    i = out.find("level\tpage_num")
    filas = list(csv.DictReader(io.StringIO(out[i:]), delimiter="\t"))
    confs = [float(r["conf"]) for r in filas
             if (r.get("text") or "").strip() and float(r["conf"]) >= 0]
    texto = subprocess.run(
        ["tesseract", "stdin", "stdout", "-l", "spa", "--psm", psm],
        input=buf.getvalue(), capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return texto, confs


def umbral_adaptativo(g, radio=30, c=12):
    a = np.asarray(g).astype(float)
    m = np.asarray(g.filter(ImageFilter.BoxBlur(radio))).astype(float)
    return Image.fromarray(np.where(a < m - c, 0, 255).astype("uint8"))


def recortar_hoja(g, pad=10):
    a = np.asarray(g.filter(ImageFilter.BoxBlur(15))).astype(float) > 150
    filas = np.where(a.mean(1) > 0.3)[0]
    cols = np.where(a.mean(0) > 0.3)[0]
    if not len(filas) or not len(cols):
        return g
    return g.crop((max(0, cols.min() - pad), max(0, filas.min() - pad),
                   min(g.width, cols.max() + pad), min(g.height, filas.max() + pad)))


def inclinacion(binaria):
    chica = binaria.resize((binaria.width // 3, binaria.height // 3))
    tinta = Image.fromarray(((np.asarray(chica) < 128) * 255).astype("uint8"))

    def puntaje(ang):
        s = np.asarray(tinta.rotate(ang, fillcolor=0)).sum(1).astype(float)
        return ((s[1:] - s[:-1]) ** 2).sum()
    ordenados = sorted(np.arange(-20, 20.01, 1.0), key=puntaje, reverse=True)
    picos = []
    for ang in ordenados:  # hasta tres ángulos candidatos separados entre sí
        if all(abs(ang - p) > 3 for p in picos):
            picos.append(ang)
        if len(picos) == 3:
            break
    return [float(max(np.arange(p - 1, p + 1.01, 0.1), key=puntaje)) for p in picos]


def procesar_pagina(png):
    g = Image.open(png).convert("L")
    hoja = recortar_hoja(g)
    mejor = None
    # Si la confianza no alcanza, la página puede estar girada un cuarto de
    # vuelta (pdfimages no aplica la rotación de página del PDF).
    for base in (0, 270, 90, 180):
        girada = hoja.rotate(base, expand=True, fillcolor=255) if base else hoja
        for ang in inclinacion(umbral_adaptativo(girada)):
            r = ocr_enderezada(girada, ang) + (base,)
            if mejor is None or r[0] > mejor[0]:
                mejor = r
            if r[4] >= 85:  # confianza media suficiente: no hace falta seguir
                break
        if mejor[4] >= 85:
            break
    buenas, nombre, texto, n, media, ang, base = mejor
    return texto, f"giro {base}° {ang:+.1f}° {nombre} {n} pal ({buenas} >=70, media {media:.0f})"


def ocr_enderezada(hoja, ang):
    derecha = hoja.rotate(ang, resample=Image.BICUBIC, expand=True, fillcolor=255)
    variantes = {
        "adaptativo psm3": (umbral_adaptativo(derecha), "3"),
        "gris psm3": (ImageOps.autocontrast(derecha, 2), "3"),
        "gris psm6": (ImageOps.autocontrast(derecha, 2), "6"),
    }
    mejor = None
    for nombre, (img, psm) in variantes.items():
        texto, confs = tesseract(img, psm)
        buenas = sum(c >= 70 for c in confs)
        if mejor is None or buenas > mejor[0]:
            media = sum(confs) / len(confs) if confs else 0.0
            mejor = (buenas, nombre, texto, len(confs), media, ang)
    return mejor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdfs", required=True)
    ap.add_argument("--salida", default="../ocr")
    ap.add_argument("--solo", nargs="*", help="procesa sólo estos identificadores")
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        trabajos = []
        for pdf in sorted(glob.glob(os.path.join(a.pdfs, "*.pdf"))):
            ident = os.path.splitext(os.path.basename(pdf))[0]
            if a.solo and ident not in a.solo:
                continue
            subprocess.run(["pdfimages", "-png", pdf, os.path.join(tmp, ident)], check=True)
            trabajos.append((ident, sorted(glob.glob(os.path.join(tmp, ident + "-*.png")))))
        with ProcessPoolExecutor() as ex:
            for ident, paginas in trabajos:
                resultados = list(ex.map(procesar_pagina, paginas))
                with open(os.path.join(a.salida, ident + ".txt"), "w", encoding="utf-8") as fh:
                    fh.write("".join(t for t, _ in resultados))
                print(ident, " | ".join(f"p{i+1}: {s}" for i, (_, s) in enumerate(resultados)), flush=True)


if __name__ == "__main__":
    main()
