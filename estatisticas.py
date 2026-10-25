# O arquivo estatisticas serve para o processamento e análise dos dados meteorológicos.

from math import sqrt

from database import agregados_por_dia


def resumir(n, soma, soma_quadrados, minimo, maximo):
    """Transforma somas já calculadas em média, desvio padrão, mínimo e máximo.

    Desvio padrão amostral: sqrt((Σx² − (Σx)²/n) / (n − 1)).
    """
    if not n:
        return None
    media = soma / n
    if n > 1:
        variancia = (soma_quadrados - soma * soma / n) / (n - 1)
        desvio = sqrt(max(variancia, 0.0))  # max evita erro de arredondamento negativo
    else:
        desvio = 0.0
    return {
        "media": round(media, 2),
        "desvio_padrao": round(desvio, 2),
        "minimo": round(minimo, 2),
        "maximo": round(maximo, 2),
    }


def _montar(dias):
    """Junta um ou mais grupos de agregados em um único resultado."""
    total = sum(d["n"] for d in dias)
    if not total:
        return {"total_leituras": 0, "temperatura": None, "umidade": None}

    def resumo(soma, quad, minimo, maximo):
        return resumir(
            total,
            sum(d[soma] for d in dias),
            sum(d[quad] for d in dias),
            min(d[minimo] for d in dias),
            max(d[maximo] for d in dias),
        )

    return {
        "total_leituras": total,
        "temperatura": resumo("soma_t", "quad_t", "min_t", "max_t"),
        "umidade": resumo("soma_u", "quad_u", "min_u", "max_u"),
    }


def estatisticas_gerais():
    return _montar(agregados_por_dia())


def estatisticas_por_dia():
    """Uma linha por dia (em horário de SP), da mais antiga para a mais recente."""
    return [{"dia": d["dia"], **_montar([d])} for d in agregados_por_dia()]
