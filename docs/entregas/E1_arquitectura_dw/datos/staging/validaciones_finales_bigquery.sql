-- Validaciones posteriores a las capturas: estas consultas no se ejecutaron en esta entrega.
SELECT 'RNPDNO' AS fuente, COUNT(*) AS filas
FROM `proyecto-511216.misoginia_staging.stg_rnpdno`
UNION ALL
SELECT 'MusicBrainz', COUNT(*)
FROM `proyecto-511216.misoginia_staging.stg_musicbrainz_tags`
UNION ALL
SELECT 'Mexico Evalua', COUNT(*)
FROM `proyecto-511216.misoginia_staging.stg_mexico_evalua_12_indices`;

SELECT delito, COUNT(*) AS registros,
  COUNTIF(entidad='Nacional') AS valores_nacionales
FROM `proyecto-511216.misoginia_staging.stg_mexico_evalua_12_indices`
GROUP BY delito ORDER BY delito;

SELECT COUNT(*) AS busquedas,
  COUNT(DISTINCT artista_buscado) AS nombres_distintos,
  COUNTIF(REGEXP_CONTAINS(respuesta_json, r'"error"\s*:')) AS respuestas_error
FROM `proyecto-511216.misoginia_staging.stg_musicbrainz_tags`;
