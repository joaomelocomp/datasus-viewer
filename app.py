import json
import uuid
from datetime import datetime
from pathlib import Path

import plotly.express as px
import plotly.utils
from flask import Flask, jsonify, render_template, request, session

from src.download import DataSUSDownloader, SYSTEMS
from reader import DataSUSReader
from stats import calcular_estatisticas
from validators.uf import validar_uf
from validators.year import validar_ano

app = Flask(__name__)
app.secret_key = "change-me-in-production"  # required for session cookies

PASTA = Path(__file__).resolve().parent / "data" / "raw"
PASTA.mkdir(exist_ok=True)

UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES",
    "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
    "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]

SYSTEM_DESCRIPTIONS = {
    "SIH": "Internações Hospitalares",
    "SIA": "Atendimentos Ambulatoriais",
    "SIM": "Óbitos",
    "SINASC": "Nascimentos",
    "CNES-ST": "Estabelecimentos de Saúde",
    "CNES-LT": "Leitos Hospitalares",
}

# In-memory per-session dataframe store: {session_id: DataFrame}
# NOTE: single-process only. For multi-worker/production deployments,
# swap this for a shared cache (Redis, etc.) keyed the same way.
DF_STORE: dict = {}


def _sid() -> str:
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    return session["sid"]


def _get_df():
    return DF_STORE.get(_sid())


def _set_df(df):
    DF_STORE[_sid()] = df


def _list_files():
    arquivos = sorted(
        PASTA.rglob("*.dbc"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    return [
        {
            "name": a.name,
            "size_mb": round(a.stat().st_size / 1_048_576, 2),
            "modified": datetime.fromtimestamp(
                a.stat().st_mtime
            ).strftime("%d/%m/%Y %H:%M"),
        }
        for a in arquivos
    ]


def _df_payload(df):
    return {
        "rows": len(df),
        "cols": len(df.columns),
        "columns": list(df.columns),
        "stats": calcular_estatisticas(df),
    }


@app.route("/")
def index():
    df = _get_df()
    return render_template(
        "index.html",
        ufs=UFS,
        default_uf="RJ",
        systems=SYSTEM_DESCRIPTIONS,
        files=_list_files(),
        df_loaded=df is not None,
        df_info=_df_payload(df) if df is not None else None,
    )


@app.get("/api/files")
def api_files():
    return jsonify(files=_list_files())


@app.post("/api/files/delete")
def api_files_delete():
    nomes = request.json.get("files", [])
    for nome in nomes:
        (PASTA / nome).unlink(missing_ok=True)
    return jsonify(files=_list_files())


@app.post("/api/files/open")
def api_files_open():
    nome = request.json.get("file")
    caminho = PASTA / nome
    if not caminho.exists():
        return jsonify(error=f"Arquivo não encontrado: {nome}"), 404
    df = DataSUSReader().read(caminho)
    _set_df(df)
    return jsonify(**_df_payload(df))


@app.post("/api/download")
def api_download():
    body = request.json

    try:
        print("1. Recebendo requisição:", body, flush=True)

        uf = validar_uf(body.get("uf"))
        year = validar_ano(int(body.get("year")))
        month = int(body.get("month"))
        system = body.get("system")

        print(f"2. Parâmetros: {uf=} {year=} {month=} {system=}", flush=True)

        downloader = DataSUSDownloader(system=system)

        print("3. Iniciando download...", flush=True)

        arquivo = downloader.download(
            uf=uf,
            year=year,
            month=month
        )

        print(f"4. Download concluído: {arquivo}", flush=True)

        df = DataSUSReader().read(arquivo)

        print(f"5. Arquivo lido: {df.shape}", flush=True)

        _set_df(df)

        print("6. Tudo pronto!", flush=True)

        return jsonify(
            path=str(arquivo),
            files=_list_files(),
            **_df_payload(df)
        )

    except ValueError as e:
        print("ERRO ValueError:", e, flush=True)
        return jsonify(error=str(e)), 400

    except Exception as e:
        import traceback

        print("ERRO REAL:", flush=True)
        traceback.print_exc()

        return jsonify(error=str(e)), 500

@app.post("/api/chart")
def api_chart():
    df = _get_df()
    if df is None:
        return jsonify(error="Nenhum dado carregado."), 400

    body = request.json
    chart_type = body.get("chart_type")
    column = body.get("column")
    top_n = int(body.get("top_n", 15))

    try:
        if chart_type in ("Barras", "Pizza"):
            counts = df[column].value_counts(dropna=True).head(top_n).reset_index()
            counts.columns = [column, "count"]
            fig = (
                px.bar(counts, x=column, y="count")
                if chart_type == "Barras"
                else px.pie(counts, names=column, values="count")
            )
        elif chart_type == "Dispersão":
            col_x = body.get("x")
            col_y = body.get("y")
            cor = body.get("color") or None
            fig = px.scatter(df, x=col_x, y=col_y, color=cor)
        elif chart_type == "Histograma":
            fig = px.histogram(df, x=column, nbins=30)
        else:
            return jsonify(error=f"Tipo de gráfico inválido: {chart_type}"), 400
    except Exception as e:
        return jsonify(error=str(e)), 400

    fig_json = json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    return jsonify(figure=fig_json)


import os

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )