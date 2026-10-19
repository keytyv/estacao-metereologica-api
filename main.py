# O arquivo main serve para criar e cuidar da api
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from adafruit import buscar_leituras
from database import consultar_leituras, criar_tabela, inserir_leituras
from estatisticas import estatisticas_gerais, estatisticas_por_dia


def sincronizar():
    """Busca as leituras no Adafruit IO e grava as novas no banco."""
    leituras = buscar_leituras()
    novas = inserir_leituras(leituras)
    return {"leituras_no_feed": len(leituras), "novas_leituras": novas}


@asynccontextmanager
async def ciclo_de_vida(app):
    # Ao ligar a API: cria a tabela e já puxa as leituras do Adafruit.
    # Se o Adafruit estiver fora do ar, a API sobe mesmo assim.
    criar_tabela()
    try:
        sincronizar()
    except requests.RequestException:
        pass
    yield


app = FastAPI(title="API da Estação Meteorológica", lifespan=ciclo_de_vida)

# Libera o acesso do dashboard (front-end) à API
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
def inicio():
    return {"mensagem": "API da Estação Meteorológica funcionando!"}


@app.post("/sincronizar")
def rota_sincronizar():
    try:
        return sincronizar()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Não foi possível acessar o Adafruit IO")


@app.get("/leituras")
def leituras(limite: int = Query(None, ge=1, le=5000)):
    return consultar_leituras(limite)


@app.get("/leituras/ultima")
def ultima_leitura():
    resultado = consultar_leituras(limite=1)
    if not resultado:
        raise HTTPException(status_code=404, detail="Nenhuma leitura no banco ainda")
    return resultado[0]


@app.get("/estatisticas")
def estatisticas():
    return estatisticas_gerais(consultar_leituras())


@app.get("/estatisticas/diarias")
def estatisticas_diarias():
    return estatisticas_por_dia(consultar_leituras())