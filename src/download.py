from pathlib import Path
from ftplib import FTP
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class SystemConfig:
    directory: str
    filename_fn: Callable[[str, int, int], str]  # (uf, year, month) -> filename

def _monthly(prefix: str) -> Callable[[str, int, int], str]:
    return lambda uf, year, month: f"{prefix}{uf.upper()}{str(year)[2:]}{month:02}.dbc"

def _annual(prefix: str) -> Callable[[str, int, int], str]:
    return lambda uf, year, month: f"{prefix}{uf.upper()}{year}.dbc"  # month ignorado

SYSTEMS: dict[str, SystemConfig] = {
    "SIH": SystemConfig("/dissemin/publicos/SIHSUS/200801_/Dados", _monthly("RD")),
    "SIA": SystemConfig("/dissemin/publicos/SIASUS/200801_/Dados", _monthly("PA")),
    "SIM": SystemConfig("/dissemin/publicos/SIM/CID10/DORES", _annual("DO")),
    "SINASC": SystemConfig("/dissemin/publicos/SINASC/NOV/DNRES", _annual("DN")),
    # CNES tem subgrupos — trate como sistemas próprios (ex: "CNES-ST", "CNES-LT")
    "CNES-ST": SystemConfig("/dissemin/publicos/CNES/200508_/Dados/ST", _monthly("ST")),
    "CNES-LT": SystemConfig("/dissemin/publicos/CNES/200508_/Dados/LT", _monthly("LT")),
}

class DataSUSDownloader:
    HOST = "ftp.datasus.gov.br"

    def __init__(self, system: str):
        if system not in SYSTEMS:
            raise ValueError(f"Sistema não suportado: {system}. Opções: {list(SYSTEMS)}")
        self.config = SYSTEMS[system]
        self.raw_dir = Path("data/raw") / system
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def build_filename(self, uf: str, year: int, month: int) -> str:
        return self.config.filename_fn(uf, year, month)

    def download(self, uf: str, year: int, month: int) -> Path:
        filename = self.build_filename(uf, year, month)
        destination = self.raw_dir / filename

        with FTP(self.HOST) as ftp:
            ftp.login()
            ftp.cwd(self.config.directory)
            print(f"Baixando {filename}...")
            with open(destination, "wb") as f:
                ftp.retrbinary(f"RETR {filename}", f.write)

        return destination