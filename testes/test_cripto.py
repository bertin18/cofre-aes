import hashlib
from secrets import token_urlsafe, token_bytes

import pytest

from app import cripto


def test_pbkdf2_confere_com_implementacao_independente():
    senha = token_urlsafe(24) + "ç漢"
    sal = cripto.gerar_sal()
    esperado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, 210000, 32)
    assert cripto.derivar_chave(senha, sal, 210000) == esperado
    assert cripto.derivar_chave(senha, cripto.gerar_sal(), 210000) != esperado


def test_roundtrip_unicode_e_aad():
    chave = token_bytes(32)
    texto = token_urlsafe(24) + " á漢🔒"
    dados = cripto.cifrar(chave, texto, b"cofre|segredo")
    assert cripto.decifrar(chave, *dados, b"cofre|segredo") == texto
    for chave_errada, aad in [(token_bytes(32), b"cofre|segredo"), (chave, b"outro|segredo")]:
        with pytest.raises(ValueError):
            cripto.decifrar(chave_errada, *dados, aad)


def test_verificador_vinculado_ao_cofre():
    chave = token_bytes(32)
    dados = cripto.criar_verificador(chave, "cofre-a")
    assert cripto.senha_mestra_correta(chave, *dados, "cofre-a")
    assert not cripto.senha_mestra_correta(chave, *dados, "cofre-b")
    assert not cripto.senha_mestra_correta(token_bytes(32), *dados, "cofre-a")


@pytest.mark.parametrize("iteracoes", [1, 209999, 2000001, "210000"])
def test_parametros_kdf_invalidos(iteracoes):
    with pytest.raises(ValueError):
        cripto.derivar_chave(token_urlsafe(24), cripto.gerar_sal(), iteracoes)


def test_sal_e_chave_com_tamanho_invalido():
    with pytest.raises(ValueError):
        cripto.derivar_chave(token_urlsafe(24), token_bytes(8), 210000)
    with pytest.raises(ValueError):
        cripto.cifrar(token_bytes(16), token_urlsafe(24), b"contexto")
