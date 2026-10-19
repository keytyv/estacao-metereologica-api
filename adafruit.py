# O arquivo adafruit serve para buscar as leituras que o ESP enviou ao Adafruit IO.
import json
from datetime import datetime, timedelta, timezone

import requests

URL_FEED = "https://io.adafruit.com/api/v2/larielivitoria/feeds/estacao/data"
FUSO_SP = timezone(timedelta(hours=-3))  # UTC-3 (horário de Brasília)


def converter_para_sp(created_at):
    """Converte '2026-10-02T19:46:06Z' (UTC) para '2026-10-02T16:46:06-03:00'."""
    em_utc = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return em_utc.astimezone(FUSO_SP).isoformat()


def buscar_leituras(limite=1000):
    """Consulta o feed e devolve uma lista de dicionários já tratados."""
    resposta = requests.get(URL_FEED, params={"limit": limite}, timeout=15)
    resposta.raise_for_status()

    leituras = []
    for item in resposta.json():
        try:
            # O campo "value" chega como texto JSON: '{"umidade": 70.6, "temperatura": 24.7}'
            valor = json.loads(item["value"])
            leituras.append({
                "adafruit_id": item["id"],
                "temperatura": float(valor["temperatura"]),
                "umidade": float(valor["umidade"]),
                "data_hora": converter_para_sp(item["created_at"]),
            })
        except (KeyError, ValueError, TypeError):
            # Ignora leituras malformadas em vez de derrubar a sincronização
            continue
    return leituras