# Preparación de archivos para staging (BigQuery). Correr en Google Colab, una celda por bloque.
# Cada bloque deja el CSV listo para cargar y muestra su esquema y el número de filas esperado.
# No pegar contraseñas ni tokens en el código.

# %% [markdown]
# # Preparación de archivos para staging (BigQuery)
#
# **Cómo usar este cuaderno**
#
# 1. Súbelo a Google Colab (colab.research.google.com → Archivo → Subir cuaderno).
# 2. Corre **la celda 0** (Preparación). Siempre, una sola vez por sesión.
# 3. Corre **solo la celda de la tabla que vas a cargar**. Cada una:
#    - te pide que subas el archivo (o lo descarga ella sola),
#    - muestra el **esquema**, la codificación y el **número de filas esperado**,
#    - y descarga a tu computadora el archivo listo para BigQuery.
# 4. Con ese archivo y ese esquema haces la carga en la consola de BigQuery (ver la guía del chat).
#
# Regla de staging: los datos van **sin limpiar**. Aquí solo se (a) quitan los nombres de personas del RNPDNO,
# (b) se toma una muestra de los archivos que pasan los 100 MB, y (c) se pasan a CSV los que vienen en otro formato.
# No pegues contraseñas ni tokens en ninguna celda.

# %% [markdown]
# ## 0. Preparación (siempre primero)

# %%
import csv, json, os, re, time, unicodedata, zipfile
from pathlib import Path
import pandas as pd
from google.colab import files

os.makedirs("salida", exist_ok=True)


def limpia_nombre(c):
    """Quita acentos y caracteres raros: BigQuery no acepta espacios ni acentos en nombres de columna."""
    c = unicodedata.normalize("NFKD", str(c)).encode("ascii", "ignore").decode()
    c = re.sub(r"[^0-9a-zA-Z]+", "_", c).strip("_").lower()
    return c or "col"


def esquema(columnas):
    """Texto 'col:STRING,col2:STRING' para pegar en BigQuery (Editar como texto)."""
    usados, nombres = {}, []
    for c in columnas:
        n = limpia_nombre(c)
        if n[0].isdigit():
            n = "c_" + n
        usados[n] = usados.get(n, 0) + 1
        nombres.append(n if usados[n] == 1 else f"{n}_{usados[n]}")
    return ",".join(f"{n}:STRING" for n in nombres)


def revisar_csv():
    """Sube un CSV (sin modificarlo) y te dice codificación, delimitador y esquema para BigQuery."""
    subido = files.upload()
    ruta = next(iter(subido))
    crudo = open(ruta, "rb").read()
    try:
        crudo.decode("utf-8")
        codificacion, en_bq = "utf-8-sig", "UTF-8"
    except UnicodeDecodeError:
        codificacion, en_bq = "latin-1", "ISO-8859-1"
    primera = crudo.decode(codificacion).splitlines()[0]
    try:
        delim = csv.Sniffer().sniff(primera, delimiters=",;|\t").delimiter
    except csv.Error:
        delim = ","
    columnas = next(csv.reader([primera], delimiter=delim))
    nombre_delim = {",": "coma", ";": "punto y coma", "|": "barra vertical", "\t": "tabulador"}[delim]
    print(f"Archivo: {ruta}")
    print(f"Codificación para BigQuery: {en_bq}")
    print(f"Delimitador de campo: {nombre_delim}")
    print(f"Columnas: {len(columnas)}")
    n_lineas = crudo.count(b"\n") - 1
    print(f"Líneas de datos (aproximado): {n_lineas:,}")
    print("\nESQUEMA (cópialo completo):\n")
    print(esquema(columnas))


def guardar_y_bajar(df, nombre):
    """Guarda en UTF-8, muestra el esquema y descarga el archivo."""
    ruta = f"salida/{nombre}.csv"
    df.to_csv(ruta, index=False, encoding="utf-8")
    mb = os.path.getsize(ruta) / 1e6
    print(f"Filas: {len(df):,} | Columnas: {df.shape[1]} | Tamaño: {mb:.1f} MB (el límite de la consola es ~100 MB)")
    print("\nESQUEMA (cópialo completo):\n")
    print(esquema(df.columns))
    files.download(ruta)

# %% [markdown]
# ## A. Archivos que se cargan tal cual (solo necesitas el esquema)
#
# Corre `revisar_csv()`, sube el archivo y copia lo que imprime. **No se modifica el archivo**: lo cargas a BigQuery
# desde tu computadora. Úsalo para: SESNSP delitos, SESNSP víctimas, CONAPO y ENDIREH (`TB_SEC_IV.csv`).

# %%
revisar_csv()   # elige el archivo cuando aparezca el botón

# %% [markdown]
# ## B. Kaggle Spotify Charts, solo México → `stg_kaggle_charts_mx`
#
# Descarga el archivo global (3.48 GB) dentro de Colab, se queda con las filas de México (Top 200 y Viral 50)
# y te baja un CSV de ~60 MB. Si Kaggle pide iniciar sesión, hazlo desde la ventana que aparece, no pegues tu token.
# **Filas esperadas: 448,832.**

# %%
import kagglehub

carpeta = Path(kagglehub.dataset_download("dhruvildave/spotify-charts"))
csv_charts = next(carpeta.rglob("*.csv"))
partes = []
for pedazo in pd.read_csv(csv_charts, chunksize=1_000_000, dtype=str):
    partes.append(pedazo[pedazo["region"] == "Mexico"])
kaggle_mx = pd.concat(partes, ignore_index=True)
guardar_y_bajar(kaggle_mx, "stg_kaggle_charts_mx")

# %% [markdown]
# ## C. RNPDNO sin nombres → `stg_rnpdno`
#
# Sube el CSV de la versión pública (latin-1). La celda **elimina las columnas con nombres de personas**
# antes de guardar. **Revisa la lista que imprime**: ninguna columna con nombres debe quedar.
# **Filas esperadas: 116,945.**

# %%
subido = files.upload()
ruta = next(iter(subido))
rnpdno = pd.read_csv(ruta, dtype=str, encoding="latin-1")
print("Columnas originales:", rnpdno.columns.tolist())

con_nombres = [c for c in rnpdno.columns if re.search(r"nombre|apellido", c, re.I)]
rnpdno = rnpdno.drop(columns=con_nombres)
print("\nSe eliminaron:", con_nombres)
print("Columnas que quedan:", rnpdno.columns.tolist())
assert not any(re.search(r"nombre|apellido", c, re.I) for c in rnpdno.columns)

guardar_y_bajar(rnpdno, "stg_rnpdno")

# %% [markdown]
# ## D. Censo 2020 ITER (muestra) → `stg_censo_iter`
#
# El archivo pesa 150 MB y no entra por la consola. Sube el **ZIP** (`iter_00_cpv2020_csv.zip`, 36.6 MB).
# La muestra conserva las **filas de total por entidad** (las que se usan: `POBTOT`, `POBFEM`, `VPH_INTER`,
# `TVIVPARHAB`) y 20 localidades por entidad. Deben salir **33 filas de total** (nacional + 32 entidades).

# %%
subido = files.upload()
ruta = next(iter(subido))
z = zipfile.ZipFile(ruta)
candidatos = [n for n in z.namelist() if n.lower().endswith(".csv") and "conjunto_de_datos" in n.lower()]
print("Archivos CSV dentro del ZIP:", candidatos)

def leer_zip(z, nombre):
    for cod in ("utf-8-sig", "latin-1"):
        try:
            with z.open(nombre) as f:
                return pd.read_csv(f, dtype=str, encoding=cod)
        except UnicodeDecodeError:
            continue

iter_df = leer_zip(z, candidatos[0])
assert {"ENTIDAD", "NOM_LOC"} <= set(iter_df.columns), iter_df.columns.tolist()[:15]

es_total = iter_df["NOM_LOC"].str.contains("Total de la entidad|Total nacional", case=False, na=False)
totales = iter_df[es_total]
resto = iter_df[~es_total].groupby("ENTIDAD").head(20)
print("Filas de total por entidad (esperado 33):", len(totales))

guardar_y_bajar(pd.concat([totales, resto], ignore_index=True), "stg_censo_iter")

# %% [markdown]
# ## E. ENDUTIH 2024, usuarios → `stg_endutih_usuarios`
#
# Sube el ZIP de microdatos en DBF (`endutih2024_bd_dbf.zip`, 8.8 MB). La celda lo pasa a CSV.
# Si el CSV pasa de ~90 MB, toma una muestra por entidad. **Filas esperadas: 58,080** (o menos si salió muestra).

# %%
!pip -q install dbfread
from dbfread import DBF

subido = files.upload()
ruta = next(iter(subido))
zipfile.ZipFile(ruta).extractall("endutih")
tablas = sorted(p for p in Path("endutih").rglob("*") if p.suffix.lower() == ".dbf")
print("Tablas DBF encontradas:", [p.name for p in tablas])

usuarios = [p for p in tablas if p.stem.lower() == "tic_2024_usuarios"]
assert usuarios, "Elige a mano el archivo de usuarios de la lista de arriba"

dbf = DBF(str(usuarios[0]), encoding="latin-1", load=False)
endutih = pd.DataFrame(iter(dbf)).astype("string")
print("Filas completas:", len(endutih))

endutih.to_csv("salida/_prueba_tamano.csv", index=False)
if os.path.getsize("salida/_prueba_tamano.csv") > 90e6:
    endutih = endutih.groupby("CVE_ENT").head(150)
    print("Muy grande: se toma una muestra de 150 filas por entidad")
os.remove("salida/_prueba_tamano.csv")

guardar_y_bajar(endutih, "stg_endutih_usuarios")

# %% [markdown]
# ## F. Natural Earth, solo México → `stg_naturalearth_mx`
#
# Se descarga solo. Deja los registros de México con su geometría como texto (WKT). **Filas esperadas: 33**
# (los 32 estados y un registro sin nombre).

# %%
import requests
import geopandas as gpd

url = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
r = requests.get(url, timeout=120)
r.raise_for_status()
open("ne_admin1.zip", "wb").write(r.content)

mundo = gpd.read_file("ne_admin1.zip")
mex = mundo[mundo["adm0_a3"] == "MEX"].copy()
mex["geometry_wkt"] = mex.geometry.to_wkt()
columnas = [c for c in ["name", "name_es", "iso_3166_2", "adm1_code", "adm0_a3", "geometry_wkt"] if c in mex.columns]
guardar_y_bajar(pd.DataFrame(mex[columnas]), "stg_naturalearth_mx")

# %% [markdown]
# ## G. CONEVAL → `stg_coneval_pobreza`
#
# Sube el ZIP `AE_estatal_2022.zip`. El libro tiene una hoja por entidad en formato de reporte. Aquí se juntan
# **todas las hojas tal cual** (celdas como texto) en una sola tabla, con la columna `hoja` y el número de `fila`.

# %%
subido = files.upload()
ruta = next(iter(subido))
z = zipfile.ZipFile(ruta)
libros = [n for n in z.namelist() if n.lower().endswith((".xlsx", ".xls"))]
print("Libros de Excel dentro del ZIP:", libros)
z.extract(libros[0], "coneval")

hojas = pd.read_excel(Path("coneval") / libros[0], sheet_name=None, header=None, dtype=str)
print("Hojas:", len(hojas))
partes = []
for nombre, h in hojas.items():
    h = h.copy()
    h.insert(0, "fila", range(1, len(h) + 1))
    h.insert(0, "hoja", nombre)
    partes.append(h)
coneval = pd.concat(partes, ignore_index=True)
coneval.columns = ["hoja", "fila"] + [f"c{i:02d}" for i in range(1, coneval.shape[1] - 1)]

guardar_y_bajar(coneval, "stg_coneval_pobreza")

# %% [markdown]
# ## H. MiSonGyny → `stg_misongyny`
#
# Se clona el repositorio dentro de Colab y se juntan los archivos TRAIN y TEST (con la columna `archivo_origen`).
# Revisa lo que imprime: deben verse `id, song_title, song_artist, label`.

# %%
!git clone -q https://github.com/CCogS-Mx/MiSonGyny-Misogyny-in-song-lyrics-dataset misongyny

todos = [p for p in Path("misongyny").rglob("*") if p.suffix.lower() in (".csv", ".tsv")]
elegidos = [p for p in todos if re.search(r"train|test", p.name, re.I)] or todos
print("Archivos incluidos:")
partes = []
for p in elegidos:
    df = pd.read_csv(p, dtype=str, sep=None, engine="python", encoding="utf-8-sig")
    df["archivo_origen"] = p.name
    print(" -", p.name, df.shape, df.columns.tolist()[:5])
    partes.append(df)
misongyny = pd.concat(partes, ignore_index=True)

guardar_y_bajar(misongyny, "stg_misongyny")

# %% [markdown]
# ## I. MusicBrainz, muestra de artistas → `stg_musicbrainz_tags`
#
# Consulta la API (1 por segundo) para 12 artistas y guarda **la respuesta tal como la devuelve**
# en una columna de texto. En la línea `set_useragent` pon tu correo de la facultad.

# %%
!pip -q install musicbrainzngs
import musicbrainzngs as mb

mb.set_useragent("ProyectoMisoginiaMusical", "0.1", "TU_CORREO@ciencias.unam.mx")

artistas = ["Bad Bunny", "J Balvin", "Maluma", "Christian Nodal", "Ozuna", "Rauw Alejandro",
            "Piso 21", "KAROL G", "Luis Miguel", "Sebastian Yatra", "León Larregui", "Cartel De Santa"]

filas = []
for a in artistas:
    try:
        respuesta = mb.search_artists(artist=a, limit=3)
    except Exception as e:
        respuesta = {"error": str(e)}
    filas.append({"artista_buscado": a, "respuesta_json": json.dumps(respuesta, ensure_ascii=False, default=str)})
    time.sleep(1.1)

guardar_y_bajar(pd.DataFrame(filas), "stg_musicbrainz_tags")
