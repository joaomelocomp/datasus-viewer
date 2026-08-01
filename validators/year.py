def validar_ano (year: int):
    if year < 1999 or year > 2024:
        raise ValueError("Ano inválido")

    else:
        return year