import streamlit as st
from src.download import DataSUSDownloader
from reader import *
from src.download import SYSTEMS
import plotly.express as px
from validators.uf import validar_uf
from validators.year import validar_ano

#python -m streamlit run app.py

st.title("Busca de dados")

col1, col2, col3 = st.columns(3)
uf = col1.text_input("UF", value="RJ").upper()
year = col2.number_input("Ano", value=2024, step=1)
month = col3.number_input("Mês", value=1, min_value=1, max_value=12, step=1)

tipo_dado = st.selectbox("Selecione o sistema", options=list(SYSTEMS.keys()))

if st.button("Baixar e carregar"):
    try:
        uf = validar_uf(uf)
        year = validar_ano(year)
        downloader = DataSUSDownloader(system=tipo_dado)
        arquivo = downloader.download(uf=uf, year=year, month=month)
        st.session_state["df"] = DataSUSReader().read(arquivo)
        st.success(f"Arquivo salvo em: {arquivo}")
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
