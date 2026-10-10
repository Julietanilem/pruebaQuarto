-- =====================================================================
-- E1 · Arquitectura del DW — DDL
-- Misoginia en la música consumida en México y violencia de género
-- Ejecutar en BigQuery con el proyecto del equipo seleccionado.
-- Los tres datasets deben quedar en la misma ubicación (US).
-- Orden: datasets, dimensiones y al final hechos (las FK citan PK ya creadas).
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Datasets (capas)
-- ---------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS misoginia_staging
  OPTIONS (location = 'US',
           description = 'Staging (bronze): datos crudos, tal como vienen de cada fuente del catálogo');

CREATE SCHEMA IF NOT EXISTS misoginia_dw
  OPTIONS (location = 'US',
           description = 'DW (gold): esquema estrella con dos hechos y cinco dimensiones');

CREATE SCHEMA IF NOT EXISTS misoginia_mart
  OPTIONS (location = 'US',
           description = 'DataMart (gold): vistas que responden P1 a P4');

-- ---------------------------------------------------------------------
-- 2. Dimensiones
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE misoginia_dw.dim_fecha (
  fecha_key            INT64  NOT NULL OPTIONS (description = 'Llave sustituta AAAAMM01: primer día del mes'),
  fecha                DATE   NOT NULL OPTIONS (description = 'Primer día del mes'),
  anio                 INT64  NOT NULL,
  semestre             INT64,
  trimestre            INT64,
  mes                  INT64  NOT NULL,
  nombre_mes           STRING,
  indice_mes           INT64  NOT NULL OPTIONS (description = 'anio * 12 + mes; ordena los meses aunque falten algunos'),
  evento_restriccion_musical STRING OPTIONS (description = 'Propuesta nacional para restringir música en ese mes (Senado, marzo de 2020); NULL si no hubo'),
  PRIMARY KEY (fecha_key) NOT ENFORCED
)
OPTIONS (description = 'Tiempo a nivel mes, calendario generado. SCD tipo 0. Responde: P1, P2, P3');

CREATE OR REPLACE TABLE misoginia_dw.dim_entidad (
  entidad_key    INT64  NOT NULL OPTIONS (description = 'Llave sustituta'),
  cve_ent        INT64  NOT NULL OPTIONS (description = 'Clave INEGI de la entidad, 1 a 32'),
  entidad        STRING NOT NULL OPTIONS (description = 'Nombre del catálogo INEGI'),
  nombre_trends  STRING OPTIONS (description = 'Nombre tal como lo escribe Google Trends en español (Estado de México, Coahuila de Zaragoza...); el catálogo de silver guarda también la versión en inglés'),
  iso_3166_2     STRING OPTIONS (description = 'Código ISO de la subregión (MX-CMX, MX-YUC...)'),
  region         STRING OPTIONS (description = 'Región del Banco de México: norte, centro norte, centro o sur. Jerarquía entidad -> región'),
  geometry_wkt   STRING OPTIONS (description = 'Natural Earth (F18), para mapas'),
  PRIMARY KEY (entidad_key) NOT ENFORCED
)
OPTIONS (description = 'Entidad federativa. SCD tipo 0: las 32 entidades no cambian en la ventana. Conformada entre ambos hechos. Responde: P1, P2');

CREATE OR REPLACE TABLE misoginia_dw.dim_cancion (
  cancion_key          INT64  NOT NULL OPTIONS (description = 'Llave sustituta'),
  spotify_id           STRING OPTIONS (description = 'Llave natural: ID de Spotify que usa Kworb (F4); Kaggle (F5) puede tener otro ID para la misma canción'),
  clave_cancion        STRING OPTIONS (description = 'Artista y título normalizados; une con LRCLIB (F7) y MiSonGyny (F6)'),
  titulo               STRING,
  artista_principal    STRING,
  artistas             STRING OPTIONS (description = 'Todos los artistas acreditados'),
  termino_trends       STRING OPTIONS (description = 'Tema de Google Trends (F11) del artista, o su término más común si no tiene tema'),
  pais_artista         STRING OPTIONS (description = 'País del artista, MusicBrainz (F8)'),
  genero               STRING OPTIONS (description = 'Género principal del artista: MusicBrainz (F8) o Last.fm (F19), revisado a mano'),
  macrogenero          STRING OPTIONS (description = 'Agrupación de las etiquetas más frecuentes de los artistas principales (urbano, regional mexicano, pop...). Jerarquía genero -> macrogenero'),
  etiquetas_fuente     STRING OPTIONS (description = 'Etiquetas crudas de MusicBrainz (F8) o Last.fm (F19), separadas por coma'),
  tiene_letra          BOOL   OPTIONS (description = 'Letra encontrada en LRCLIB (F7); la letra no se guarda'),
  en_corpus_misongyny  BOOL   OPTIONS (description = 'La canción está etiquetada en MiSonGyny (F6)'),
  etiqueta_misongyny   STRING OPTIONS (description = 'Etiqueta de referencia de MiSonGyny, para validar'),
  es_misogina          BOOL   OPTIONS (description = 'Salida del clasificador; NULL si no hay letra'),
  categoria_misoginia  STRING OPTIONS (description = 'sexualización, violencia, odio o no relacionada (categorías de MiSonGyny)'),
  score_misoginia      FLOAT64 OPTIONS (description = 'Probabilidad del clasificador'),
  origen_etiqueta      STRING OPTIONS (description = 'misongyny (etiqueta humana del corpus F6) o clasificador; NULL si no hay letra'),
  version_modelo       STRING OPTIONS (description = 'Versión del clasificador que asignó la etiqueta'),
  PRIMARY KEY (cancion_key) NOT ENFORCED
)
OPTIONS (description = 'Canción consumida, con su artista, género y clasificación. SCD tipo 1: al reentrenar el clasificador se reclasifica toda la historia. Responde: P1, P2, P3, P4');

CREATE OR REPLACE TABLE misoginia_dw.dim_tipo_violencia (
  tipo_violencia_key  INT64  NOT NULL OPTIONS (description = 'Llave sustituta; -1 = no aplica (canción no misógina o sin letra)'),
  tipo_lgamvlv        STRING NOT NULL OPTIONS (description = 'psicológica, física, sexual, económica o patrimonial, feminicida, mediática, sin distinguir, desaparición, control, no aplica'),
  ambito_lgamvlv      STRING OPTIONS (description = 'familiar, comunitario u otro, cuando el delito lo define'),
  origen              STRING NOT NULL OPTIONS (description = 'SESNSP, RNPDNO o clasificador'),
  categoria_origen    STRING OPTIONS (description = 'Categoría tal como la nombra la fuente: delito del SESNSP, estatus del RNPDNO (sin localizar, localizada con vida, localizada sin vida) o categoría de MiSonGyny'),
  bien_juridico       STRING OPTIONS (description = 'SESNSP: bien jurídico afectado'),
  tipo_delito         STRING OPTIONS (description = 'SESNSP'),
  subtipo_delito      STRING OPTIONS (description = 'SESNSP'),
  modalidad           STRING OPTIONS (description = 'SESNSP'),
  medido_en_sesnsp    BOOL   OPTIONS (description = 'FALSE para tipos sin delito equivalente (económica o patrimonial, mediática) y para el RNPDNO'),
  es_control          BOOL   OPTIONS (description = 'TRUE para homicidio doloso total, control de violencia general'),
  PRIMARY KEY (tipo_violencia_key) NOT ENFORCED
)
OPTIONS (description = 'Tipos de violencia mapeados a la LGAMVLV. Conformada entre ambos hechos por tipo_lgamvlv. SCD tipo 1: el mapeo se corrige sobrescribiendo. Responde: P2, P3, P4');

CREATE OR REPLACE TABLE misoginia_dw.dim_contexto_entidad (
  contexto_key                 INT64  NOT NULL OPTIONS (description = 'Llave sustituta: una por entidad y año'),
  cve_ent                      INT64  NOT NULL OPTIONS (description = 'Clave INEGI 1-32; 0 = fila nacional de referencia, sin hechos'),
  anio                         INT64  NOT NULL,
  es_nacional                  BOOL   NOT NULL,
  poblacion_total              INT64  OPTIONS (description = 'CONAPO (F3), mitad de año'),
  poblacion_mujeres            INT64  OPTIONS (description = 'CONAPO (F3), mitad de año; denominador de tasas'),
  poblacion_mujeres_15_mas     INT64  OPTIONS (description = 'CONAPO (F3); denominador de la ENDIREH'),
  poblacion_hombres            INT64  OPTIONS (description = 'CONAPO (F3), mitad de año; denominador de la tasa de víctimas hombres'),
  pct_usuarios_internet        FLOAT64 OPTIONS (description = 'ENDUTIH (F16)'),
  usuarios_internet_estimados  INT64  OPTIONS (description = 'poblacion_total * pct_usuarios_internet; escala el interés de búsqueda'),
  pct_viviendas_internet       FLOAT64 OPTIONS (description = 'Censo 2020 ITER (F14); solo 2020'),
  pct_pobreza                  FLOAT64 OPTIONS (description = 'CONEVAL (F15); años pares'),
  indice_impunidad             FLOAT64 OPTIONS (description = 'México Evalúa (F17)'),
  propuesta_restriccion_musical STRING OPTIONS (description = 'Propuesta estatal para restringir música en ese año (Sinaloa, 2019); NULL si no hubo'),
  prevalencia_total            FLOAT64 OPTIONS (description = 'ENDIREH (F2), % de mujeres de 15 años y más, últimos 12 meses; solo años de levantamiento'),
  prevalencia_psicologica      FLOAT64 OPTIONS (description = 'ENDIREH (F2)'),
  prevalencia_fisica           FLOAT64 OPTIONS (description = 'ENDIREH (F2)'),
  prevalencia_sexual           FLOAT64 OPTIONS (description = 'ENDIREH (F2)'),
  prevalencia_economica_patrimonial FLOAT64 OPTIONS (description = 'ENDIREH (F2)'),
  PRIMARY KEY (contexto_key) NOT ENFORCED
)
OPTIONS (description = 'Contexto anual de cada entidad (mini-dimensión). SCD tipo 1: las fuentes revisan sus cifras y se sobrescriben. Responde: P1, P2, P4');

-- ---------------------------------------------------------------------
-- 3. Hechos
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE misoginia_dw.fact_consumo_musical (
  fecha_key               INT64 NOT NULL,
  entidad_key             INT64 NOT NULL,
  cancion_key             INT64 NOT NULL,
  tipo_violencia_key      INT64 NOT NULL OPTIONS (description = 'Tipo principal de la letra; -1 si no aplica'),
  contexto_key            INT64 NOT NULL OPTIONS (description = 'Contexto de la entidad en el año del mes'),
  streams_estimados       FLOAT64 OPTIONS (description = 'Streams nacionales del mes (chart semanal de Kworb, F4, repartido por días) x peso_entidad. Aditiva. 2015-2025'),
  peso_entidad            FLOAT64 OPTIONS (description = 'Participación estimada de la entidad en el consumo de la canción; suma 1 entre las 32. No aditiva'),
  interes_busqueda        INT64   OPTIONS (description = 'Google Trends (F11): interés del tema en la entidad durante el año, 0-100, relativo a su descarga. No aditiva'),
  semanas_en_chart_nacional INT64 OPTIONS (description = 'Semanas del chart semanal nacional que terminan en el mes. Dato nacional repetido en las 32 entidades: no se suma entre entidades'),
  mejor_posicion_nacional INT64   OPTIONS (description = 'Mejor posición semanal nacional entre las semanas que terminan en el mes. Dato nacional repetido. No aditiva'),
  origen_peso             STRING  OPTIONS (description = 'De dónde salió el peso, en orden de preferencia: artista_anio, genero_anio o usuarios_internet'),
  fuente                  STRING  OPTIONS (description = 'Código del catálogo de la fila de consumo: F4 (Kworb)'),
  PRIMARY KEY (fecha_key, entidad_key, cancion_key) NOT ENFORCED,
  FOREIGN KEY (fecha_key) REFERENCES misoginia_dw.dim_fecha (fecha_key) NOT ENFORCED,
  FOREIGN KEY (entidad_key) REFERENCES misoginia_dw.dim_entidad (entidad_key) NOT ENFORCED,
  FOREIGN KEY (cancion_key) REFERENCES misoginia_dw.dim_cancion (cancion_key) NOT ENFORCED,
  FOREIGN KEY (tipo_violencia_key) REFERENCES misoginia_dw.dim_tipo_violencia (tipo_violencia_key) NOT ENFORCED,
  FOREIGN KEY (contexto_key) REFERENCES misoginia_dw.dim_contexto_entidad (contexto_key) NOT ENFORCED
)
OPTIONS (description = 'Grano: una fila por canción, entidad y mes. El consumo por entidad es una estimación: el consumo nacional del mes se reparte con el interés de búsqueda del artista por entidad. Responde: P1, P2, P3, P4');

CREATE OR REPLACE TABLE misoginia_dw.fact_violencia (
  fecha_key           INT64 NOT NULL,
  entidad_key         INT64 NOT NULL,
  tipo_violencia_key  INT64 NOT NULL OPTIONS (description = 'Delito del SESNSP al nivel de modalidad, o desaparición del RNPDNO'),
  contexto_key        INT64 NOT NULL OPTIONS (description = 'Contexto de la entidad en el año del mes'),
  carpetas            INT64 OPTIONS (description = 'Carpetas de investigación, archivo de delitos del SESNSP (F1). Aditiva'),
  victimas_mujeres    INT64 OPTIONS (description = 'Víctimas mujeres del SESNSP (F1) o mujeres desaparecidas del RNPDNO (F13); NULL si la fuente no lo reporta. Aditiva'),
  victimas_mujeres_menores INT64 OPTIONS (description = 'Parte de victimas_mujeres menores de 18 años (rango de edad del SESNSP, edad del RNPDNO). Aditiva'),
  victimas_hombres    INT64 OPTIONS (description = 'Víctimas hombres del archivo de víctimas del SESNSP (F1), para comparar. Aditiva'),
  fuente              STRING OPTIONS (description = 'Código del catálogo: F1 o F13'),
  PRIMARY KEY (fecha_key, entidad_key, tipo_violencia_key) NOT ENFORCED,
  FOREIGN KEY (fecha_key) REFERENCES misoginia_dw.dim_fecha (fecha_key) NOT ENFORCED,
  FOREIGN KEY (entidad_key) REFERENCES misoginia_dw.dim_entidad (entidad_key) NOT ENFORCED,
  FOREIGN KEY (tipo_violencia_key) REFERENCES misoginia_dw.dim_tipo_violencia (tipo_violencia_key) NOT ENFORCED,
  FOREIGN KEY (contexto_key) REFERENCES misoginia_dw.dim_contexto_entidad (contexto_key) NOT ENFORCED
)
OPTIONS (description = 'Grano: una fila por entidad, delito o registro (modalidad del SESNSP o desaparición del RNPDNO) y mes. Responde: P2, P3, P4');
