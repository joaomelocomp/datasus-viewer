"""
Leitor de arquivos DataSUS (DBC/DBF) - versao otimizada para baixo consumo de RAM.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import gc
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

    _IDADE_FATOR = {1: 1 / 24 / 365, 2: 1 / 365, 3: 1 / 12, 4: 1, 5: 100}

    # Colunas conhecidas com dtype fixo. Tudo que nao esta aqui passa pelo
    # downcast automatico em _optimize_dtypes (categoria ou numerico menor).
    _DTYPE_HINTS = {
        "SEXO": "Int8",
        "IDADE": "Int16",
    }

    # Cardinalidade maxima (fracao de linhas unicas) para virar 'category'.
    # Colunas como UF, CID, MUNIC_RES tem poucos valores repetidos -> category
    # economiza muito. Colunas quase-unicas (ex. um ID) NAO viram category
    # (categoria com alta cardinalidade custa mais RAM que string comum).
    _CATEGORY_THRESHOLD = 0.5

    def read(
        self,
        filepath: str | Path,
        decode: bool = True,
        **kwargs,
    ) -> pd.DataFrame:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

        ext = path.suffix.lower()
        handler_name = self.READERS.get(ext)
        if handler_name is None:
            raise ValueError(f"Extensao nao suportada: {ext}")

        df = getattr(self, handler_name)(path, **kwargs)
        df = self._decode_known_fields(df) if decode else df
        df = self._optimize_dtypes(df)
        gc.collect()
        return df

    def _decode_known_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        if "IDADE" in df.columns:
            idade = pd.to_numeric(df["IDADE"], errors="coerce")
            unidade = (idade // 100).astype("Int64")
            valor = idade % 100
            df["IDADE"] = (valor * unidade.map(self._IDADE_FATOR)).astype("float32")
            del idade, unidade, valor
        if "SEXO" in df.columns:
            df["SEXO"] = (
                df["SEXO"].map({1: "Masculino", 3: "Feminino"})
                .fillna("Ignorado")
                .astype("category")
            )
        return df

    def _optimize_dtypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Downcast generico e seguro, aplicado a QUALQUER coluna nao tratada
        manualmente acima. Nao remove nem renomeia nada -- so troca a
        representacao interna:
          - object/string com baixa cardinalidade -> category
          - colunas numericas -> menor int/float que caiba nos valores
        Isso preserva 100% dos valores e nomes de coluna (importante pq
        /api/chart referencia colunas por nome dinamicamente).
        """
        n = len(df)
        if n == 0:
            return df

        for col in df.columns:
            if col in self._DTYPE_HINTS or col in ("IDADE", "SEXO"):
                continue  # ja tratado

            s = df[col]
            dtype_str = str(s.dtype)

            if dtype_str in ("object", "string"):
                nunique = s.nunique(dropna=True)
                if nunique / n < self._CATEGORY_THRESHOLD:
                    df[col] = s.astype("category")
                # senao mantem como esta (alta cardinalidade -> category custaria mais)

            elif dtype_str.startswith(("int", "Int")):
                df[col] = pd.to_numeric(s, downcast="integer")

            elif dtype_str.startswith(("float", "Float")):
                df[col] = pd.to_numeric(s, downcast="float")

        return df

    def _read_dbc(
        self, path: Path, encoding: str = "iso-8859-1", **kwargs
    ) -> pd.DataFrame:
        if dbc2dbf is None:
            raise ImportError("pyreaddbc nao instalado: pip install pyreaddbc")

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            dbf_path = Path(tmp) / (path.stem + ".dbf")
            dbc2dbf(str(path), str(dbf_path))
            # .dbf descompactado (pode ser 10-20x o tamanho do .dbc) fica
            # so no disco temporario e e apagado ao sair do 'with'.
            return self._read_dbf(dbf_path, encoding=encoding)

    def _read_dbf(
        self, path: Path, encoding: str = "iso-8859-1", **kwargs
    ) -> pd.DataFrame:
        from dbfread import DBF

        # load=False: dbfread NAO materializa list[OrderedDict] inteira em
        # RAM. Ele vira um iterador que le/decodifica 1 registro por vez.
        # Isso elimina a duplicacao "lista de dicts + DataFrame" que existia
        # com load=True + pd.DataFrame(iter(table)).
        table = DBF(str(path), encoding=encoding, load=False)
        field_names = table.field_names

        # Acumulacao colunar (dict de listas) em vez de lista de dicts:
        # o padrao de acesso por coluna facilita o downcast por coluna logo
        # depois, sem precisar reconstruir o DataFrame inteiro.
        cols: dict[str, list] = {name: [] for name in field_names}
        for record in table:
            for name in field_names:
                cols[name].append(record.get(name))

        data = {}
        for name in field_names:
            raw = cols.pop(name)
            dtype = self._DTYPE_HINTS.get(name)
            data[name] = pd.array(raw, dtype=dtype) if dtype else pd.array(raw, dtype="string")
            del raw

        df = pd.DataFrame(data)
        del data, cols
        return df

    def _read_csv(self, path: Path, **kwargs) -> pd.DataFrame:
        kwargs.setdefault("encoding", "iso-8859-1")
        kwargs.setdefault("sep", ";")
        return pd.read_csv(path, **kwargs)

    def _read_parquet(self, path: Path, **kwargs) -> pd.DataFrame:
        return pd.read_parquet(path, **kwargs)