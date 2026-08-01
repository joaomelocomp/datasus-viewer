UFS = {
    "AC","AL","AP","AM","BA","CE","DF","ES",
    "GO","MA","MT","MS","MG","PA","PB","PR",
    "PE","PI","RJ","RN","RS","RO","RR","SC",
    "SP","SE","TO"
}

def validar_uf (uf: str) -> str:
    uf = uf.strip().upper()

    if uf not in UFS:
        raise ValueError("UF inválida")

    return uf