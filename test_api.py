import statistics

import pytest
from fastapi.testclient import TestClient

import main

LEITURAS = [
    {"adafruit_id": "a", "temperatura": 20.0, "umidade": 60.0, "data_hora": "2026-10-01T10:00:00-03:00"},
    {"adafruit_id": "b", "temperatura": 24.0, "umidade": 70.0, "data_hora": "2026-10-01T12:00:00-03:00"},
    {"adafruit_id": "c", "temperatura": 28.0, "umidade": 50.0, "data_hora": "2026-10-02T09:00:00-03:00"},
]


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setenv("SYNC_TOKEN", "segredo")
    monkeypatch.setattr(main, "INTERVALO_SYNC_MIN", 0)          # sincroniza só uma vez
    monkeypatch.setattr(main, "buscar_leituras", lambda: LEITURAS)  # sem internet nos testes
    with TestClient(main.app) as c:
        yield c


def test_raiz_e_saude(cliente):
    assert cliente.get("/").json()["documentacao"] == "/docs"
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_swagger_disponivel(cliente):
    assert cliente.get("/docs").status_code == 200
    assert cliente.get("/openapi.json").status_code == 200


def test_leituras_ordenadas_e_limite(cliente):
    dados = cliente.get("/leituras").json()
    assert [l["temperatura"] for l in dados] == [28.0, 24.0, 20.0]  # mais recente primeiro
    assert len(cliente.get("/leituras?limite=2").json()) == 2
    assert cliente.get("/leituras?limite=2&deslocamento=2").json()[0]["temperatura"] == 20.0
    assert cliente.get("/leituras?limite=0").status_code == 422


def test_ultima(cliente):
    assert cliente.get("/leituras/ultima").json()["temperatura"] == 28.0


def test_ultima_sem_dados(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "vazio.db"))
    monkeypatch.setattr(main, "INTERVALO_SYNC_MIN", 0)
    monkeypatch.setattr(main, "buscar_leituras", lambda: [])
    with TestClient(main.app) as c:
        assert c.get("/leituras/ultima").status_code == 404
        geral = c.get("/estatisticas").json()
        assert geral == {"total_leituras": 0, "temperatura": None, "umidade": None}


def test_estatisticas_batem_com_statistics(cliente):
    temps = [l["temperatura"] for l in LEITURAS]
    geral = cliente.get("/estatisticas").json()
    assert geral["total_leituras"] == 3
    assert geral["temperatura"]["media"] == round(statistics.mean(temps), 2)
    assert geral["temperatura"]["desvio_padrao"] == round(statistics.stdev(temps), 2)
    assert geral["temperatura"]["minimo"] == 20.0
    assert geral["umidade"]["maximo"] == 70.0


def test_estatisticas_diarias(cliente):
    dias = cliente.get("/estatisticas/diarias").json()
    assert [d["dia"] for d in dias] == ["2026-10-01", "2026-10-02"]
    assert dias[0]["total_leituras"] == 2
    assert dias[0]["temperatura"]["media"] == 22.0
    assert dias[1]["temperatura"]["desvio_padrao"] == 0.0  # só 1 leitura no dia


def test_sincronizar_exige_token(cliente):
    assert cliente.post("/sincronizar").status_code == 401
    assert cliente.post("/sincronizar", headers={"X-Token": "errado"}).status_code == 401
    ok = cliente.post("/sincronizar", headers={"X-Token": "segredo"})
    assert ok.status_code == 200
    assert ok.json() == {"leituras_no_feed": 3, "novas_leituras": 0}  # já tinham entrado ao ligar


def test_sincronizar_desativado_sem_token_configurado(cliente, monkeypatch):
    monkeypatch.delenv("SYNC_TOKEN")
    assert cliente.post("/sincronizar", headers={"X-Token": "qualquer"}).status_code == 403
