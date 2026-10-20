import random
from datetime import datetime, timedelta

import pandas as pd

random.seed(42)

# (comuna, region, ruta, peso_riesgo)
ZONAS = [
    ("Santiago", "Metropolitana", "Av. Libertador Bernardo O'Higgins", 5),
    ("Maipú", "Metropolitana", "Camino a Melipilla", 6),
    ("Puente Alto", "Metropolitana", "Av. Concha y Toro", 5),
    ("Quilicura", "Metropolitana", "Ruta 5 Norte", 4),
    ("Melipilla", "Metropolitana", "Ruta 78", 6),
    ("San Bernardo", "Metropolitana", "Ruta 5 Sur", 5),
    ("Valparaíso", "Valparaíso", "Av. España", 3),
    ("Viña del Mar", "Valparaíso", "Ruta 68", 4),
    ("Concepción", "Biobío", "Autopista Concepción-Talcahuano", 4),
    ("Los Ángeles", "Biobío", "Ruta 5 Sur", 3),
    ("Temuco", "Araucanía", "Ruta 5 Sur", 3),
    ("Antofagasta", "Antofagasta", "Ruta 1", 2),
    ("La Serena", "Coquimbo", "Ruta 5 Norte", 2),
    ("Puerto Montt", "Los Lagos", "Ruta 5 Sur", 2),
]

TIPOS = ["Colisión", "Atropello", "Choque", "Volcamiento", "Caída"]
CAUSAS = [
    "Exceso de velocidad",
    "Imprudencia del conductor",
    "Desobediencia a la señalización",
    "Conducción bajo la influencia del alcohol",
    "Fatiga o somnolencia",
    "Distracción al volante",
]
CLIMAS = ["Despejado", "Lluvia", "Niebla", "Nublado"]

filas = []
inicio = datetime(2025, 1, 1)
for i in range(1, 801):
    comuna, region, ruta, peso = random.choices(
        ZONAS, weights=[z[3] for z in ZONAS]
    )[0]
    fecha = inicio + timedelta(
        days=random.randint(0, 364), hours=random.randint(0, 23)
    )
    clima = random.choices(CLIMAS, weights=[55, 20, 5, 20])[0]
    tipo = random.choice(TIPOS)
    causa = random.choice(CAUSAS)
    graves = random.choices([0, 1, 2, 3], weights=[60, 25, 10, 5])[0]
    fallecidos = random.choices([0, 1, 2], weights=[88, 10, 2])[0]
    if clima in ("Lluvia", "Niebla") and random.random() < 0.3:
        graves += 1
    filas.append(
        {
            "id_siniestro": i,
            "fecha": fecha.strftime("%Y-%m-%d"),
            "hora": fecha.strftime("%H:%M"),
            "region": region,
            "comuna": comuna,
            "ruta": ruta,
            "tipo": tipo,
            "causa": causa,
            "clima": clima,
            "lesionados_graves": graves,
            "fallecidos": fallecidos,
        }
    )

df = pd.DataFrame(filas)
df.to_csv("data/siniestros.csv", index=False, encoding="utf-8")
print(f"OK: {len(df)} siniestros guardados en data/siniestros.csv")
print(df.head())