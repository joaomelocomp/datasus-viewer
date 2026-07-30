from src.download import DataSUSDownloader
from reader import *

downloader = DataSUSDownloader()

arquivo = downloader.download(
    uf=input("Digite o UF ").upper(),
    year=int(input("Digite o ano ")),
    month=int(input("Digite o mês "))
)

print(f"Arquivo salvo em: {arquivo}")

reader = DataSUSReader()
df = reader.read(arquivo)

print(f"Registros: {len(df)} | Colunas: {list(df.columns)}")
print(df.head())