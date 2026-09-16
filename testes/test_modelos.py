from secrets import token_urlsafe

import pytest
from pydantic import ValidationError

from app.modelos import AtualizarSegredo, NovoCofre, NovoSegredo


@pytest.mark.parametrize("modelo,campo,limite,outros", [
    (NovoCofre, "senha_mestra", 1024, {"nome": "Teste"}),
    (NovoSegredo, "senha", 10000, {"titulo": "Teste"}),
    (AtualizarSegredo, "senha", 10000, {}),
])
@pytest.mark.parametrize("caso", ["vazia", "minima", "maxima", "excede"])
def test_limites_e_mascaramento_de_senha(modelo, campo, limite, outros, caso):
    tamanho = {"vazia": 0, "minima": 1, "maxima": limite, "excede": limite + 1}[caso]
    senha = token_urlsafe(tamanho + 1)[:tamanho]
    if caso in ("vazia", "excede"):
        with pytest.raises(ValidationError):
            modelo(**outros, **{campo: senha})
    else:
        instancia = modelo(**outros, **{campo: senha})
        assert len(getattr(instancia, campo).get_secret_value()) == tamanho
        assert instancia.model_dump(mode="json")[campo] == "**********"
