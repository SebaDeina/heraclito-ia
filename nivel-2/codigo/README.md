# Buscador de fallos — nivel 2

Buscador de texto completo sobre las 120 sentencias del Tribunal de Locaciones
de Calípolis. Usa **SQLite FTS5** (código abierto) con ranking **BM25**, a
través del módulo `sqlite3` de la biblioteca estándar de Python.

## Archivos

| Archivo | Qué es |
|---|---|
| `buscador.py` | Carga, indexación y consulta. |
| `consultas.json` | Las 19 consultas que usamos, una por tipo de cláusula revisada. |
| `resultados.md` | Salida de esas consultas (sentencias y fragmentos recuperados). |

El índice (`indice.db`) no se sube: se regenera con el comando de indexación.

## Entradas

- `../fallos/F-001.md` … `F-120.md`: sentencias en Markdown, tal como se
  entregaron en el expediente.
- `consultas.json`: lista de objetos `{id, tema, consulta, articulo?}`.

## Instalación

Python 3.9 o superior. No hay dependencias externas: FTS5 viene compilado en
el SQLite que trae Python. Para comprobarlo:

```bash
python3 -c "import sqlite3; sqlite3.connect(':memory:').execute('create virtual table t using fts5(x)')"
```

## Uso

Desde `nivel-2/codigo/`:

```bash
# 1. Carga + indexación (crea indice.db)
python3 buscador.py indexar --fallos ../fallos --db indice.db

# 2. Consulta de texto libre
python3 buscador.py consultar "batería central cuotas adquisición" --db indice.db -k 8

# Limitar a fallos que debaten un artículo
python3 buscador.py consultar "alerta aislada sensor ingreso" --articulo 18

# 3. Reproducir todas las consultas del nivel
python3 buscador.py lote consultas.json --db indice.db --salida resultados.md
```

Cada resultado muestra número de sentencia, órgano (Sala o Plenario), fecha de
publicación, artículos debatidos, estado de vigencia, puntaje BM25, sección y
el fragmento recuperado:

```
- F-037 | Plenario | 2026-04-25 | arts. 15,16 | vigente | revoca F-014 | bm25 77.438 | consideraciones
  > El Tribunal distingue el hecho probado ... La adquisición de batería central fija es bien común permanente ...
- F-014 | Sala Segunda | 2026-03-21 | arts. 15,16 | REVOCADO por F-037 | bm25 56.77 | consideraciones
```

## Cómo funciona

1. **Carga** (`cargar_fallos`): lee cada `F-NNN.md` y extrae del encabezado el
   número, el órgano y la fecha; de los Vistos, los artículos debatidos; y de
   la parte resolutiva, la frase "Se revoca expresamente la doctrina de F-NNN".
2. **Indexación** (`indexar`): divide cada fallo en fragmentos (un párrafo por
   registro) etiquetados con su sección, y los guarda en una tabla virtual
   FTS5 con el tokenizador `unicode61 remove_diacritics 2`, que ignora
   mayúsculas y acentos. Una tabla auxiliar `fallos` guarda los metadatos y
   las relaciones `revoca` / `revocado_por`.
3. **Consulta** (`consultar`): convierte la pregunta en términos unidos por
   `OR` (sin palabras vacías), ordena los fragmentos con `bm25()` y devuelve
   el mejor fragmento de cada sentencia.

Dos decisiones de diseño que responden a las Leyes de Calípolis:

- Por defecto sólo se consultan Antecedentes, Consideraciones y Parte
  resolutiva. Las actuaciones de prueba y el anexo son relatos de partes y
  testigos, que el artículo 31 distingue de la razón decisoria; se indexan
  igual y se incluyen con `--todas`.
- Cada resultado indica si un plenario posterior revocó la doctrina del fallo,
  porque el artículo 32 impide citarlo como autoridad vigente.

## Cómo usamos los resultados

Para cada tipo de cláusula corrimos una consulta y leímos los fragmentos
recuperados. Citamos un fallo sólo cuando su razón decisoria resuelve los
mismos hechos que la cláusula y está vigente. En la práctica eso dejó seis
plenarios (F-037, F-058, F-076, F-097, F-104 y F-106). No citamos las
sentencias revocadas (F-009, F-014, F-022, F-031, F-043, F-052) ni las de Sala
cuyos hechos no coinciden con la cláusula. Cuando la incompatibilidad surge
directamente de un tope, plazo o prohibición del texto legal, la lista de
fallos queda vacía.
