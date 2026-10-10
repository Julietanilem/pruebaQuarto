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
# (b) se convierten formatos cuando se requiere. No se hace muestreo automático por tamaño.
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
# ## D. Censo 2020 ITER completo → `stg_censo_iter`
#
# Conserva las 195,662 filas y 286 columnas del CSV original de INEGI, sin filtrar ni muestrear.
# El CSV de 142.73 MiB se sube directamente desde Colab a Cloud Storage; no se descarga por consola.
# Requiere un bucket privado con ubicación compatible con `misoginia_staging`.
# Se carga a tabla temporal, se comprueba y solamente después se reemplaza la tabla definitiva.

# %%
from google.colab import auth
from google.cloud import storage, bigquery

subido = files.upload()
ruta_zip = next(iter(subido))
with zipfile.ZipFile(ruta_zip) as archivo:
    candidatos = [n for n in archivo.namelist()
                  if n.lower().endswith('.csv') and 'conjunto_de_datos' in n.lower()]
    assert len(candidatos) == 1, f'Archivos encontrados: {candidatos}'
    archivo.extract(candidatos[0], 'iter_completo')
ruta_csv_iter = Path('iter_completo') / candidatos[0]
with ruta_csv_iter.open('r', encoding='utf-8-sig', newline='') as f:
    lector = csv.reader(f)
    columnas_iter = next(lector)
    filas_iter = sum(1 for _ in lector)
assert len(columnas_iter) == 286, len(columnas_iter)
print('Archivo ITER original:', ruta_csv_iter)
print(f'Filas: {filas_iter:,}; columnas: {len(columnas_iter)}; MiB: {ruta_csv_iter.stat().st_size/1024**2:.2f}')
assert filas_iter == 195662, 'El número de filas difiere de la versión documentada: verificar fuente.'

# %% [markdown]
# Antes de correr: crear un bucket privado en Cloud Storage en ubicación compatible con BigQuery.
# Sustituir el nombre del bucket solo si el proyecto usa otro.

# %%
auth.authenticate_user()
PROJECT_ID = 'proyecto-511216'
BUCKET_ITER = 'proyecto-511216-datos-iter2020'
OBJETO_ITER = 'iter2020/conjunto_de_datos_iter_00CSV20.csv'
cliente_storage = storage.Client(project=PROJECT_ID)
blob = cliente_storage.bucket(BUCKET_ITER).blob(OBJETO_ITER)
blob.upload_from_filename(str(ruta_csv_iter), content_type='text/csv', timeout=600)
uri_iter = f'gs://{BUCKET_ITER}/{OBJETO_ITER}'
print('Archivo subido:', uri_iter)

# %% [markdown]
# La tabla temporal se carga usando el esquema STRING ya existente de 286 columnas.
# Ninguna tabla definitiva se modifica durante esta primera validación.

# %%
cliente_bq = bigquery.Client(project=PROJECT_ID)
tabla_final_iter = f'{PROJECT_ID}.misoginia_staging.stg_censo_iter'
tabla_temp_iter = f'{PROJECT_ID}.misoginia_staging.stg_censo_iter_completo'
esquema_iter_bq = cliente_bq.get_table(tabla_final_iter).schema
config_iter = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.CSV,
    skip_leading_rows=1,
    schema=esquema_iter_bq,
    encoding='UTF-8',
    allow_quoted_newlines=True,
    max_bad_records=0,
    source_column_match='POSITION',
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
)
cliente_bq.load_table_from_uri(uri_iter, tabla_temp_iter, job_config=config_iter).result()
tabla_iter = cliente_bq.get_table(tabla_temp_iter)
print(f'Original: {filas_iter:,} filas / {len(columnas_iter)} columnas')
print(f'Temporal: {tabla_iter.num_rows:,} filas / {len(tabla_iter.schema)} columnas')
assert tabla_iter.num_rows == filas_iter and len(tabla_iter.schema) == len(columnas_iter)
print('Verificación de dimensiones correcta. Ya se puede reemplazar la tabla definitiva.')

# %% [markdown]
# Ejecutar en BigQuery SOLO después de validar:
# CREATE OR REPLACE TABLE `proyecto-511216.misoginia_staging.stg_censo_iter`
# AS SELECT * FROM `proyecto-511216.misoginia_staging.stg_censo_iter_completo`;
# Comprobar 195662 filas en la definitiva, y entonces eliminar la temporal y el objeto del bucket.

# %% [markdown]
# ## E. ENDUTIH 2024, usuarios completos → `stg_endutih_usuarios`
#
# Convierte todos los registros del DBF original `tic_2024_usuarios.dbf` a CSV UTF-8.
# Validación realizada: DBF original = 58,080 filas y 232 columnas;
# CSV preparado = 58,080 filas y 232 columnas; BigQuery = 58,080 filas y 232 columnas.
# No se muestrea por tamaño. La comparación de dimensiones no comprueba cada valor.

# %%
!pip -q install dbfread
from dbfread import DBF

subido = files.upload()
ruta = next(iter(subido))
with zipfile.ZipFile(ruta) as archivo:
    archivo.extractall('endutih')
tablas = sorted(p for p in Path('endutih').rglob('*') if p.suffix.lower() == '.dbf')
usuarios = [p for p in tablas if p.stem.lower() == 'tic_2024_usuarios']
assert len(usuarios) == 1, f'Archivo DBF de usuarios ambiguo: {usuarios}'
dbf = DBF(str(usuarios[0]), encoding='latin-1', load=False)
filas_dbf = len(dbf)
columnas_dbf = len(dbf.field_names)
endutih = pd.DataFrame(iter(dbf)).astype('string')
# BigQuery no admite campos que comiencen con guion bajo en el esquema preparado.
endutih.columns = [str(c).lower().lstrip('_') for c in endutih.columns]
assert len(endutih) == filas_dbf and len(endutih.columns) == columnas_dbf
assert len(set(endutih.columns)) == columnas_dbf, 'Nombres de columna duplicados'
ruta_endutih = 'salida/stg_endutih_usuarios.csv'
endutih.to_csv(ruta_endutih, index=False, encoding='utf-8', quoting=csv.QUOTE_ALL)
with open(ruta_endutih, newline='', encoding='utf-8') as f:
    filas_csv = sum(1 for _ in csv.reader(f)) - 1
assert filas_csv == filas_dbf, 'Error en el CSV generado'
print(f'DBF original: {filas_dbf:,} filas / {columnas_dbf} columnas')
print(f'CSV completo: {filas_csv:,} filas / {len(endutih.columns)} columnas')
print('Esquema BigQuery:')
print(','.join(f'{c}:STRING' for c in endutih.columns))
files.download(ruta_endutih)

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
# ## I. MusicBrainz — búsquedas de todo el catálogo Kworb → `stg_musicbrainz_tags`
#
# La selección de artistas se obtiene de `stg_kworb_catalogo_canciones` en BigQuery.
# Se conserva el JSON de resultados de búsqueda, incluidos mensajes de error; no se decide
# automáticamente que el primer resultado corresponde a la identidad del artista.
# Las etiquetas completas se consultarán únicamente después de resolver identidades en Silver.
# Respetar el límite de una solicitud por segundo e identificar la aplicación.

# %%
!pip -q install musicbrainzngs google-cloud-bigquery
from google.colab import auth
from google.cloud import bigquery
import musicbrainzngs as mb
import csv, json, time

auth.authenticate_user()
cliente_bq = bigquery.Client(project='proyecto-511216')
consulta_artistas = """
SELECT DISTINCT TRIM(artista) AS artista
FROM `proyecto-511216.misoginia_staging.stg_kworb_catalogo_canciones`
WHERE artista IS NOT NULL AND TRIM(artista) != ''
  AND LENGTH(TRIM(track_id)) = 22
ORDER BY artista
"""
artistas = [r.artista for r in cliente_bq.query(consulta_artistas).result()]
assert artistas, 'El catálogo Kworb no devolvió artistas'
print('Nombres de artista para consultar:', len(artistas))
mb.set_useragent('misoginia-dw-unam', '1.0', 'TU_CORREO@ciencias.unam.mx')
resultados = []
for i, a in enumerate(artistas, start=1):
    try:
        respuesta = mb.search_artists(artist=a, limit=5)
    except Exception as exc:
        respuesta = {'error': str(exc)}
    resultados.append({
        'artista_buscado': a,
        'respuesta_json': json.dumps(respuesta, ensure_ascii=False, default=str),
    })
    print(f'{i}/{len(artistas)}: {a}')
    time.sleep(1.2)

ruta_mb = 'salida/stg_musicbrainz_tags.csv'
pd.DataFrame(resultados).to_csv(ruta_mb, index=False, encoding='utf-8', quoting=csv.QUOTE_ALL)
assert len(resultados) == len(artistas)
print('Filas generadas:', len(resultados))
print('Búsquedas con error:', sum('"error"' in r['respuesta_json'] for r in resultados))
print('Esquema: artista_buscado:STRING,respuesta_json:STRING')
files.download(ruta_mb)

# %% [markdown]
# ## J. México Evalúa — 12 índices del reporte Hallazgos 2023
#
# Se cargan todas las barras publicadas de las doce gráficas por delito, incluyendo
# los valores nacionales; las entidades excluidas por la fuente no se completan.
# El extractor utiliza las coordenadas de texto del PDF, verifica el alineamiento
# y registra página, abreviatura original, unidad y referencia bibliográfica.
# No se realiza reconocimiento óptico de caracteres ni se estiman valores.

# %%
!pip -q install pymupdf pandas
import importlib.util
subido = files.upload()  # seleccionar HALLAZGOS2023.pdf
pdf_hallazgos = next((n for n in subido if n.lower().endswith('.pdf')), None)
assert pdf_hallazgos, 'Debes subir Hallazgos 2023 en formato PDF'
# Subir también extraer_hallazgos_2023_completo.py si no está en la sesión.
if not Path('extraer_hallazgos_2023_completo.py').exists():
    print('Sube ahora extraer_hallazgos_2023_completo.py del repositorio')
    files.upload()
spec = importlib.util.spec_from_file_location('hallazgos', 'extraer_hallazgos_2023_completo.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
valores = mod.extraer(pdf_hallazgos)
assert len(valores) == 314 and valores.delito.nunique() == 12
ruta_evalua = 'salida/stg_mexico_evalua_12_indices.csv'
valores.to_csv(ruta_evalua, index=False, encoding='utf-8')
print(valores.groupby('delito').size().to_string())
print('Filas:', len(valores), 'Índices:', valores.delito.nunique())
print('Esquema:', ','.join(f'{c}:STRING' for c in valores.columns))
files.download(ruta_evalua)
