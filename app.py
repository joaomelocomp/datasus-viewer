import streamlit as st
from src.download import DataSUSDownloader
from reader import *

st.title("DataSUS Explorer")

col1, col2, col3 = st.columns(3)
uf = col1.text_input("UF", value="RJ").upper()
year = col2.number_input("Ano", value=2024, step=1)
month = col3.number_input("Mês", value=1, min_value=1, max_value=12, step=1)

if st.button("Baixar e carregar"):
    downloader = DataSUSDownloader()
    arquivo = downloader.download(uf=uf, year=year, month=month)
    st.session_state["df"] = DataSUSReader().read(arquivo)
    st.success(f"Arquivo salvo em: {arquivo}")

if "df" in st.session_state:
    df = st.session_state["df"]
    st.write(f"Registros: {len(df)} | Colunas: {len(df.columns)}")

    coluna_alvo = st.selectbox("Escolha a coluna para plotar", df.columns)
    top_n = st.slider("Top N", 5, 30, 15)

    counts = df[coluna_alvo].value_counts(dropna=True).head(top_n)
    st.bar_chart(counts)