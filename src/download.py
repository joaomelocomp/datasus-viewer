from pathlib import Path
from ftplib import FTP

class DataSUSDownloader:

    HOST = "ftp.datasus.gov.br"
    DIRECTORY = "/dissemin/publicos/SIHSUS/200801_/Dados"

    def __init__(self):
        self.raw_dir = Path("data/raw")
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def build_filename(self, uf: str, year: int, month: int):
        yy = str(year)[2:]
        mm = f"{month:02}"
        return f"RD{uf.upper()}{yy}{mm}.dbc"
    
    def download(self, uf: str, year: int, month: int):

        filename = self.build_filename(uf, year, month)
        destination = self.raw_dir / filename

        ftp = FTP(self.HOST)
        ftp.login()
        ftp.cwd(self.DIRECTORY)

        print(f"Baixando {filename}...")

        with open(destination, "wb") as f:
            ftp.retrbinary(f"RETR {filename}", f.write)

        ftp.quit()

        return destination