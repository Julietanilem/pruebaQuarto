-- =====================================================================
-- E1 · Arquitectura del DW — Consultas del DataMart
-- Una o más vistas por pregunta de E0, sobre el esquema estrella.
-- Operaciones OLAP: ROLLUP con GROUPING, funciones de ventana
-- (RANK, AVG y MAX con marco RANGE, SUM OVER, CORR OVER) y UNPIVOT.
-- Las vistas son válidas aunque las tablas del DW estén vacías.
--
-- Reglas que siguen todas las vistas:
--   * El consumo nacional es la suma de las 32 entidades (el reparto
--     conserva el total), así que no existe una fila "Nacional".
--   * Los datos nacionales repetidos en cada entidad (semanas en el
--     chart, mejor posición) se toman una sola vez por canción y mes.
--   * La proporción misógina solo cuenta canciones clasificadas
--     (es_misogina no nulo); la cobertura se reporta aparte.
--   * Todo resultado por entidad es una estimación y se marca así.
-- =====================================================================

-- ---------------------------------------------------------------------
-- P1a. Proporción misógina del consumo nacional por año, macrogénero y
--      género, con subtotales (ROLLUP) y marcas de subtotal (GROUPING).
--      Primero se vuelve al nivel nacional por canción y mes.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW misoginia_mart.p1_proporcion_misogina_genero AS
WITH nacional AS (
  SELECT
    f.fecha_key,
    f.cancion_key,
    SUM(f.streams_estimados)         AS streams,
    MAX(f.semanas_en_chart_nacional) AS semanas_en_chart
  FROM misoginia_dw.fact_consumo_musical AS f
  GROUP BY f.fecha_key, f.cancion_key
)
SELECT
  d.anio,
  c.macrogenero,
  c.genero,
  GROUPING(d.anio)        AS es_total_anios,
  GROUPING(c.macrogenero) AS es_total_macrogeneros,
  GROUPING(c.genero)      AS es_total_generos,
  COUNT(DISTINCT n.cancion_key) AS canciones,
  SUM(n.streams) AS streams,
  SAFE_DIVIDE(SUM(IF(c.es_misogina, n.streams, 0)),
              SUM(IF(c.es_misogina IS NOT NULL, n.streams, 0))) AS proporcion_misogina,
  SAFE_DIVIDE(SUM(IF(c.es_misogina, n.semanas_en_chart, 0)),
              SUM(IF(c.es_misogina IS NOT NULL, n.semanas_en_chart, 0))) AS proporcion_misogina_semanas,
  SAFE_DIVIDE(SUM(IF(c.es_misogina IS NOT NULL, n.streams, 0)),
              SUM(n.streams)) AS cobertura_clasificada,
  SAFE_DIVIDE(SUM(IF(c.origen_etiqueta = 'misongyny', n.streams, 0)),
              SUM(IF(c.es_misogina IS NOT NULL, n.streams, 0))) AS pct_etiqueta_humana
FROM nacional AS n
JOIN misoginia_dw.dim_fecha   AS d ON d.fecha_key = n.fecha_key
JOIN misoginia_dw.dim_cancion AS c ON c.cancion_key = n.cancion_key
GROUP BY ROLLUP (d.anio, c.macrogenero, c.genero);

-- ---------------------------------------------------------------------
-- P1b. Proporción misógina estimada por entidad y año, con el lugar de
--      cada entidad en el año (RANK) y su distancia al promedio estatal.
--      pct_peso_artista indica qué parte del consumo se repartió con
--      Trends del propio artista (el resto usa el género o los usuarios
--      de internet).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW misoginia_mart.p1_proporcion_misogina_entidad AS
WITH base AS (
  SELECT
    d.anio,
    e.cve_ent,
    e.entidad,
    SUM(IF(c.es_misogina, f.streams_estimados, 0))             AS streams_misoginos,
    SUM(IF(c.es_misogina IS NOT NULL, f.streams_estimados, 0)) AS streams_clasificados,
    SUM(IF(STARTS_WITH(f.origen_peso, 'artista'), f.streams_estimados, 0)) AS streams_peso_artista,
    SUM(f.streams_estimados) AS streams_totales
  FROM misoginia_dw.fact_consumo_musical AS f
  JOIN misoginia_dw.dim_fecha   AS d ON d.fecha_key = f.fecha_key
  JOIN misoginia_dw.dim_entidad AS e ON e.entidad_key = f.entidad_key
  JOIN misoginia_dw.dim_cancion AS c ON c.cancion_key = f.cancion_key
  GROUP BY d.anio, e.cve_ent, e.entidad
),
indicadores AS (
  SELECT
    anio,
    cve_ent,
    entidad,
    SAFE_DIVIDE(streams_misoginos, streams_clasificados) AS proporcion_misogina,
    SAFE_DIVIDE(streams_peso_artista, streams_totales)   AS pct_peso_artista
  FROM base
)
SELECT
  anio,
  cve_ent,
  entidad,
  proporcion_misogina,
  pct_peso_artista,
  RANK() OVER (PARTITION BY anio ORDER BY proporcion_misogina DESC) AS lugar_en_el_anio,
  proporcion_misogina
    - AVG(proporcion_misogina) OVER (PARTITION BY anio) AS diferencia_vs_promedio_estatal,
  TRUE AS es_estimacion
FROM indicadores;

-- ---------------------------------------------------------------------
-- P2a. Serie mensual nacional: proporción misógina del consumo frente a
--      las tasas por 100 mil mujeres de cada tipo de violencia.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW misoginia_mart.p2_serie_mensual_nacional AS
WITH musica AS (
  SELECT
    f.fecha_key,
    SAFE_DIVIDE(SUM(IF(c.es_misogina, f.streams_estimados, 0)),
                SUM(IF(c.es_misogina IS NOT NULL, f.streams_estimados, 0))) AS proporcion_misogina
  FROM misoginia_dw.fact_consumo_musical AS f
  JOIN misoginia_dw.dim_cancion AS c ON c.cancion_key = f.cancion_key
  GROUP BY f.fecha_key
),
violencia AS (
  SELECT
    v.fecha_key,
    t.tipo_lgamvlv,
    t.es_control,
    SUM(v.carpetas)         AS carpetas,
    SUM(v.victimas_mujeres) AS victimas_mujeres
  FROM misoginia_dw.fact_violencia AS v
  JOIN misoginia_dw.dim_tipo_violencia AS t ON t.tipo_violencia_key = v.tipo_violencia_key
  GROUP BY v.fecha_key, t.tipo_lgamvlv, t.es_control
),
poblacion AS (
  SELECT anio, SUM(poblacion_mujeres) AS mujeres
  FROM misoginia_dw.dim_contexto_entidad
  WHERE NOT es_nacional
  GROUP BY anio
)
SELECT
  d.fecha,
  d.anio,
  d.mes,
  vi.tipo_lgamvlv,
  vi.es_control,
  mu.proporcion_misogina,
  vi.carpetas,
  vi.victimas_mujeres,
  SAFE_DIVIDE(vi.carpetas, p.mujeres) * 100000         AS tasa_carpetas_100k_mujeres,
  SAFE_DIVIDE(vi.victimas_mujeres, p.mujeres) * 100000 AS tasa_victimas_100k_mujeres,
  -- Indicador de cada tipo: carpetas en delitos del SESNSP;
  -- mujeres desaparecidas en el RNPDNO, que no tiene carpetas
  SAFE_DIVIDE(COALESCE(vi.carpetas, vi.victimas_mujeres), p.mujeres) * 100000 AS tasa_indicador_100k_mujeres
FROM violencia AS vi
JOIN misoginia_dw.dim_fecha AS d ON d.fecha_key = vi.fecha_key
JOIN poblacion AS p ON p.anio = d.anio
LEFT JOIN musica AS mu ON mu.fecha_key = vi.fecha_key;

-- ---------------------------------------------------------------------
-- P2b. Coeficiente de correlación nacional por tipo de violencia, con el
--      número de meses que entran.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW misoginia_mart.p2_correlacion_nacional AS
SELECT
  tipo_lgamvlv,
  es_control,
  COUNTIF(proporcion_misogina IS NOT NULL AND tasa_indicador_100k_mujeres IS NOT NULL) AS n_meses,
  CORR(proporcion_misogina, tasa_indicador_100k_mujeres) AS correlacion_pearson
FROM misoginia_mart.p2_serie_mensual_nacional
GROUP BY tipo_lgamvlv, es_control;

-- ---------------------------------------------------------------------
-- P2c. Panel entidad-año: proporción misógina estimada frente a tasas
--      oficiales, con variables de control, la tasa de víctimas hombres para
--      comparar y la parte de víctimas menores de edad. CORR como función de ventana:
--      entre estados para cada año y con todos los años juntos.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW misoginia_mart.p2_panel_entidad_anio AS
WITH violencia AS (
  SELECT
    d.anio,
    e.cve_ent,
    t.tipo_lgamvlv,
    v.contexto_key,
    SUM(v.carpetas)                 AS carpetas,
    SUM(v.victimas_mujeres)         AS victimas_mujeres,
    SUM(v.victimas_mujeres_menores) AS victimas_mujeres_menores,
    SUM(v.victimas_hombres)         AS victimas_hombres
  FROM misoginia_dw.fact_violencia AS v
  JOIN misoginia_dw.dim_fecha          AS d ON d.fecha_key = v.fecha_key
  JOIN misoginia_dw.dim_entidad        AS e ON e.entidad_key = v.entidad_key
  JOIN misoginia_dw.dim_tipo_violencia AS t ON t.tipo_violencia_key = v.tipo_violencia_key
  GROUP BY d.anio, e.cve_ent, t.tipo_lgamvlv, v.contexto_key
),
panel AS (
  SELECT
    m.anio,
    m.cve_ent,
    m.entidad,
    vi.tipo_lgamvlv,
    m.proporcion_misogina,
    m.pct_peso_artista,
    SAFE_DIVIDE(vi.carpetas, ctx.poblacion_mujeres) * 100000         AS tasa_carpetas_100k_mujeres,
    SAFE_DIVIDE(vi.victimas_mujeres, ctx.poblacion_mujeres) * 100000 AS tasa_victimas_100k_mujeres,
    SAFE_DIVIDE(COALESCE(vi.carpetas, vi.victimas_mujeres), ctx.poblacion_mujeres) * 100000 AS tasa_indicador_100k_mujeres,
    SAFE_DIVIDE(vi.victimas_hombres, ctx.poblacion_hombres) * 100000 AS tasa_victimas_100k_hombres,
    SAFE_DIVIDE(vi.victimas_mujeres_menores, vi.victimas_mujeres)     AS pct_victimas_menores,
    ctx.pct_usuarios_internet,
    ctx.pct_pobreza,
    ctx.indice_impunidad
  FROM misoginia_mart.p1_proporcion_misogina_entidad AS m
  JOIN violencia AS vi ON vi.cve_ent = m.cve_ent AND vi.anio = m.anio
  JOIN misoginia_dw.dim_contexto_entidad AS ctx ON ctx.contexto_key = vi.contexto_key
)
SELECT
  anio,
  cve_ent,
  entidad,
  tipo_lgamvlv,
  proporcion_misogina,
  pct_peso_artista,
  tasa_carpetas_100k_mujeres,
  tasa_victimas_100k_mujeres,
  tasa_indicador_100k_mujeres,
  tasa_victimas_100k_hombres,
  pct_victimas_menores,
  pct_usuarios_internet,
  pct_pobreza,
  indice_impunidad,
  CORR(proporcion_misogina, tasa_indicador_100k_mujeres)
    OVER (PARTITION BY tipo_lgamvlv, anio) AS correlacion_entre_estados_del_anio,
  CORR(proporcion_misogina, tasa_indicador_100k_mujeres)
    OVER (PARTITION BY tipo_lgamvlv)       AS correlacion_panel_completo,
  TRUE AS es_estimacion
FROM panel;

-- ---------------------------------------------------------------------
-- P3. Evolución mensual nacional de cada tipo de violencia en la música:
--     participación en el consumo, media móvil de 12 meses y cambio
--     contra el mismo mes del año anterior. Los marcos RANGE sobre
--     indice_mes cuentan meses de calendario aunque falte alguno.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW misoginia_mart.p3_tendencia_tipo_violencia AS
WITH mensual AS (
  SELECT
    d.fecha,
    d.indice_mes,
    t.tipo_lgamvlv,
    SUM(f.streams_estimados) AS streams,
    -- El dato nacional se repite igual en las 32 entidades: el promedio no cambia
    AVG(f.mejor_posicion_nacional) AS posicion_promedio
  FROM misoginia_dw.fact_consumo_musical AS f
  JOIN misoginia_dw.dim_fecha          AS d ON d.fecha_key = f.fecha_key
  JOIN misoginia_dw.dim_cancion        AS c ON c.cancion_key = f.cancion_key
  JOIN misoginia_dw.dim_tipo_violencia AS t ON t.tipo_violencia_key = f.tipo_violencia_key
  WHERE c.es_misogina IS NOT NULL
  GROUP BY d.fecha, d.indice_mes, t.tipo_lgamvlv
),
participacion AS (
  SELECT
    *,
    SAFE_DIVIDE(streams, SUM(streams) OVER (PARTITION BY indice_mes)) AS participacion
  FROM mensual
)
SELECT
  fecha,
  tipo_lgamvlv,
  streams,
  posicion_promedio,
  participacion,
  AVG(participacion) OVER (PARTITION BY tipo_lgamvlv ORDER BY indice_mes
                           RANGE BETWEEN 11 PRECEDING AND CURRENT ROW) AS media_movil_12m,
  participacion - MAX(participacion) OVER (PARTITION BY tipo_lgamvlv ORDER BY indice_mes
                                           RANGE BETWEEN 12 PRECEDING AND 12 PRECEDING) AS cambio_anual
FROM participacion;

-- ---------------------------------------------------------------------
-- P4. Tipos de violencia: participación en la música misógina, en las
--     carpetas del SESNSP y prevalencia de la ENDIREH 2021, con el lugar
--     de cada tipo en cada fuente (RANK). Los tipos sin delito
--     equivalente aparecen con NULL en la columna oficial. La
--     desaparición (RNPDNO) no es un tipo de la LGAMVLV y no entra.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW misoginia_mart.p4_tipos_musica_vs_oficial AS
WITH tipos AS (
  SELECT tipo_lgamvlv, LOGICAL_OR(medido_en_sesnsp) AS medido_en_sesnsp
  FROM misoginia_dw.dim_tipo_violencia
  WHERE NOT es_control AND tipo_lgamvlv NOT IN ('no aplica', 'desaparición')
  GROUP BY tipo_lgamvlv
),
musica AS (
  SELECT t.tipo_lgamvlv, SUM(f.streams_estimados) AS streams
  FROM misoginia_dw.fact_consumo_musical AS f
  JOIN misoginia_dw.dim_cancion        AS c ON c.cancion_key = f.cancion_key
  JOIN misoginia_dw.dim_tipo_violencia AS t ON t.tipo_violencia_key = f.tipo_violencia_key
  WHERE c.es_misogina
  GROUP BY t.tipo_lgamvlv
),
oficial AS (
  SELECT t.tipo_lgamvlv, SUM(v.carpetas) AS carpetas
  FROM misoginia_dw.fact_violencia AS v
  JOIN misoginia_dw.dim_tipo_violencia AS t ON t.tipo_violencia_key = v.tipo_violencia_key
  WHERE NOT t.es_control
  GROUP BY t.tipo_lgamvlv
),
endireh AS (
  SELECT tipo_lgamvlv, prevalencia
  FROM (
    SELECT prevalencia_psicologica, prevalencia_fisica, prevalencia_sexual,
           prevalencia_economica_patrimonial
    FROM misoginia_dw.dim_contexto_entidad
    WHERE es_nacional AND anio = 2021
  )
  UNPIVOT (prevalencia FOR tipo_lgamvlv IN (
    prevalencia_psicologica           AS 'psicológica',
    prevalencia_fisica                AS 'física',
    prevalencia_sexual                AS 'sexual',
    prevalencia_economica_patrimonial AS 'económica o patrimonial'))
)
SELECT
  tp.tipo_lgamvlv,
  tp.medido_en_sesnsp,
  SAFE_DIVIDE(m.streams, SUM(m.streams) OVER ())   AS participacion_musica,
  SAFE_DIVIDE(o.carpetas, SUM(o.carpetas) OVER ()) AS participacion_sesnsp,
  n.prevalencia                                    AS prevalencia_endireh_2021,
  -- Un tipo sin dato en una fuente no recibe lugar en esa fuente
  IF(m.streams IS NULL, NULL, RANK() OVER (ORDER BY m.streams DESC))         AS lugar_musica,
  IF(o.carpetas IS NULL, NULL, RANK() OVER (ORDER BY o.carpetas DESC))       AS lugar_sesnsp,
  IF(n.prevalencia IS NULL, NULL, RANK() OVER (ORDER BY n.prevalencia DESC)) AS lugar_endireh
FROM tipos AS tp
LEFT JOIN musica  AS m ON m.tipo_lgamvlv = tp.tipo_lgamvlv
LEFT JOIN oficial AS o ON o.tipo_lgamvlv = tp.tipo_lgamvlv
LEFT JOIN endireh AS n ON n.tipo_lgamvlv = tp.tipo_lgamvlv;
