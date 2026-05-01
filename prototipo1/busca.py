import pandas as pd
import streamlit as st
import plotly.express as px

df = pd.read_csv(r"C:\Users\melo\Desktop\Arquivos e Programas 4.0\PROG\datasus-viewer\prototipo1\data\paraanalisar.csv", sep=';', encoding='latin1',
skiprows = 4)

df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

st.header("Internações Hospitalares (Referência: 2023)")

sexo = st.selectbox("Selecione o sexo:", df['Sexo'].unique())

df_filtrado = df[df['Sexo'] == sexo]

contagem = df_filtrado['Município'].value_counts().head(10)

fig = px.bar(
    contagem,
    x=contagem.values,
    y=contagem.index,
    orientation='h',
    title="Top 10 Municípios com mais internações"
)

st.plotly_chart(fig)

fig2 = px.histogram(df_filtrado, x='Idade', nbins=20, title="Distribuição de Idade")
st.plotly_chart(fig2)