-- Validación de cierre E1, ejecutada en BigQuery el 10 de octubre de 2026.
SELECT 'RNPDNO' AS fuente, COUNT(*) AS filas FROM `proyecto-511216.misoginia_staging.stg_rnpdno`
UNION ALL SELECT 'MusicBrainz', COUNT(*) FROM `proyecto-511216.misoginia_staging.stg_musicbrainz_tags`
UNION ALL SELECT 'México Evalúa', COUNT(*) FROM `proyecto-511216.misoginia_staging.stg_mexico_evalua_12_indices`
UNION ALL SELECT 'Censo ITER', COUNT(*) FROM `proyecto-511216.misoginia_staging.stg_censo_iter`
UNION ALL SELECT 'ENDUTIH', COUNT(*) FROM `proyecto-511216.misoginia_staging.stg_endutih_usuarios`;
