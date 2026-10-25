# API da Estação Meteorológica

API em FastAPI que lê as leituras de temperatura e umidade do Adafruit IO, guarda em SQLite
e expõe tudo para o dashboard.

## Rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload
```

Abra http://127.0.0.1:8000/docs para ver o Swagger.

## Rotas

| Método | Rota                    | O que faz                                              |
|--------|-------------------------|--------------------------------------------------------|
| GET    | `/`                     | Mensagem de boas-vindas                                |
| GET    | `/saude`                | Verifica se a API está de pé                           |
| GET    | `/leituras`             | Lista leituras (`?limite=` até 5000, `?deslocamento=`) |
| GET    | `/leituras/ultima`      | Leitura mais recente                                   |
| GET    | `/estatisticas`         | Média, desvio padrão, mínimo e máximo gerais           |
| GET    | `/estatisticas/diarias` | As mesmas estatísticas, dia a dia                      |
| POST   | `/sincronizar`          | Força sincronização (exige cabeçalho `X-Token`)        |

A API também sincroniza sozinha ao ligar e a cada 5 minutos.

## Variáveis de ambiente (todas opcionais)

| Variável                | Para quê                                                      |
|-------------------------|---------------------------------------------------------------|
| `SYNC_TOKEN`            | Senha do `POST /sincronizar`. Sem ela, a rota fica desativada |
| `CORS_ORIGINS`          | Sites autorizados, separados por vírgula (padrão `*`)         |
| `SYNC_INTERVAL_MINUTES` | Intervalo da sincronização automática (`0` = só ao ligar)     |
| `ADAFRUIT_FEED_URL`     | Troca o feed do Adafruit sem mexer no código                  |
| `DATABASE_PATH`         | Caminho do arquivo SQLite                                     |

## Deploy no Render

1. Suba o código no GitHub.
2. No Render: **New → Blueprint** e escolha o repositório (ele lê o `render.yaml`).
   Ou crie um **Web Service** manualmente com:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Mande para sua amiga o link terminado em **`/docs`** (ex.: `https://seu-app.onrender.com/docs`).

Observações do plano gratuito: o serviço dorme após 15 minutos sem acesso (a primeira
visita depois disso demora cerca de 1 minuto) e o disco é apagado a cada reinício.
Ao acordar, a API recarrega do Adafruit os últimos 1000 registros.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```
