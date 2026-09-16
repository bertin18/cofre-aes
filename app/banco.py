"""Acesso ao Supabase. Este módulo não importa criptografia ou HTTP da API."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from httpx import HTTPError
from postgrest.exceptions import APIError
from supabase import Client, create_client

METADADOS = "id, titulo, usuario, url, criado_em"
RAIZ = Path(__file__).resolve().parent.parent


class ErroBanco(Exception):
    """Falha de acesso sem incluir conteúdo das consultas."""


class BancoNaoConfigurado(ErroBanco):
    pass


@lru_cache(maxsize=1)
def cliente() -> Client:
    load_dotenv(RAIZ / ".env")
    url = os.getenv("SUPABASE_URL", "").strip()
    chave = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not chave or "SEU-PROJETO" in url or chave == "SUA-CHAVE-PUBLICA":
        raise BancoNaoConfigurado("Preencha SUPABASE_URL e SUPABASE_KEY no arquivo .env")
    try:
        return create_client(url, chave)
    except Exception:
        raise BancoNaoConfigurado("Configuração do Supabase inválida") from None


def executar(consulta):
    try:
        return consulta.execute().data
    except (APIError, HTTPError):
        raise ErroBanco("Não foi possível acessar o banco") from None


class BancoSupabase:
    def inserir_cofre(self, registro: dict) -> None:
        executar(cliente().table("cofres").insert(registro))

    def buscar_cofre(self, cofre_id: str) -> dict | None:
        registros = executar(cliente().table("cofres").select("*").eq("id", cofre_id).limit(1))
        return registros[0] if registros else None

    def inserir_segredo(self, registro: dict) -> None:
        executar(cliente().table("segredos").insert(registro))

    def listar_segredos(self, cofre_id: str) -> list[dict]:
        return executar(cliente().table("segredos").select(METADADOS).eq("cofre_id", cofre_id).order("criado_em"))

    def buscar_segredo(self, cofre_id: str, segredo_id: str) -> dict | None:
        registros = executar(cliente().table("segredos").select("*")
                             .eq("cofre_id", cofre_id).eq("id", segredo_id).limit(1))
        return registros[0] if registros else None

    def atualizar_segredo(self, cofre_id: str, segredo_id: str, campos: dict) -> bool:
        return bool(executar(cliente().table("segredos").update(campos)
                             .eq("cofre_id", cofre_id).eq("id", segredo_id)))

    def remover_segredo(self, cofre_id: str, segredo_id: str) -> bool:
        return bool(executar(cliente().table("segredos").delete()
                             .eq("cofre_id", cofre_id).eq("id", segredo_id)))


def obter_banco() -> BancoSupabase:
    return BancoSupabase()
