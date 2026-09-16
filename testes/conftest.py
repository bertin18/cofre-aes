from copy import deepcopy
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.banco import METADADOS, obter_banco
from app.main import app


class BancoMemoria:
    """Substituto exclusivo dos testes; a aplicação sempre usa o Supabase."""

    def __init__(self):
        self.cofres = {}
        self.segredos = {}

    def inserir_cofre(self, registro):
        self.cofres[registro["id"]] = deepcopy(registro)

    def buscar_cofre(self, cofre_id):
        return deepcopy(self.cofres.get(cofre_id))

    def inserir_segredo(self, registro):
        self.segredos[registro["id"]] = {
            **deepcopy(registro), "criado_em": datetime.now(timezone.utc).isoformat(),
        }

    def listar_segredos(self, cofre_id):
        campos = METADADOS.split(", ")
        return [{k: r[k] for k in campos} for r in self.segredos.values() if r["cofre_id"] == cofre_id]

    def buscar_segredo(self, cofre_id, segredo_id):
        registro = self.segredos.get(segredo_id)
        return deepcopy(registro) if registro and registro["cofre_id"] == cofre_id else None

    def atualizar_segredo(self, cofre_id, segredo_id, campos):
        if self.buscar_segredo(cofre_id, segredo_id) is None:
            return False
        self.segredos[segredo_id].update(deepcopy(campos))
        return True

    def remover_segredo(self, cofre_id, segredo_id):
        if self.buscar_segredo(cofre_id, segredo_id) is None:
            return False
        del self.segredos[segredo_id]
        return True


@pytest.fixture
def banco():
    return BancoMemoria()


@pytest.fixture
def api(banco):
    app.dependency_overrides[obter_banco] = lambda: banco
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cenario(api):
    from secrets import token_urlsafe
    mestra, senha = token_urlsafe(24), token_urlsafe(24)
    resposta = api.post("/cofres", json={"nome": "Cofre de teste", "senha_mestra": mestra})
    assert resposta.status_code == 201
    cofre_id = resposta.json()["id"]
    headers = {"X-Senha-Mestra": mestra}
    rota = f"/cofres/{cofre_id}/segredos"
    resposta = api.post(rota, headers=headers, json={"titulo": "Credencial de teste", "senha": senha})
    assert resposta.status_code == 201
    segredo_id = resposta.json()["id"]
    return {"cofre_id": cofre_id, "segredo_id": segredo_id, "headers": headers,
            "mestra": mestra, "senha": senha, "rota": rota, "item": f"{rota}/{segredo_id}"}
