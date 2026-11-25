# Resumen de la corrida `base`

Generado por `python -m observabilidad.analisis`. Datos reales de `resultados.csv` y `logs.jsonl`.

## Métricas globales

|                           |   valor |
|:--------------------------|--------:|
| ejecuciones               |    39   |
| casos                     |    13   |
| precision_pct             |    94.9 |
| precision_sin_errores_pct |    94.9 |
| consistencia_pct          |    97.4 |
| tasa_error_pct            |     0   |
| latencia_media_ms         |  2567.5 |
| latencia_p50_ms           |  2027.1 |
| latencia_p95_ms           |  6876.2 |
| latencia_max_ms           | 10870.6 |
| llm_share_pct             |    93.1 |
| tools_share_pct           |     6.6 |
| llamadas_llm_media        |     1.9 |
| tokens_in_media           |  2323.9 |
| tokens_out_media          |   123.5 |
| cpu_pct_media             |     3   |
| cpu_pct_max               |   108.1 |
| ram_mb_media              |   706.2 |
| ram_peak_mb               |  1228   |
| carga_inicial_ms          |    28.2 |

## Por escenario

| scenario   |   n |   precision_pct |   tasa_error_pct |   latencia_media_ms |   latencia_p95_ms |   llm_media |   tools_media |   tokens_in_media |   cpu_pct_media |   ram_peak_mb |
|:-----------|----:|----------------:|-----------------:|--------------------:|------------------:|------------:|--------------:|------------------:|----------------:|--------------:|
| normal     |  12 |            83.3 |                0 |              3046.4 |            7010   |        2    |          1    |              2486 |             5.4 |        1228   |
| complejo   |   9 |           100   |                0 |              1982.4 |            2494.2 |        2    |          1.67 |              2456 |             2.2 |         901   |
| incompleto |   6 |           100   |                0 |              2314.9 |            3337.8 |        2.33 |          1.33 |              2905 |             2.4 |         908.1 |
| erroneo    |  12 |           100   |                0 |              2653.6 |            7191.8 |        1.5  |          0.5  |              1772 |             1.4 |         693.7 |

## Por caso (con consistencia)

| caso_id   |   n |   precision_pct |   tasa_error_pct |   latencia_media_ms |   latencia_p95_ms |   llm_media |   tools_media |   tokens_in_media |   cpu_pct_media |   ram_peak_mb |   consistencia_pct |   firmas_distintas |
|:----------|----:|----------------:|-----------------:|--------------------:|------------------:|------------:|--------------:|------------------:|----------------:|--------------:|-------------------:|-------------------:|
| C1        |   3 |           100   |                0 |              2300.3 |            2684   |        2    |          2    |              2480 |             2.1 |         900.7 |              100   |                  1 |
| C2        |   3 |           100   |                0 |              1956.3 |            2025.8 |        2    |          1    |              2412 |             2   |         900.9 |              100   |                  1 |
| C3        |   3 |           100   |                0 |              1690.5 |            1792.7 |        2    |          2    |              2475 |             2.6 |         901   |              100   |                  1 |
| E1        |   3 |           100   |                0 |               913.2 |             935.6 |        1    |          0    |              1120 |             1.6 |         693.6 |              100   |                  1 |
| E2        |   3 |           100   |                0 |              1012.6 |            1236.6 |        1    |          0    |              1145 |             1.5 |         693.6 |              100   |                  1 |
| E3        |   3 |           100   |                0 |              2873.3 |            3367.8 |        2    |          1    |              2363 |             1.5 |         693.7 |              100   |                  1 |
| E4        |   3 |           100   |                0 |              5815.4 |           10201.7 |        2    |          1    |              2462 |             1.1 |         693.7 |              100   |                  1 |
| I1        |   3 |           100   |                0 |              2762.2 |            3448.8 |        2.67 |          1.67 |              3461 |             3.3 |         908.1 |              100   |                  1 |
| I2        |   3 |           100   |                0 |              1867.5 |            1894.6 |        2    |          1    |              2349 |             1.6 |         693.6 |              100   |                  1 |
| N1        |   3 |           100   |                0 |              2147.2 |            2536.5 |        2    |          1    |              2363 |             2.4 |         692.2 |              100   |                  1 |
| N2        |   3 |           100   |                0 |              2585.8 |            3544.5 |        2    |          1    |              2370 |             1.7 |         692.2 |              100   |                  1 |
| N3        |   3 |           100   |                0 |              3672.6 |            6390.9 |        2    |          1    |              2400 |             1.5 |         692.2 |              100   |                  1 |
| N4        |   3 |            33.3 |                0 |              3780.1 |            6706.4 |        2    |          1    |              2811 |            16   |        1228   |               66.7 |                  2 |

## Latencia por etapa

| stage                       |   n |   media_ms |   p50_ms |   p95_ms |   max_ms |   suma_ms |   pct_del_tiempo_total |   errores |   sin_datos |
|:----------------------------|----:|-----------:|---------:|---------:|---------:|----------:|-----------------------:|----------:|------------:|
| llm                         |  74 |     1259.8 |    947.2 |   2561.3 |   9262.8 |     93222 |                   93.1 |         0 |           0 |
| tool:consultar_siniestros   |   5 |     1245.4 |    301   |   4124.3 |   4940.8 |      6227 |                    6.2 |         0 |           0 |
| tool:calcular_riesgo_comuna |  27 |        9.7 |      9   |     15.9 |     16.5 |       262 |                    0.3 |         0 |           6 |
| tool:ranking_riesgo         |   9 |        8.5 |      8.4 |      9.4 |      9.5 |        77 |                    0.1 |         0 |           0 |

## Errores y fallas

| error_type           |   ejecuciones | ejemplo_request_id   |   eventos_etapa |
|:---------------------|--------------:|:---------------------|----------------:|
| respuesta_incorrecta |             2 | 00c83dcb523d         |             nan |

## Anomalías (con request_id para rastrear en logs.jsonl)

| request_id   | caso_id   |   repeticion |   latency_ms |   n_llm | herramientas              | motivos                                                                                                    |
|:-------------|:----------|-------------:|-------------:|--------:|:--------------------------|:-----------------------------------------------------------------------------------------------------------|
| 00c83dcb523d | N4        |            1 |       7220.2 |       2 | consultar_siniestros      | latencia > p95 global (6876 ms); latencia > 2x mediana del caso (2083 ms); incorrecta: siniestros 47:False |
| 16242047e38b | E4        |            1 |      10870.6 |       2 | ranking_riesgo            | latencia > p95 global (6876 ms); latencia > 2x mediana del caso (4182 ms)                                  |
| 1d28e7e8bd75 | N4        |            2 |       2082.7 |       2 | consultar_siniestros      | incorrecta: siniestros 47:False                                                                            |
| 94ffddcfe17f | N3        |            3 |       6838   |       2 | ranking_riesgo            | latencia > 2x mediana del caso (2367 ms)                                                                   |
| 00c83dcb523d | N4        |            1 |       4940.8 |     nan | tool:consultar_siniestros | arranque en frío de tool:consultar_siniestros: 4941 ms vs mediana 301 ms                                   |
