# Resumen de la corrida `mejorado`

Generado por `python -m observabilidad.analisis`. Datos reales de `resultados.csv` y `logs.jsonl`.

## Métricas globales

|                           |    valor |
|:--------------------------|---------:|
| ejecuciones               |    39    |
| casos                     |    13    |
| precision_pct             |    97.4  |
| precision_sin_errores_pct |    97.4  |
| consistencia_pct          |    94.9  |
| tasa_error_pct            |     0    |
| latencia_media_ms         |  2496.7  |
| latencia_p50_ms           |  1969.3  |
| latencia_p95_ms           |  5777.2  |
| latencia_max_ms           | 13030.9  |
| llm_share_pct             |    92.7  |
| tools_share_pct           |     7    |
| llamadas_llm_media        |     1.87 |
| tokens_in_media           |  2643.3  |
| tokens_out_media          |   112.8  |
| cpu_pct_media             |    18.6  |
| cpu_pct_max               |   107.1  |
| ram_mb_media              |   318.4  |
| ram_peak_mb               |  1143.6  |
| carga_inicial_ms          |    30.3  |

## Por escenario

| scenario   |   n |   precision_pct |   tasa_error_pct |   latencia_media_ms |   latencia_p95_ms |   llm_media |   tools_media |   tokens_in_media |   cpu_pct_media |   ram_peak_mb |
|:-----------|----:|----------------:|-----------------:|--------------------:|------------------:|------------:|--------------:|------------------:|----------------:|--------------:|
| normal     |  12 |           100   |                0 |              2192.6 |            2897.9 |        2    |          1    |              2660 |             2   |         669   |
| complejo   |   9 |           100   |                0 |              2524.4 |            3680.1 |        2    |          1.67 |              2738 |             2   |         564.1 |
| incompleto |   6 |           100   |                0 |              2459.8 |            4340   |        2.17 |          1.17 |              2825 |             1.8 |         564.2 |
| erroneo    |  12 |            91.7 |                0 |              2798.3 |           12856.8 |        1.5  |          1    |              2466 |            56.1 |        1143.6 |

## Por caso (con consistencia)

| caso_id   |   n |   precision_pct |   tasa_error_pct |   latencia_media_ms |   latencia_p95_ms |   llm_media |   tools_media |   tokens_in_media |   cpu_pct_media |   ram_peak_mb |   consistencia_pct |   firmas_distintas |
|:----------|----:|----------------:|-----------------:|--------------------:|------------------:|------------:|--------------:|------------------:|----------------:|--------------:|-------------------:|-------------------:|
| C1        |   3 |           100   |                0 |              2334.2 |            2674.8 |        2    |          2    |              2764 |             2.1 |         564   |              100   |                  1 |
| C2        |   3 |           100   |                0 |              2041   |            2198.2 |        2    |          1    |              2690 |             2.1 |         564.1 |              100   |                  1 |
| C3        |   3 |           100   |                0 |              3198   |            4002.5 |        2    |          2    |              2759 |             1.7 |         564.1 |              100   |                  1 |
| E1        |   3 |           100   |                0 |                 1   |               2.1 |        0    |          0    |                 0 |           100.9 |         425.5 |              100   |                  1 |
| E2        |   3 |           100   |                0 |                 0.8 |               0.9 |        0    |          0    |                 0 |           112.2 |         425.5 |              100   |                  1 |
| E3        |   3 |           100   |                0 |             10250.6 |           12999.2 |        5    |          4    |              8595 |             9.7 |        1143.6 |               66.7 |                  2 |
| E4        |   3 |            66.7 |                0 |               941   |            1119.4 |        1    |          0    |              1267 |             1.9 |         682.8 |               66.7 |                  2 |
| I1        |   3 |           100   |                0 |              2087.5 |            3059.5 |        2.33 |          1.33 |              3036 |             2.4 |         564.2 |              100   |                  1 |
| I2        |   3 |           100   |                0 |              2832   |            4437.1 |        2    |          1    |              2614 |             1.3 |         425.6 |              100   |                  1 |
| N1        |   3 |           100   |                0 |              2624.6 |            3387.8 |        2    |          1    |              2640 |             2.2 |         669   |              100   |                  1 |
| N2        |   3 |           100   |                0 |              2172.8 |            2395.2 |        2    |          1    |              2647 |             1.8 |         563.3 |              100   |                  1 |
| N3        |   3 |           100   |                0 |              2143.9 |            2379.6 |        2    |          1    |              2678 |             1.9 |         563.4 |              100   |                  1 |
| N4        |   3 |           100   |                0 |              1829.1 |            1870   |        2    |          1    |              2673 |             2   |         563.7 |              100   |                  1 |

## Latencia por etapa

| stage                       |   n |   media_ms |   p50_ms |   p95_ms |   max_ms |   suma_ms |   pct_del_tiempo_total |   errores |   sin_datos |
|:----------------------------|----:|-----------:|---------:|---------:|---------:|----------:|-----------------------:|----------:|------------:|
| llm                         |  73 |     1236.6 |    976.8 |   2372.5 |   5976.9 |     90275 |                   92.7 |         0 |           0 |
| tool:consultar_siniestros   |   3 |     2068.1 |    235.5 |   5205.7 |   5757.9 |      6204 |                    6.4 |         0 |           0 |
| tool:calcular_riesgo_comuna |  30 |       14.7 |     17.2 |     22   |     23.8 |       440 |                    0.5 |         0 |           6 |
| tool:ranking_riesgo         |   6 |       12.9 |     13.2 |     16.2 |     16.3 |        78 |                    0.1 |         0 |           0 |
| tool:consultar_estadisticas |   7 |        8.3 |      6.4 |     13.7 |     15   |        58 |                    0.1 |         0 |           1 |

## Errores y fallas

| error_type           |   ejecuciones | ejemplo_request_id   |   eventos_etapa |
|:---------------------|--------------:|:---------------------|----------------:|
| respuesta_incorrecta |             1 | 39ac067d9e22         |             nan |

## Anomalías (con request_id para rastrear en logs.jsonl)

| request_id   | caso_id   |   repeticion |   latency_ms |   n_llm | herramientas                                                                              | motivos                                                                  |
|:-------------|:----------|-------------:|-------------:|--------:|:------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------|
| 12bc56aed829 | I1        |            1 |       3229   |       3 | calcular_riesgo_comuna;consultar_estadisticas                                             | latencia > 2x mediana del caso (1534 ms)                                 |
| e7431b03a8fb | E3        |            1 |      13030.9 |       5 | calcular_riesgo_comuna;consultar_siniestros;consultar_estadisticas;calcular_riesgo_comuna | latencia > p95 global (5777 ms)                                          |
| bdbdc992f9c9 | E3        |            2 |      12714.4 |       5 | calcular_riesgo_comuna;consultar_siniestros;consultar_estadisticas;calcular_riesgo_comuna | latencia > p95 global (5777 ms)                                          |
| 39ac067d9e22 | E4        |            2 |        812   |       1 | nan                                                                                       | incorrecta: comunas listadas 0: []                                       |
| 7397bfc91f1d | I2        |            3 |       4710.4 |       2 | calcular_riesgo_comuna                                                                    | latencia > 2x mediana del caso (1978 ms)                                 |
| 54a0fbefabfc | E1        |            3 |          2.3 |       0 | nan                                                                                       | latencia > 2x mediana del caso (0 ms)                                    |
| e7431b03a8fb | E3        |            1 |       5757.9 |     nan | tool:consultar_siniestros                                                                 | arranque en frío de tool:consultar_siniestros: 5758 ms vs mediana 236 ms |
