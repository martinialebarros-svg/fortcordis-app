# Funções utilitárias (texto, normalização) usadas por db e outras partes do app
import re
import unicodedata

def _clean_spaces(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

_PREPS = {"da", "de", "do", "das", "dos", "e"}

def nome_proprio_ptbr(s: str) -> str:
    """Converte 'JOAO DA SILVA' -> 'Joao da Silva'; mantém preposições em minúsculo."""
    s = _clean_spaces(s)
    if not s:
        return s
    def _cap_token(tok: str) -> str:
        if not tok:
            return tok
        if tok.isalpha() and tok.upper() == tok and len(tok) <= 4:
            return tok
        tl = tok.lower()
        if "-" in tl:
            partes = tl.split("-")
            partes = [(p[:1].upper() + p[1:]) if p else p for p in partes]
            return "-".join(partes)
        return tl[:1].upper() + tl[1:]
    palavras = s.split(" ")
    out = []
    for i, p in enumerate(palavras):
        pl = p.lower()
        if i > 0 and pl in _PREPS:
            out.append(pl)
        else:
            out.append(_cap_token(p))
    return " ".join(out)

def _norm_key(s: str) -> str:
    """Normaliza texto para chave (minúsculo, sem acentos, espaços colapsados)."""
    s = (s or "").strip().lower()
    s = " ".join(s.split())
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s
