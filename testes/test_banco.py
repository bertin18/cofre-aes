"""Verifica as consultas reais do cliente Supabase com transporte HTTP simulado."""

import json
from uuid import uuid4

import httpx
import pytest
from supabase import ClientOptions, create_client

from app import banco


def test_consultas_filtram_cofre_e_segredo_e_projetam_metadados(monkeypatch):
    requisicoes = []
    cofre_id, segredo_id = str(uuid4()), str(uuid4())

    def responder(request):
        requisicoes.append(request)
        return httpx.Response(200, json=[{"id": segredo_id}], headers={"content-range": "0-0/1"})

    with httpx.Client(transport=httpx.MockTransport(responder)) as transporte:
        cliente = create_client("https://laboratorio.supabase.co", "sb_publishable_apenas_teste",
                                options=ClientOptions(httpx_client=transporte))
        monkeypatch.setattr(banco, "cliente", lambda: cliente)
        repositorio = banco.BancoSupabase()
        repositorio.listar_segredos(cofre_id)
        assert requisicoes[-1].url.params["select"] == banco.METADADOS.replace(" ", "")
        repositorio.buscar_segredo(cofre_id, segredo_id)
        repositorio.atualizar_segredo(cofre_id, segredo_id, {"nonce": "novo"})
        repositorio.remover_segredo(cofre_id, segredo_id)
        for request in requisicoes[1:]:
            assert request.url.params["cofre_id"] == f"eq.{cofre_id}"
            assert request.url.params["id"] == f"eq.{segredo_id}"
        assert [r.method for r in requisicoes] == ["GET", "GET", "PATCH", "DELETE"]
        assert json.loads(requisicoes[2].content) == {"nonce": "novo"}


def test_erro_do_supabase_e_convertido_sem_conteudo(monkeypatch):
    def responder(request):
        return httpx.Response(403, json={"message": "detalhe interno", "code": "42501", "hint": None, "details": None})
    with httpx.Client(transport=httpx.MockTransport(responder)) as transporte:
        cliente = create_client("https://laboratorio.supabase.co", "sb_publishable_apenas_teste",
                                options=ClientOptions(httpx_client=transporte))
        monkeypatch.setattr(banco, "cliente", lambda: cliente)
        with pytest.raises(banco.ErroBanco, match="Não foi possível acessar o banco"):
            banco.BancoSupabase().listar_segredos(str(uuid4()))
