"""Contratos de entrada e saída; senhas não aparecem no repr dos modelos."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NovoCofre(Entrada):
    nome: str = Field(min_length=1, max_length=200)
    senha_mestra: SecretStr = Field(min_length=1, max_length=1024)


class NovoSegredo(Entrada):
    titulo: str = Field(min_length=1, max_length=200)
    usuario: str | None = Field(default=None, max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    senha: SecretStr = Field(min_length=1, max_length=10000)


class AtualizarSegredo(Entrada):
    senha: SecretStr = Field(min_length=1, max_length=10000)


class Identificador(BaseModel):
    id: UUID


class Mensagem(BaseModel):
    mensagem: str


class MetadadosSegredo(BaseModel):
    id: UUID
    titulo: str
    usuario: str | None = None
    url: str | None = None
    criado_em: datetime


class SegredoAberto(MetadadosSegredo):
    senha: str
