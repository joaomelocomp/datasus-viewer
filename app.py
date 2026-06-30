from src.download import DataSUSDownloader

downloader = DataSUSDownloader()

arquivo = downloader.download(
    uf="SP",
    year=2024,
    month=1
)

print(f"Arquivo salvo em: {arquivo}")