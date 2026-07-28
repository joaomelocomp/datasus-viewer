"""
Leitor de arquivos DataSUS (DBC/DBF) baixados via DataSUSDownloader.
"""
from pathlib import Path
import pandas as pd

try:
    from pyreaddbc import dbc2dbf
except ImportError:
    dbc2dbf = None  # pip install pyreaddbc


class DataSUSReader:
    """Le arquivos .dbc/.dbf/.csv/.parquet resultantes do download."""

    READERS = {
        ".dbc": "_read_dbc",
        ".dbf": "_read_dbf",
        ".csv": "_read_csv",
        ".parquet": "_read_parquet",
    }

    def read(self, filepath: str | Path, **kwargs) -> pd.DataFrame:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

        ext = path.suffix.lower()
        handler_name = self.READERS.get(ext)
        if handler_name is None:
            raise ValueError(f"Extensao nao suportada: {ext}")

        return getattr(self, handler_name)(path, **kwargs)

    def _read_dbc(self, path: Path, encoding: str = "iso-8859-1") -> pd.DataFrame:
        if dbc2dbf is None:
            raise ImportError("pyreaddbc nao instalado: pip install pyreaddbc")

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dbf_path = Path(tmp) / (path.stem + ".dbf")
            dbc2dbf(str(path), str(dbf_path))
            return self._read_dbf(dbf_path, encoding=encoding)

    def _read_dbf(self, path: Path, encoding: str = "iso-8859-1") -> pd.DataFrame:
        from dbfread import DBF  # pip install dbfread
        table = DBF(str(path), encoding=encoding, load=True)
        return pd.DataFrame(iter(table))

    def _read_csv(self, path: Path, **kwargs) -> pd.DataFrame:
        kwargs.setdefault("encoding", "iso-8859-1")
        kwargs.setdefault("sep", ";")
        return pd.read_csv(path, **kwargs)

    def _read_parquet(self, path: Path, **kwargs) -> pd.DataFrame:
        return pd.read_parquet(path, **kwargs)


if __name__ == "__main__":
    from src.download import DataSUSDownloader

    downloader = DataSUSDownloader()
    arquivo = downloader.download(uf="SP", year=2024, month=1)

    reader = DataSUSReader()
    df = reader.read(arquivo)

    print(f"Registros: {len(df)} | Colunas: {list(df.columns)}")
    print(df.head())