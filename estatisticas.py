# O arquivo estatisticas serve para o processamento e análise dos dados meteorológicos.
from statistics import mean, median, stdev


def resumir(valores):
    """Recebe uma lista de números e devolve um dicionário com as estatísticas."""
    if not valores:
        return None
    return {
        "media": round(mean(valores), 2),
        "desvio_padrao": round(stdev(valores), 2) if len(valores) > 1 else 0.0,
    }


def estatisticas_gerais(leituras):
    temperaturas = [l["temperatura"] for l in leituras]
    umidades = [l["umidade"] for l in leituras]
    return {
        "total_leituras": len(leituras),
        "temperatura": resumir(temperaturas),
        "umidade": resumir(umidades),
    }


def estatisticas_por_dia(leituras):
    """Agrupa as leituras por dia (em horário de SP) usando um dicionário de listas."""
    por_dia = {}
    for leitura in leituras:
        dia = leitura["data_hora"][:10]  # 'AAAA-MM-DD'
        por_dia.setdefault(dia, []).append(leitura)

    resultado = []
    for dia in sorted(por_dia):
        resultado.append({"dia": dia, **estatisticas_gerais(por_dia[dia])})
    return resultado