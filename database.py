# O arquivo database serve para criar e consultar o banco de dados.

import os
import sqlite3
from contextlib import closing

CAMINHO_PADRAO = os.path.join("banco_de_dados", "banco.db")


def caminho_banco():
    # Lido a cada chamada para poder ser trocado por variável de ambiente (e nos testes).
    return os.getenv("DATABASE_PATH", CAMINHO_PADRAO)


def conectar():
    caminho = caminho_banco()
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    conexao = sqlite3.connect(caminho, timeout=10)
    conexao.row_factory = sqlite3.Row  # permite acessar colunas pelo nome
    return conexao


def criar_tabela():
    with closing(conectar()) as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS leituras_metereologicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                temperatura REAL NOT NULL,
                umidade REAL NOT NULL,
                data_hora TEXT NOT NULL,
                adafruit_id TEXT NOT NULL UNIQUE
            )
        """)
        # Índice em data_hora: deixa o ORDER BY ... DESC rápido mesmo com muitas leituras.
        conexao.execute("""
            CREATE INDEX IF NOT EXISTS idx_leituras_data_hora
            ON leituras_metereologicas (data_hora)
        """)
        conexao.commit()


def inserir_leituras(leituras):
    """Insere uma lista de leituras (dicionários) e devolve quantas eram novas.

    O campo adafruit_id é UNIQUE, então leituras que já estão no banco
    são ignoradas e nunca duplicam.
    """
    with closing(conectar()) as conexao:
        antes = conexao.total_changes
        conexao.executemany(
            """
            INSERT OR IGNORE INTO leituras_metereologicas
                (temperatura, umidade, data_hora, adafruit_id)
            VALUES (?, ?, ?, ?)
            """,
            [
                (l["temperatura"], l["umidade"], l["data_hora"], l["adafruit_id"])
                for l in leituras
            ],
        )
        conexao.commit()
        return conexao.total_changes - antes


def consultar_leituras(limite=None, deslocamento=0):
    """Devolve as leituras da mais recente para a mais antiga."""
    sql = """
        SELECT id, temperatura, umidade, data_hora
        FROM leituras_metereologicas
        ORDER BY data_hora DESC
    """
    parametros = []
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        parametros = [limite, deslocamento]

    with closing(conectar()) as conexao:
        return [dict(linha) for linha in conexao.execute(sql, parametros).fetchall()]


def agregados_por_dia():
    """Calcula contagem, somas, mínimos e máximos por dia direto no SQL.

    Assim o banco faz a conta e a API não precisa carregar todas as leituras
    na memória. A soma dos quadrados serve para calcular o desvio padrão depois.
    """
    sql = """
        SELECT
            substr(data_hora, 1, 10)       AS dia,
            COUNT(*)                       AS n,
            SUM(temperatura)               AS soma_t,
            SUM(temperatura * temperatura) AS quad_t,
            MIN(temperatura)               AS min_t,
            MAX(temperatura)               AS max_t,
            SUM(umidade)                   AS soma_u,
            SUM(umidade * umidade)         AS quad_u,
            MIN(umidade)                   AS min_u,
            MAX(umidade)                   AS max_u
        FROM leituras_metereologicas
        GROUP BY dia
        ORDER BY dia
    """
    with closing(conectar()) as conexao:
        return [dict(linha) for linha in conexao.execute(sql).fetchall()]
