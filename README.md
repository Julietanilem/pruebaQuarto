# Proyecto Integrador — Almacenes y Minería de Datos

Facultad de Ciencias, UNAM. Proyecto Integrador construido de forma incremental sobre la metodología
**CRISP-DM**, entregado como sitio web con [Quarto](https://quarto.org/) y desplegado con GitHub
Pages.

**Sitio publicado:** <https://aymd-2027-1.github.io/almacenes-mineria-proyecto/>

## Integrantes

- Flores Morán Julieta Melina
- García Landa Brenda Yareli
- Jiménez Rivera Emiliano Kaleb
- Zarco Romero José Antonio

## Entregas

| Entrega | Fase CRISP-DM | Contenido |
|---|---|---|
| **E0 — Comprensión del negocio** | 1. Comprensión del negocio | Bitácora del stakeholder, Business Understanding Canvas, preguntas de investigación, criterio de éxito, riesgos y supuestos, uso de IA. |
| **E1 — Arquitectura del DW** | 2. Comprensión de los datos | **Fuentes de datos:** criterios de selección, búsqueda documentada, 27 fuentes evaluadas (19 aceptadas, de 14 tipos distintos, y 8 descartadas) y catálogo con una página por fuente. **Arquitectura** medallion en BigQuery (bronze/staging, silver/preparación, gold/DW y DataMart) con linaje y reglas de calidad. **Esquema estrella** con dos hechos (consumo musical por canción, entidad y mes; violencia por entidad, delito y mes) y cinco dimensiones, DDL y siete vistas del DataMart. Matriz de trazabilidad, pivote (consumo por entidad estimado con Google Trends), E0 v2, uso de IA y referencias. |

## Estructura del repositorio

```
.
├── entregas/
│   ├── E0_comprension_negocio/
│   │   ├── bitacora.qmd          # bitácora de la reunión con el stakeholder
│   │   ├── canvas.qmd            # Business Understanding Canvas
│   │   ├── preguntas.qmd         # preguntas de investigación priorizadas
│   │   ├── criterio_exito.qmd    # criterio de éxito en términos de negocio
│   │   ├── riesgos_supuestos.qmd # supuestos y riesgos
│   │   ├── uso_ia.qmd            # documentación de uso de LLMs
│   │   └── e0_v2.qmd             # secciones de E0 actualizadas tras el pivote
│   └── E1_arquitectura_dw/
│       ├── fuentes.qmd           # criterios, búsqueda documentada y fuentes evaluadas
│       ├── fuentes/              # catálogo: una página por fuente (F1–F19)
│       ├── arquitectura.qmd      # capas staging, DW y DataMart; integración; consultas del mart
│       ├── estrella.qmd          # grano, hechos, dimensiones, diagrama Mermaid y DDL
│       ├── trazabilidad.qmd      # matriz pregunta-métrica-dimensión-fuente
│       ├── pivote.qmd            # búsqueda de consumo por entidad y cambios respecto a E0
│       ├── datos/trends/         # descargas de Google Trends usadas como evidencia
│       ├── sql/                  # ddl_dw.sql, consultas_mart.sql
│       ├── uso_ia.qmd            # documentación de uso de LLMs
│       ├── referencias.qmd       # referencias citadas en E1
│       └── img/                  # capturas de pantalla, vistas previas y evidencia de BigQuery
├── assets/                       # logo y scripts del sitio
├── _quarto.yml                   # configuración y navegación del sitio (output-dir: docs)
├── index.qmd                     # página de inicio del sitio
├── theme.scss                    # estilos del sitio
├── docs/                         # sitio compilado (servido por GitHub Pages)
└── README.md
```

Este repositorio y su sitio Quarto se reutilizan durante todo el semestre: cada entrega agrega una
nueva carpeta en `entregas/` y sus páginas correspondientes al sitio.

## Cómo previsualizar el sitio localmente

Requiere tener [Quarto](https://quarto.org/docs/get-started/) instalado.

```bash
quarto preview
```

## Cómo compilar el sitio

```bash
quarto render
```

Esto genera el sitio estático en `docs/`, que es la carpeta que sirve GitHub Pages.

## Despliegue en GitHub Pages

1. Hacer `quarto render` y confirmar que `docs/` se generó correctamente.
2. Subir el repositorio a GitHub (`main` como rama por defecto).
3. En GitHub: **Settings -> Pages -> Branch: `main` / `docs`**.
4. Pegar la URL pública resultante en este README, en la sección "Sitio publicado" de arriba.


Para publicar modificaciones de Quarto en GitHub Pages: ejecutar `quarto render` en la raíz del repositorio antes de `git add -A`, porque Pages publica los HTML de `docs/`.


### E1 — Cierre de las fuentes de staging (octubre de 2026)

La arquitectura y las fichas documentan las 16 tablas creadas en `misoginia_staging`. El material reproducible de preparación se encuentra en `entregas/E1_arquitectura_dw/datos/staging/`: notebook de Colab, script de extracción de doce índices de *Hallazgos 2023*, CSV derivado y consultas de verificación. Se distingue la creación de una tabla de la validación definitiva de la calidad de todos sus registros.
