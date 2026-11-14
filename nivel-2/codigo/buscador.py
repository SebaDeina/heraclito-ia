#!/usr/bin/env python3
"""Buscador de sentencias del Tribunal de Locaciones de Calípolis.

Motor: SQLite FTS5 (código abierto, incluido en la biblioteca estándar de
Python a través del módulo `sqlite3`), con ranking BM25.

Etapas:
  1. CARGA      -> cargar_fallos():   lee fallos/F-NNN.md y extrae metadatos.
  2. INDEXACIÓN -> indexar():         parte cada fallo en fragmentos y los
                                      guarda en una tabla FTS5.
  3. CONSULTA   -> consultar():       recupera fragmentos por BM25 y los
                                      agrupa por número de sentencia.

Uso:
  python buscador.py indexar   --fallos ../fallos --db indice.db
  python buscador.py consultar "batería central cuotas" --db indice.db
  python buscador.py lote      consultas.json --db indice.db --salida resultados.md
"""
import argparse
import glob
import json
import os
import re
import sqlite3
import sys

SECCIONES = [
    ("vistos", "I. Vistos"),
    ("antecedentes", "II. Antecedentes"),
    ("prueba", "III. Tramitación y prueba"),
    ("consideraciones", "IV. Consideraciones"),
    ("deliberacion", "V. Deliberación"),
    ("resolutiva", "VI. Parte resolutiva"),
    ("anexo", "Anexo de actuaciones incorporadas"),
]
# Secciones donde está la razón decisoria. Las actuaciones de prueba y el
# anexo son relatos de partes y testigos: se indexan, pero por defecto no se
# consultan (artículo 31: se distingue la razón decisoria de los relatos).
SECCIONES_DECISORIAS = ("antecedentes", "consideraciones", "resolutiva")

STOPWORDS = set(
    "a al algo ante aun aunque cada como con contra cual cuando de del desde "
    "donde el ella en entre es esa ese esta este la las lo los mas más ni no o "
    "para pero por que qué se sea ser si sin sobre su sus también tras un una "
    "uno y ya e u le les son fue ha han hay".split()
)


# ---------------------------------------------------------------- 1. CARGA
def cargar_fallos(carpeta):
    """Lee cada F-NNN.md y devuelve una lista de dicts con metadatos y secciones."""
    fallos = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "F-*.md"))):
        with open(ruta, encoding="utf-8") as fh:
            texto = fh.read()
        cab = re.search(
            r"Sentencia (F-\d{3})\. (Sala Primera|Sala Segunda|Plenario)\. "
            r"Publicación: (\d{2})/(\d{2})/(\d{4})\.",
            texto,
        )
        if not cab:
            print(f"aviso: encabezado no reconocido en {ruta}", file=sys.stderr)
            continue
        numero, organo, dd, mm, aaaa = cab.groups()
        arts = re.search(r"artículos? ([\d, y]+) de Las Leyes", texto)
        articulos = re.findall(r"\d+", arts.group(1)) if arts else []
        revoca = re.findall(r"Se revoca expresamente la doctrina de (F-\d{3})", texto)
        fallos.append(
            {
                "numero": numero,
                "organo": organo,
                "fecha": f"{aaaa}-{mm}-{dd}",
                "articulos": ",".join(articulos),
                "revoca": revoca,
                "secciones": partir_secciones(texto),
            }
        )
    return fallos


def partir_secciones(texto):
    """Devuelve [(seccion, parrafo)] respetando los títulos del fallo."""
    marcas = []
    for clave, titulo in SECCIONES:
        pos = texto.find("\n" + titulo + "\n")
        if pos >= 0:
            marcas.append((pos, clave, titulo))
    marcas.sort()
    fragmentos = []
    for i, (pos, clave, titulo) in enumerate(marcas):
        fin = marcas[i + 1][0] if i + 1 < len(marcas) else len(texto)
        cuerpo = texto[pos + len(titulo) + 2 : fin]
        for parrafo in cuerpo.split("\n\n"):
            parrafo = parrafo.strip()
            if len(parrafo) > 40 and not parrafo.startswith("Actuación "):
                fragmentos.append((clave, parrafo))
    return fragmentos


# ----------------------------------------------------------- 2. INDEXACIÓN
def indexar(carpeta, db):
    """Crea el índice FTS5: un registro por fragmento (párrafo) de cada fallo."""
    fallos = cargar_fallos(carpeta)
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE fallos (numero TEXT PRIMARY KEY, organo TEXT, fecha TEXT, "
        "articulos TEXT, revoca TEXT, revocado_por TEXT)"
    )
    con.execute(
        "CREATE VIRTUAL TABLE fragmentos USING fts5("
        "texto, numero UNINDEXED, seccion UNINDEXED, "
        "tokenize='unicode61 remove_diacritics 2')"
    )
    revocado_por = {}
    for f in fallos:
        for r in f["revoca"]:
            revocado_por.setdefault(r, []).append(f["numero"])
    n_frag = 0
    for f in fallos:
        con.execute(
            "INSERT INTO fallos VALUES (?,?,?,?,?,?)",
            (
                f["numero"],
                f["organo"],
                f["fecha"],
                f["articulos"],
                ",".join(f["revoca"]),
                ",".join(revocado_por.get(f["numero"], [])),
            ),
        )
        for seccion, parrafo in f["secciones"]:
            con.execute(
                "INSERT INTO fragmentos (texto, numero, seccion) VALUES (?,?,?)",
                (parrafo, f["numero"], seccion),
            )
            n_frag += 1
    con.commit()
    con.close()
    print(f"indexados {len(fallos)} fallos y {n_frag} fragmentos en {db}")


# -------------------------------------------------------------- 3. CONSULTA
def armar_consulta_fts(pregunta):
    """Convierte texto libre en una consulta FTS5: términos unidos por OR."""
    terminos = [
        t for t in re.findall(r"\w+", pregunta.lower()) if t not in STOPWORDS and len(t) > 1
    ]
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(terminos))


def consultar(db, pregunta, k=8, todas_las_secciones=False, articulo=None):
    """Devuelve hasta k fallos ordenados por su mejor fragmento (BM25).

    Cada resultado trae número de sentencia, órgano, fecha, estado de vigencia
    (si un plenario posterior revocó su doctrina) y el fragmento recuperado.
    """
    con = sqlite3.connect(db)
    sql = (
        "SELECT g.numero, g.seccion, g.texto, bm25(fragmentos) AS puntaje, "
        "f.organo, f.fecha, f.articulos, f.revoca, f.revocado_por "
        "FROM fragmentos g JOIN fallos f ON f.numero = g.numero "
        "WHERE fragmentos MATCH ?"
    )
    params = [armar_consulta_fts(pregunta)]
    if not todas_las_secciones:
        sql += " AND g.seccion IN (%s)" % ",".join("?" * len(SECCIONES_DECISORIAS))
        params += list(SECCIONES_DECISORIAS)
    if articulo:
        sql += " AND (',' || f.articulos || ',') LIKE ?"
        params.append(f"%,{articulo},%")
    sql += " ORDER BY puntaje LIMIT 400"  # bm25() de FTS5: menor es mejor
    vistos, resultados = set(), []
    for fila in con.execute(sql, params):
        numero = fila[0]
        if numero in vistos:
            continue
        vistos.add(numero)
        resultados.append(
            {
                "numero": numero,
                "seccion": fila[1],
                "fragmento": fila[2],
                "puntaje": round(-fila[3], 3),
                "organo": fila[4],
                "fecha": fila[5],
                "articulos": fila[6],
                "revoca": fila[7],
                "revocado_por": fila[8],
            }
        )
        if len(resultados) >= k:
            break
    con.close()
    return resultados


def formatear(resultados):
    lineas = []
    for r in resultados:
        estado = "vigente"
        if r["revocado_por"]:
            estado = f"REVOCADO por {r['revocado_por']}"
        extra = f" | revoca {r['revoca']}" if r["revoca"] else ""
        lineas.append(
            f"- {r['numero']} | {r['organo']} | {r['fecha']} | arts. {r['articulos']} | "
            f"{estado}{extra} | bm25 {r['puntaje']} | {r['seccion']}"
        )
        lineas.append(f"  > {r['fragmento'][:420]}")
    return "\n".join(lineas) if lineas else "(sin resultados)"


def lote(db, archivo, salida, k):
    """Ejecuta las consultas de consultas.json y escribe un informe Markdown."""
    with open(archivo, encoding="utf-8") as fh:
        consultas = json.load(fh)
    partes = ["# Resultados de las consultas del nivel 2\n"]
    for c in consultas:
        res = consultar(db, c["consulta"], k=k, articulo=c.get("articulo"))
        partes.append(f"## {c['id']} — {c['tema']}\n")
        partes.append(f"Consulta: `{c['consulta']}`"
                      + (f" (filtro artículo {c['articulo']})" if c.get("articulo") else "") + "\n")
        partes.append(formatear(res) + "\n")
    with open(salida, "w", encoding="utf-8") as fh:
        fh.write("\n".join(partes))
    print(f"{len(consultas)} consultas escritas en {salida}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("indexar", help="carga los fallos y crea el índice FTS5")
    pi.add_argument("--fallos", default="../fallos")
    pi.add_argument("--db", default="indice.db")
    pc = sub.add_parser("consultar", help="consulta de texto libre")
    pc.add_argument("pregunta")
    pc.add_argument("--db", default="indice.db")
    pc.add_argument("-k", type=int, default=8)
    pc.add_argument("--articulo", help="limita a fallos que debaten ese artículo")
    pc.add_argument("--todas", action="store_true", help="incluye actuaciones de prueba y anexo")
    pl = sub.add_parser("lote", help="ejecuta un archivo de consultas")
    pl.add_argument("archivo")
    pl.add_argument("--db", default="indice.db")
    pl.add_argument("--salida", default="resultados.md")
    pl.add_argument("-k", type=int, default=8)
    a = p.parse_args()
    if a.cmd == "indexar":
        indexar(a.fallos, a.db)
    elif a.cmd == "consultar":
        print(formatear(consultar(a.db, a.pregunta, a.k, a.todas, a.articulo)))
    else:
        lote(a.db, a.archivo, a.salida, a.k)


if __name__ == "__main__":
    main()
