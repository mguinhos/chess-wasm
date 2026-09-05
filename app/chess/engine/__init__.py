# `canvas` depende do navegador (js, pyodide), então fica de fora: quem precisa
# dele importa `chess.engine.canvas` diretamente. Assim a lógica de xadrez
# continua importável em Python comum, inclusive nos testes.
from . import coordinates

__all__ = [
    "coordinates"
]
