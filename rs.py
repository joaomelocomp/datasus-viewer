import streamlit as st
from src.download import DataSUSDownloader
from reader import *
from src.download import SYSTEMS
import plotly.express as px
from validators.uf import validar_uf
from validators.year import validar_ano
from pathlib import Path

PASTA = Path("downloads")

arquivos = list(PASTA.glob("*.dbc"))

#python -m streamlit run app.py

st.title("Busca de dados")

ufs = [
    "AC","AL","AP","AM","BA","CE","DF","ES",
    "GO","MA","MT","MS","MG","PA","PB","PR",
    "PE","PI","RJ","RN","RS","RO","RR","SC",
    "SP","SE","TO",
]

col1, col2, col3 = st.columns(3)
uf = col1.selectbox("UF", options=ufs, index=ufs.index("RJ"))
year = col2.number_input("Ano", value=2024, step=1)
month = col3.number_input("Mês", value=1, min_value=1, max_value=12, step=1)

tipo_dado = st.selectbox("Selecione o sistema", options=list(SYSTEMS.keys()))

import pandas as pd
from datetime import datetime

st.subheader("Dados baixados")

arquivos = sorted(PASTA.glob("*.dbc"), key=lambda p: p.stat().st_mtime, reverse=True)

if not arquivos:
    st.info("Nenhum arquivo baixado ainda.")
else:
    registros = [
        {
            "Excluir": False,
            "Arquivo": a.name,
            "Tamanho (MB)": round(a.stat().st_size / 1_048_576, 2),
            "Modificado": datetime.fromtimestamp(a.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
        }
        for a in arquivos
    ]
    df_arquivos = pd.DataFrame(registros)

    edited = st.data_editor(
        df_arquivos,
        column_config={
            "Excluir": st.column_config.CheckboxColumn(required=True),
            "Arquivo": st.column_config.TextColumn(disabled=True),
            "Tamanho (MB)": st.column_config.NumberColumn(disabled=True),
            "Modificado": st.column_config.TextColumn(disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        key="editor_arquivos",
    )

    selecionados = edited[edited["Excluir"]]["Arquivo"].tolist()

    col_a, col_b = st.columns([1, 3])

    with col_a:
        if st.button("Abrir selecionado", disabled=len(selecionados) != 1):
            st.session_state["df"] = DataSUSReader().read(PASTA / selecionados[0])
            st.success(f"{selecionados[0]} carregado.")

    with col_b:
        if selecionados:
            if st.session_state.get("confirmar_exclusao") != tuple(selecionados):
                if st.button(f"Excluir {len(selecionados)} arquivo(s)", type="primary"):
                    st.session_state["confirmar_exclusao"] = tuple(selecionados)
                    st.rerun()
            else:
                st.warning(f"Confirma exclusão de: {', '.join(selecionados)}?")
                c1, c2 = st.columns(2)
                if c1.button("Sim, excluir", type="primary"):
                    for nome in selecionados:
                        (PASTA / nome).unlink(missing_ok=True)
                    del st.session_state["confirmar_exclusao"]
                    st.success("Arquivo(s) excluído(s).")
                    st.rerun()
                if c2.button("Cancelar"):
                    del st.session_state["confirmar_exclusao"]
                    st.rerun()

if st.button("Baixar e carregar"):
    try:
        uf = validar_uf(uf)
        year = validar_ano(year)
        downloader = DataSUSDownloader(system=tipo_dado)
        arquivo = downloader.download(uf=uf, year=year, month=month)
        st.session_state["df"] = DataSUSReader().read(arquivo)
        st.success(f"Arquivo salvo em: {arquivo}")
        st.rerun()

    except ValueError as e:
        st.error(e)

if "df" in st.session_state:
    df = st.session_state["df"]
    st.write(f"Registros: {len(df)} | Colunas: {len(df.columns)}")

    tipo_grafico = st.selectbox("Tipo de gráfico", ["Barras", "Pizza", "Dispersão", "Histograma"])
    coluna_alvo = st.selectbox("Escolha a coluna para plotar", df.columns)
    top_n = st.slider("Quantidade de categorias exibidas", 5, 30, 15)

    if tipo_grafico in ("Barras", "Pizza"):
        counts = df[coluna_alvo].value_counts(dropna=True).head(top_n).reset_index()
        counts.columns = [coluna_alvo, "count"]

        if tipo_grafico == "Barras":
            fig = px.bar(counts, x=coluna_alvo, y="count")
        else:
            fig = px.pie(counts, names=coluna_alvo, values="count")

    elif tipo_grafico == "Dispersão":
        col_x = st.selectbox("Eixo X", df.columns, key="x")
        col_y = st.selectbox("Eixo Y", df.columns, key="y")
        cor = st.selectbox("Colorir por (opcional)", [None] + list(df.columns), key="cor")
        fig = px.scatter(df, x=col_x, y=col_y, color=cor)

    elif tipo_grafico == "Histograma":
        fig = px.histogram(df, x=coluna_alvo, nbins=30)

    st.plotly_chart(fig, use_container_width=True)
