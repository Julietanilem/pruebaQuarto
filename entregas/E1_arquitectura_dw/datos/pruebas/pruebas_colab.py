# Pruebas para las capturas 2.1, 2.2 y 2.3. Correr en Colab, una celda por bloque.
# Al terminar cada bloque, captura su salida con el nombre indicado.

# %% 0. Preparación (una sola vez)
!pip -q install musicbrainzngs beautifulsoup4

import re, time
from io import StringIO
from pathlib import Path
import pandas as pd
import requests
import kagglehub
from bs4 import BeautifulSoup

# Kaggle Spotify Charts: Top 200 de México, 2017-2021
csv = next(Path(kagglehub.dataset_download("dhruvildave/spotify-charts")).rglob("*.csv"))
partes = []
for ch in pd.read_csv(csv, chunksize=1_000_000,
                      usecols=["title", "artist", "date", "region", "chart", "url", "streams"]):
    partes.append(ch[(ch["region"] == "Mexico") & (ch["chart"] == "top200")])
mx = pd.concat(partes, ignore_index=True)
mx["date"] = pd.to_datetime(mx["date"])
mx["artista_principal"] = mx["artist"].str.split(",").str[0].str.strip()
mx["track_id"] = mx["url"].str.extract(r"track/([A-Za-z0-9]{22})")
print("Filas de México, Top 200:", len(mx))

# %% 2.2 Cobertura de artistas por año  ->  captura: prueba_cobertura_artistas.png
print("Parte de los streams del Top 200 que explican los artistas principales de cada año\n")
for anio, g in mx.groupby(mx["date"].dt.year):
    s = g.groupby("artista_principal")["streams"].sum().sort_values(ascending=False)
    print(f"{anio}   Top 50: {s.head(50).sum()/s.sum():.1%}   Top 100: {s.head(100).sum()/s.sum():.1%}")

# %% 2.3 MusicBrainz, 50 artistas con más streams  ->  captura: prueba_musicbrainz.png
import musicbrainzngs as mb
mb.set_useragent("ProyectoUNAM-AlmacenesMineria", "0.1", "proyecto-academico")

top50 = mx.groupby("artista_principal")["streams"].sum().sort_values(ascending=False).head(50).index
etiquetas = {}
for art in top50:
    r = mb.search_artists(artist=art, limit=1).get("artist-list", [])
    tags = sorted(r[0].get("tag-list", []), key=lambda t: -int(t.get("count", 0))) if r else []
    etiquetas[art] = [t["name"] for t in tags[:8]]
    time.sleep(1.1)                      # MusicBrainz pide una consulta por segundo

con = [a for a, t in etiquetas.items() if t]
print(f"Con etiquetas: {len(con)} de {len(top50)}")
print("Sin etiquetas:", [a for a, t in etiquetas.items() if not t])
for a in list(top50)[:10]:
    print(a, etiquetas[a])
print("\nSebastian Yatra:", etiquetas.get("Sebastian Yatra"))

# %% 2.1 Kworb semanal  ->  capturas: prueba_kworb_colab_1.png y prueba_kworb_colab_2.png
H = {"User-Agent": "Proyecto academico UNAM - Almacenes y Mineria de Datos"}
BASE = "https://kworb.net/spotify/"
CACHE = Path("kworb_cache"); CACHE.mkdir(exist_ok=True)

def get(url):
    f = CACHE / (re.sub(r"[^A-Za-z0-9]", "_", url) + ".html")
    if f.exists():
        return f.read_text(encoding="utf-8")
    r = requests.get(url, headers=H, timeout=30); r.raise_for_status()
    f.write_text(r.text, encoding="utf-8"); time.sleep(1.5)
    return r.text

soup = BeautifulSoup(get(BASE + "country/mx_weekly_totals.html"), "html.parser")
canciones = list(dict.fromkeys(
    (m.group(1), a.get_text(strip=True))
    for a in soup.select('a[href*="track/"]')
    if (m := re.search(r"track/([A-Za-z0-9]{22})", a["href"]))))

def historial_mx(tid):
    t = next(x for x in pd.read_html(StringIO(get(f"{BASE}track/{tid}.html"))) if "MX" in x.columns)
    mxk = t[[t.columns[0], "MX"]].copy(); mxk.columns = ["semana", "valor"]
    v = mxk["valor"].astype(str).str.extract(r"^(\d+)\s*(?:\(([\d,]+)\))?")
    mxk["posicion"] = pd.to_numeric(v[0], errors="coerce")
    mxk["streams"] = pd.to_numeric(v[1].str.replace(",", ""), errors="coerce")
    mxk["semana"] = pd.to_datetime(mxk["semana"], format="%Y/%m/%d", errors="coerce")
    mxk["track_id"] = tid
    return mxk.dropna(subset=["semana", "posicion"])

sem = pd.concat([historial_mx(tid) for tid, _ in canciones[:300]], ignore_index=True)

print("Canciones en la lista semanal de México:", len(canciones))
print("Primera semana con streams:", sem.dropna(subset=["streams"])["semana"].min().date())
cob = sem[sem["posicion"] <= 50].groupby("semana")["posicion"].nunique()
print("\nPosiciones 1-50 recuperadas por semana (300 canciones), por año:")
print(cob.groupby(cob.index.year).agg(["min", "median", "max"]))
hueco = cob[(cob.index >= "2022-01-01") & (cob.index < "2023-10-01")]
print("\nSemanas de enero 2022 a septiembre 2023 con datos:", len(hueco), "de 91")

# %% 2.1 (segunda captura) Comparación con Kaggle en 2021
k21 = mx[mx["date"].dt.year == 2021]
cand = sem[(sem["semana"].dt.year == 2021) & sem["track_id"].isin(set(k21["track_id"]))]
comp = []
for _, r in cand.sort_values("posicion").groupby("track_id").head(2).head(20).iterrows():
    d = k21[k21["track_id"] == r["track_id"]].set_index("date")["streams"]
    comp.append({"semana": r["semana"].date(), "posicion": int(r["posicion"]), "kworb": r["streams"],
                 "kaggle_7_dias": d[(d.index > r["semana"] - pd.Timedelta(days=7)) & (d.index <= r["semana"])].sum()})
comp = pd.DataFrame(comp)
comp["coincide"] = comp["kworb"] == comp["kaggle_7_dias"]
print(comp)
