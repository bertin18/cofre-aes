import json
from copy import deepcopy
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from fastapi.exceptions import ResponseValidationError

from app import cripto
from app.banco import BancoNaoConfigurado, ErroBanco, obter_banco
from app.main import app


def test_01_mesma_senha_produz_nonces_distintos(api, banco, cenario):
    c = cenario
    resposta = api.post(c["rota"], headers=c["headers"], json={"titulo": "Segunda", "senha": c["senha"]})
    assert resposta.status_code == 201
    a, b = banco.segredos[c["segredo_id"]], banco.segredos[resposta.json()["id"]]
    assert a["nonce"] != b["nonce"]
    assert a["criptograma"] != b["criptograma"]


def test_02_senha_mestra_incorreta(api, cenario):
    c = cenario
    resposta = api.get(c["item"], headers={"X-Senha-Mestra": token_urlsafe(24)})
    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "senha-mestra incorreta"}
    assert c["senha"] not in resposta.text and c["mestra"] not in resposta.text


def test_03_persistencia_sem_senhas_legiveis(banco, cenario):
    dados = json.dumps([banco.cofres, banco.segredos])
    assert cenario["senha"] not in dados and cenario["mestra"] not in dados
    r = banco.segredos[cenario["segredo_id"]]
    assert "senha" not in r and "chave" not in r
    assert len(cripto.de_b64(r["nonce"])) == 12
    assert len(cripto.de_b64(r["etiqueta"])) == 16
    assert len(cripto.de_b64(r["criptograma"])) == len(cenario["senha"].encode())


@pytest.mark.parametrize("campo", ["criptograma", "etiqueta", "nonce"])
def test_04_adulteracao_recusada(api, banco, cenario, campo):
    registro = banco.segredos[cenario["segredo_id"]]
    dados = bytearray(cripto.de_b64(registro[campo]))
    dados[0] ^= 1
    registro[campo] = cripto.para_b64(bytes(dados))
    resposta = api.get(cenario["item"], headers=cenario["headers"])
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "registro adulterado"}


def test_05_troca_de_criptogramas_recusada(api, banco, cenario):
    c = cenario
    novo = api.post(c["rota"], headers=c["headers"], json={"titulo": "Destino", "senha": token_urlsafe(24)}).json()["id"]
    a, b = banco.segredos[c["segredo_id"]], banco.segredos[novo]
    for campo in ("nonce", "criptograma", "etiqueta"):
        b[campo] = a[campo]
    resposta = api.get(f"{c['rota']}/{novo}", headers=c["headers"])
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "registro adulterado"}


def test_ciclo_completo_e_listagem_sem_campos_cifrados(api, banco, cenario):
    c = cenario
    assert api.post(f"/cofres/{c['cofre_id']}/abrir", headers=c["headers"]).status_code == 200
    resposta = api.get(c["item"], headers=c["headers"])
    assert resposta.status_code == 200 and resposta.json()["senha"] == c["senha"]
    assert resposta.headers["cache-control"] == "no-store"
    listagem = api.get(c["rota"], headers=c["headers"])
    assert listagem.status_code == 200
    assert set(listagem.json()[0]) == {"id", "titulo", "usuario", "url", "criado_em"}
    nonce_anterior = banco.segredos[c["segredo_id"]]["nonce"]
    senha_nova = token_urlsafe(24)
    assert api.put(c["item"], headers=c["headers"], json={"senha": senha_nova}).status_code == 200
    assert nonce_anterior != banco.segredos[c["segredo_id"]]["nonce"]
    assert api.get(c["item"], headers=c["headers"]).json()["senha"] == senha_nova
    assert api.delete(c["item"], headers=c["headers"]).status_code == 200
    assert api.get(c["item"], headers=c["headers"]).status_code == 404
    assert api.delete(c["item"], headers=c["headers"]).status_code == 404


@pytest.mark.parametrize("metodo,colecao", [("get", True), ("post", True), ("get", False), ("put", False), ("delete", False)])
@pytest.mark.parametrize("autenticacao,codigo", [("ausente", 422), ("errada", 401)])
def test_autenticacao_em_todas_as_operacoes(api, banco, cenario, metodo, colecao, autenticacao, codigo):
    c = cenario
    antes = deepcopy(banco.segredos)
    kwargs = {"headers": {} if autenticacao == "ausente" else {"X-Senha-Mestra": token_urlsafe(24)}}
    if metodo in ("put", "post"):
        kwargs["json"] = {"senha": token_urlsafe(24)}
        if metodo == "post":
            kwargs["json"]["titulo"] = "Teste"
    resposta = getattr(api, metodo)(c["rota"] if colecao else c["item"], **kwargs)
    assert resposta.status_code == codigo
    assert banco.segredos == antes


@pytest.mark.parametrize("metodo", ["get", "put", "delete"])
def test_segredo_de_outro_cofre_inacessivel(api, banco, cenario, metodo):
    c = cenario
    mestra = token_urlsafe(24)
    outro = api.post("/cofres", json={"nome": "Outro", "senha_mestra": mestra}).json()["id"]
    kwargs = {"headers": {"X-Senha-Mestra": mestra}}
    if metodo == "put":
        kwargs["json"] = {"senha": token_urlsafe(24)}
    antes = deepcopy(banco.segredos)
    resposta = getattr(api, metodo)(f"/cofres/{outro}/segredos/{c['segredo_id']}", **kwargs)
    assert resposta.status_code == 404
    assert banco.segredos == antes


def test_ids_e_cofre_inexistentes(api, cenario):
    assert api.get(f"/cofres/{uuid4()}/segredos", headers=cenario["headers"]).status_code == 404
    assert api.get("/cofres/nao-e-uuid/segredos", headers=cenario["headers"]).status_code == 422
    assert api.get(f"{cenario['rota']}/{uuid4()}", headers=cenario["headers"]).status_code == 404


def test_validacao_nao_reflete_senhas(api):
    segredo = token_urlsafe(24)
    resposta = api.post("/cofres", json={"nome": "Teste", "senha_mestra": {"valor": segredo}})
    assert resposta.status_code == 422 and segredo not in resposta.text
    resposta = api.post("/cofres", json={"nome": "Teste", "senha_mestra": segredo, "extra": segredo})
    assert resposta.status_code == 422 and segredo not in resposta.text


def test_validacao_nao_reflete_nome_de_campo_extra(api):
    segredo = token_urlsafe(24)
    resposta = api.post("/cofres", json={"nome": "Teste", "senha_mestra": token_urlsafe(24), segredo: "extra"})
    assert resposta.status_code == 422
    refletiu_segredo = segredo in resposta.text
    assert not refletiu_segredo


def test_resposta_invalida_do_banco_nao_propaga_senha(api, banco, cenario, caplog):
    del banco.segredos[cenario["segredo_id"]]["criado_em"]
    resposta = None
    try:
        resposta = api.get(cenario["item"], headers=cenario["headers"])
    except ResponseValidationError:
        # Não imprimir a exceção bruta, que pode conter o segredo decifrado.
        pass
    assert resposta is not None, "A validação de saída deve ser tratada pela API"
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": "dados do registro inválidos"}
    assert resposta.headers["cache-control"] == "no-store"
    exposto = any(valor in resposta.text or valor in caplog.text
                  for valor in (cenario["senha"], cenario["mestra"]))
    assert not exposto


def test_base64_invalido_recusado(api, banco, cenario):
    banco.segredos[cenario["segredo_id"]]["criptograma"] = "%%%"
    resposta = api.get(cenario["item"], headers=cenario["headers"])
    assert resposta.status_code == 500 and "senha" not in resposta.json()


def test_sal_e_iteracoes_adulterados_nao_travam_api(api, banco, cenario):
    banco.cofres[cenario["cofre_id"]]["kdf_iteracoes"] = 10**12
    assert api.get(cenario["item"], headers=cenario["headers"]).status_code == 500


@pytest.mark.parametrize("erro", [BancoNaoConfigurado, ErroBanco])
def test_falha_banco_sem_detalhes_sensiveis(api, erro):
    segredo = token_urlsafe(24)
    def falhar():
        raise erro(segredo)
    app.dependency_overrides[obter_banco] = falhar
    resposta = api.post("/cofres", json={"nome": "Teste", "senha_mestra": token_urlsafe(24)})
    assert resposta.status_code == 503 and segredo not in resposta.text
