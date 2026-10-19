# O arquivo database serve para criar e consultar o banco de dados.
import os
import sqlite3
from contextlib import closing

PASTA_BANCO = "banco_de_dados"
CAMINHO_BANCO = os.path.join(PASTA_BANCO, "banco.db")


def conectar():
    # Garante que a pasta do banco exista antes de abrir a conexão
    os.makedirs(PASTA_BANCO, exist_ok=True)
    return sqlite3.connect(CAMINHO_BANCO)


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


def consultar_leituras(limite=None):
    """Devolve as leituras da mais recente para a mais antiga."""
    sql = """
        SELECT id, temperatura, umidade, data_hora
        FROM leituras_metereologicas
        ORDER BY data_hora DESC
    """
    parametros = ()
    if limite is not None:
        sql += " LIMIT ?"
        parametros = (limite,)

    with closing(conectar()) as conexao:
        linhas = conexao.execute(sql, parametros).fetchall()

    resultado = []
    for linha in linhas:
        resultado.append({
            "id": linha[0],
            "temperatura": linha[1],
            "umidade": linha[2],
            "data_hora": linha[3],
        })
    return resultado