"""
Calculo das "Estatisticas rapidas" do dashboard.

Opera apenas sobre o DataFrame ja carregado (nao mexe em download/leitura).
Como cada sistema do DATASUS (SIH, SIA, SIM, SINASC, CNES...) usa nomes de
coluna diferentes, nada aqui assume um layout fixo: cada metrica tenta
localizar uma coluna adequada e cai para "N/D" se nao encontrar nada
confiavel, em vez de quebrar ou inventar um numero.
"""
from __future__ import annotations

import pandas as pd

# Candidatos conhecidos de coluna de municipio, em ordem de prioridade,
# cobrindo os layouts mais comuns do DATASUS:
#   SIH (RD)      -> MUNIC_RES / MUNIC_MOV
#   SIA (PA)      -> PA_MUNPCN / PA_UFMUN
#   SIM/SINASC    -> CODMUNRES
#   CNES (ST/LT)  -> CODUFMUN
_MUNICIPIO_CANDIDATOS = [
    "MUNIC_RES", "MUNIC_MOV", "CODMUNRES", "MUNRES",
    "PA_MUNPCN", "PA_UFMUN", "CODUFMUN", "MUNICIPIO",
]

# Fallback (so usado se nenhum candidato acima existir): qualquer coluna
# contendo "MUN" no nome.
_MUNICIPIO_SUBSTR = "MUN"

# Identificador de internacao/AIH -- relevante principalmente para o SIH.
# Outros sistemas (SIA, SIM, SINASC, CNES) nao tem esse conceito, entao a
# metrica so e calculada quando essa coluna existe.
_INTERNACAO_SUBSTR = "AIH"

# A coluna de idade so e aceita por igualdade EXATA (case-insensitive).
# Substrings como "IDADEMAE" existem em outros sistemas (ex: SINASC) e
# representam algo semanticamente diferente (idade da mae, nao a idade do
# registro/paciente), entao usar "contains" aqui seria enganoso.
_IDADE_NOME = "IDADE"

# Faixa plausivel de idade em anos, usada so para descartar outliers
# grosseiros que poderiam distorcer a media (ex: erro de decodificacao).
_IDADE_MIN, _IDADE_MAX = 0, 130


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """Retorna o primeiro nome de coluna real que bate (case-insensitive)
    com algum candidato da lista, na ordem de prioridade informada."""
    upper_map = {c.upper(): c for c in df.columns}
    for cand in candidates:
        if cand in upper_map:
            return upper_map[cand]
    return None


def _find_column_contains(df: pd.DataFrame, substr: str) -> str | None:
    for c in df.columns:
        if substr in str(c).upper():
            return c
    return None


def _fmt_int_ptbr(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _fmt_float_ptbr(x: float, decimals: int = 1) -> str:
    s = f"{x:,.{decimals}f}"
    # troca separadores: "," (milhar) -> "." e "." (decimal) -> ","
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _na() -> dict:
    return {"value": None, "display": "N/D"}


def calcular_estatisticas(df: pd.DataFrame) -> dict:
    """
    Calcula as 4 metricas de "Estatisticas rapidas" a partir do DataFrame
    ja carregado. Cada metrica retorna {"value": ..., "display": "..."};
    quando nao e possivel calcular com confianca, value=None e
    display="N/D" -- nunca lanca excecao por causa de uma metrica ausente.
    """
    if df is None or len(df.columns) == 0:
        return {
            "registros": _na(),
            "municipios": _na(),
            "internacoes": _na(),
            "media_idade": _na(),
        }

    stats: dict = {}

    # 1. Registros -- sempre disponivel, e o proprio tamanho do DataFrame.
    registros = len(df)
    stats["registros"] = {"value": registros, "display": _fmt_int_ptbr(registros)}

    # 2. Municipios
    col_mun = _find_column(df, _MUNICIPIO_CANDIDATOS) or _find_column_contains(df, _MUNICIPIO_SUBSTR)
    if col_mun is not None:
        n_mun = int(df[col_mun].dropna().nunique())
        stats["municipios"] = {"value": n_mun, "display": _fmt_int_ptbr(n_mun)}
    else:
        stats["municipios"] = _na()

    # 3. Internacoes -- so calculada se houver identificador de AIH, pois
    # "1 linha = 1 internacao" nao vale para todos os sistemas.
    col_aih = _find_column_contains(df, _INTERNACAO_SUBSTR)
    if col_aih is not None:
        n_aih = int(df[col_aih].dropna().nunique())
        stats["internacoes"] = {"value": n_aih, "display": _fmt_int_ptbr(n_aih)}
    else:
        stats["internacoes"] = _na()

    # 4. Media de idade -- coluna "IDADE" exata (ja decodificada em anos
    # por DataSUSReader._decode_known_fields quando presente).
    col_idade = _find_column(df, [_IDADE_NOME])
    if col_idade is not None:
        idade_num = pd.to_numeric(df[col_idade], errors="coerce").dropna()
        idade_num = idade_num[(idade_num >= _IDADE_MIN) & (idade_num <= _IDADE_MAX)]
        if len(idade_num):
            media = float(idade_num.mean())
            stats["media_idade"] = {"value": media, "display": f"{_fmt_float_ptbr(media)} anos"}
        else:
            stats["media_idade"] = _na()
    else:
        stats["media_idade"] = _na()

    return stats
