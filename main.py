# O arquivo main serve para criar e cuidar da api

import asyncio
import logging
import os
import secrets
import threading
from contextlib import asynccontextmanager, suppress
from typing import List, Optional

import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from adafruit import buscar_leituras
from database import consultar_leituras, criar_tabela, inserir_leituras
from estatisticas import estatisticas_gerais, estatisticas_por_dia
from schemas import (
    Estatisticas,
    EstatisticasDia,
    Leitura,
    ResultadoSincronizacao,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("estacao")

# --- Configuração (tudo opcional, via variáveis de ambiente) -----------------
# SYNC_TOKEN             senha para chamar POST /sincronizar (sem ela a rota fica desativada)
# CORS_ORIGINS           sites autorizados a usar a API, separados por vírgula (padrão: todos)
# SYNC_INTERVAL_MINUTES  de quanto em quanto tempo sincronizar sozinha (0 = só ao ligar)
INTERVALO_SYNC_MIN = float(os.getenv("SYNC_INTERVAL_MINUTES", "5"))
ORIGENS_PERMITIDAS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

_trava_sync = threading.Lock()  # evita duas sincronizações ao mesmo tempo


def sincronizar():
    """Busca as leituras no Adafruit IO e grava as novas no banco."""
    with _trava_sync:
        leituras = buscar_leituras()
        novas = inserir_leituras(leituras)
    return {"leituras_no_feed": len(leituras), "novas_leituras": novas}


async def sincronizar_periodicamente():
    """Sincroniza ao ligar e depois a cada INTERVALO_SYNC_MIN minutos, em segundo plano."""
    while True:
        try:
            # to_thread roda a função "lenta" fora do loop principal, sem travar a API
            resultado = await asyncio.to_thread(sincronizar)
            logger.info("Sincronização: %s", resultado)
        except requests.RequestException as erro:
            logger.warning("Adafruit IO indisponível: %s", erro)
        except Exception:
            logger.exception("Erro inesperado na sincronização")

        if INTERVALO_SYNC_MIN <= 0:
            return
        await asyncio.sleep(INTERVALO_SYNC_MIN * 60)


@asynccontextmanager
async def ciclo_de_vida(app):
    # Ao ligar: cria a tabela e dispara a sincronização em segundo plano.
    # A API já responde na hora, mesmo que o Adafruit esteja lento ou fora do ar.
    criar_tabela()
    tarefa = asyncio.create_task(sincronizar_periodicamente())
    yield
    tarefa.cancel()
    with suppress(asyncio.CancelledError):
        await tarefa


app = FastAPI(
    title="API da Estação Meteorológica",
    description="Leituras de temperatura e umidade da estação, vindas do Adafruit IO.",
    version="2.0.0",
    lifespan=ciclo_de_vida,
)

# Libera o acesso do dashboard (front-end) à API.
# Em produção, defina CORS_ORIGINS com o endereço do dashboard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Cria o botão "Authorize" no Swagger para informar o token.
cabecalho_token = APIKeyHeader(name="X-Token", auto_error=False)


def exigir_token(token: Optional[str] = Depends(cabecalho_token)):
    esperado = os.getenv("SYNC_TOKEN")
    if not esperado:
        raise HTTPException(status_code=403, detail="Sincronização manual desativada (SYNC_TOKEN não definido)")
    # compare_digest compara sem vazar informação pelo tempo de resposta
    if not token or not secrets.compare_digest(token, esperado):
        raise HTTPException(status_code=401, detail="Token inválido")


@app.get("/", tags=["Geral"])
def inicio():
    return {"mensagem": "API da Estação Meteorológica funcionando!", "documentacao": "/docs"}


@app.get("/saude", tags=["Geral"])
def saude():
    """Rota leve para o Render (ou um monitor) verificar se a API está de pé."""
    return {"status": "ok"}


@app.post(
    "/sincronizar",
    response_model=ResultadoSincronizacao,
    dependencies=[Depends(exigir_token)],
    tags=["Leituras"],
)
def rota_sincronizar():
    """Força uma sincronização com o Adafruit IO (exige o cabeçalho X-Token)."""
    try:
        return sincronizar()
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="Não foi possível acessar o Adafruit IO")


@app.get("/leituras", response_model=List[Leitura], tags=["Leituras"])
def leituras(
    limite: int = Query(1000, ge=1, le=5000, description="Quantas leituras devolver"),
    deslocamento: int = Query(0, ge=0, description="Quantas leituras pular (paginação)"),
):
    """Leituras da mais recente para a mais antiga."""
    return consultar_leituras(limite, deslocamento)


@app.get("/leituras/ultima", response_model=Leitura, tags=["Leituras"])
def ultima_leitura():
    resultado = consultar_leituras(limite=1)
    if not resultado:
        raise HTTPException(status_code=404, detail="Nenhuma leitura no banco ainda")
    return resultado[0]


@app.get("/estatisticas", response_model=Estatisticas, tags=["Estatísticas"])
def estatisticas():
    return estatisticas_gerais()


@app.get("/estatisticas/diarias", response_model=List[EstatisticasDia], tags=["Estatísticas"])
def estatisticas_diarias():
    return estatisticas_por_dia()
