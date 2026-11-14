#!/usr/bin/env python3
"""Anonimización local del texto OCR del nivel 3.

Corre en la computadora del equipo, antes de que cualquier texto llegue a un
modelo externo. Lee ocr/<ID>.txt y escribe anonimizado/<ID>.txt.

Estrategia (conservadora: ante la duda, enmascara):
  1. Identificadores numéricos: DNI, CUIT/CUIL, teléfonos, CBU/CVU y cualquier
     secuencia de 7 o más dígitos (aun con puntos, guiones o espacios).
  2. Correos electrónicos.
  3. Direcciones: Calle / Avenida / Pasaje / Boulevard ... + número, piso y
     unidad.
  4. Renglones de identificación de partes ("Locador:", "Locatario:",
     "Garante:", "Contacto técnico designado:", "Firma", "Aclaración", ...):
     se conserva el rol y se enmascara el resto del renglón.
  5. Nombres conocidos: nombres y apellidos que aparecen en el material de los
     niveles 1 y 2 (encabezados de contratos y carátulas de fallos).
  6. Lista blanca: toda palabra con inicial mayúscula que no figure en el
     vocabulario de las Leyes, de las cláusulas de contratos anteriores y de
     las consideraciones de los fallos se reemplaza por [NOMBRE?]. Esto
     también enmascara palabras mal reconocidas: se pierde algo de texto, pero
     no se filtra un nombre por un error de OCR.

El script sólo imprime conteos (reemplazos y control de fugas), nunca texto.

Uso:
  python3 anonimizar.py --ocr ../ocr --salida ../anonimizado \
      --leyes ../../leyes-de-platon.md --referencias ../../nivel-1 ../../nivel-2
"""
import argparse
import collections
import glob
import os
import re
import unicodedata

ROLES = (r"Locador(?:a)?|Locatari[oa]|Garante|Fiador(?:a)?|Contacto t[eé]cnico(?: designado)?|"
         r"Propietari[oa]|Apoderad[oa]|Testigo|Firma|Aclaraci[oó]n|Representante|Ocupante")
CALLES = r"Calle|Avenida|Av\.|Pasaje|Pje\.|Boulevard|Bv\.|Camino|Diagonal|Plaza"


def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def clave(w):
    return sin_acentos(w).lower()


def leer(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def cargar_referencias(leyes, carpetas):
    """Devuelve (vocabulario permitido, nombres conocidos) desde niveles anteriores."""
    vocab, nombres = set(), set()
    textos = [leer(leyes)]
    for carpeta in carpetas:
        for p in glob.glob(os.path.join(carpeta, "contratos", "*.md")):
            t = leer(p)
            for m in re.finditer(rf"^(?:{ROLES})[^:\n]*: ([^.\n]+)\.", t, re.M):
                nombres.update(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", m.group(1)))
            nombres.update(w for m in re.finditer(r"garantía personal de ([^\n]+?) constituye", t)
                           for w in m.group(1).split())
            # sólo cláusulas y anexos, sin el bloque de identificación de partes
            if "Cláusula C01" in t:
                t = t[t.index("Cláusula C01"):]
            t = re.sub(r"garantía personal de [^\n]+? constituye", "garantía personal de constituye", t)
            t = re.sub(rf"(?:{CALLES}) [^,\n]+ \d+(?:, piso \d+, unidad \d+)?", "", t)
            textos.append(t)
        for p in glob.glob(os.path.join(carpeta, "fallos", "*.md")):
            t = leer(p)
            m = re.search(r"\n\n(.+?) contra (.+?)\. Expediente", t)
            if m:
                nombres.update(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]+", m.group(1) + " " + m.group(2)))
            for sec in ("IV. Consideraciones", "V. Deliberación", "VI. Parte resolutiva"):
                i = t.find(sec)
                if i >= 0:
                    textos.append(t[i:i + 3000])
        for p in glob.glob(os.path.join(carpeta, "enunciado.md")):
            textos.append(leer(p))
    for t in textos:
        vocab.update(clave(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", t))
    comunes = {"y", "otros", "contra", "administracion", "de", "del", "la", "los", "las"}
    nombres = {clave(n) for n in nombres if len(n) > 2} - comunes
    vocab -= nombres
    return vocab, nombres


PATRONES = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("CUIT", re.compile(r"\b\d{2}\s?[-‐–]\s?\d{7,8}\s?[-‐–]\s?\d\b")),
    ("TELEFONO", re.compile(r"\+\s?\d{1,3}(?:[\s().-]*\d){8,}")),
    ("DNI", re.compile(r"\b\d{1,2}[.\s]\d{3}[.\s]\d{3}\b")),
    ("NUMERO", re.compile(r"\d(?:[\s.\-–]?\d){6,}")),
    ("DIRECCION", re.compile(
        rf"\b(?:{CALLES})\s+(?:[^\W\d_]+\s+){{0,5}}?\d{{1,5}}"
        r"(?:\s*,?\s*piso\s*\d+)?(?:\s*,?\s*(?:unidad|depto\.?|dpto\.?)\s*\w+)?", re.I)),
]


def anonimizar(texto, vocab, nombres, cont):
    for etiqueta, pat in PATRONES:
        texto, n = pat.subn(f"[{etiqueta}]", texto)
        cont[etiqueta] += n
    # renglones de identificación: se conserva el rol
    def rol(m):
        cont["RENGLON_PARTE"] += 1
        return m.group(1) + " [DATOS PERSONALES]"
    texto = re.sub(rf"^(\s*(?:{ROLES})[^:\n]{{0,30}}:)[^\n]*$", rol, texto, flags=re.M | re.I)

    def palabra(m):
        w = m.group(0)
        k = clave(w)
        if k in nombres:
            cont["NOMBRE"] += 1
            return "[NOMBRE]"
        if w[0].isupper() and len(w) > 1 and k not in vocab:
            cont["NOMBRE?"] += 1
            return "[NOMBRE?]"
        return w
    return re.sub(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", palabra, texto)


def controlar(texto, nombres):
    """Conteos de posibles fugas que deben dar cero."""
    palabras = [clave(w) for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", texto)]
    return {
        "nombres_conocidos": sum(w in nombres for w in palabras),
        "digitos_7_o_mas": len(re.findall(r"\d(?:\D?\d){6,}", texto)),
        "arrobas": texto.count("@"),
        "calles_con_numero": len(re.findall(rf"(?:{CALLES})\s+\D{{0,40}}\d", texto, re.I)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", default="../ocr")
    ap.add_argument("--salida", default="../anonimizado")
    ap.add_argument("--leyes", required=True)
    ap.add_argument("--referencias", nargs="+", required=True)
    a = ap.parse_args()
    vocab, nombres = cargar_referencias(a.leyes, a.referencias)
    print(f"vocabulario permitido: {len(vocab)} palabras; nombres conocidos: {len(nombres)}")
    os.makedirs(a.salida, exist_ok=True)
    total = collections.Counter()
    for p in sorted(glob.glob(os.path.join(a.ocr, "*.txt"))):
        cont = collections.Counter()
        salida = anonimizar(leer(p), vocab, nombres, cont)
        fugas = controlar(salida, nombres)
        with open(os.path.join(a.salida, os.path.basename(p)), "w", encoding="utf-8") as fh:
            fh.write(salida)
        total.update(cont)
        print(os.path.basename(p), dict(cont), "| control:", fugas)
    print("total", dict(total))


if __name__ == "__main__":
    main()
