# O arquivo schemas descreve o formato das respostas (aparece no Swagger em /docs).

from typing import Optional

from pydantic import BaseModel


class Leitura(BaseModel):
    id: int
    temperatura: float
    umidade: float
    data_hora: str


class Resumo(BaseModel):
    media: float
    desvio_padrao: float
    minimo: float
    maximo: float


class Estatisticas(BaseModel):
    total_leituras: int
    temperatura: Optional[Resumo] = None
    umidade: Optional[Resumo] = None


class EstatisticasDia(Estatisticas):
    dia: str


class ResultadoSincronizacao(BaseModel):
    leituras_no_feed: int
    novas_leituras: int
