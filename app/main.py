"""Rotas e orquestração. Nenhuma senha ou chave é mantida entre requisições."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from app import cripto
from app.banco import BancoNaoConfigurado, BancoSupabase, ErroBanco, obter_banco
from app.modelos import (AtualizarSegredo, Identificador, Mensagem,
                         MetadadosSegredo, NovoCofre, NovoSegredo, SegredoAberto)

app = FastAPI(title="Cofre de Senhas", version="1.0.0",
              description="Laboratório de AES-256-GCM e PBKDF2. Informe X-Senha-Mestra no botão Authorize.")
cabecalho = APIKeyHeader(name="X-Senha-Mestra", auto_error=False)
Banco = Annotated[BancoSupabase, Depends(obter_banco)]


@app.middleware("http")
async def sem_cache(request: Request, call_next):
    resposta = await call_next(request)
    resposta.headers["Cache-Control"] = "no-store"
    return resposta


@app.exception_handler(RequestValidationError)
async def erro_validacao(request: Request, erro: RequestValidationError):
    # Valores e nomes de campos extras são controlados pelo cliente e podem conter senhas.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": list(item["loc"][:-1] if item["type"] == "extra_forbidden" else item["loc"]),
         "msg": "Campo inválido ou obrigatório", "type": item["type"]}
        for item in erro.errors()
    ]})


@app.exception_handler(ResponseValidationError)
async def erro_validacao_resposta(request: Request, erro: ResponseValidationError):
    # A exceção de saída pode carregar o registro inteiro, inclusive a senha decifrada.
    return JSONResponse(status_code=500, content={"detail": "dados do registro inválidos"})


@app.exception_handler(ErroBanco)
async def erro_banco(request: Request, erro: ErroBanco):
    detalhe = ("Configure SUPABASE_URL e SUPABASE_KEY no .env e execute sql/esquema.sql"
               if isinstance(erro, BancoNaoConfigurado) else "Banco de dados indisponível")
    return JSONResponse(status_code=503, content={"detail": detalhe})


@dataclass
class CofreAutenticado:
    id: str
    chave: bytes = field(repr=False)


def autenticar(cofre_id: UUID, banco: Banco,
               senha: Annotated[str | None, Security(cabecalho)]) -> CofreAutenticado:
    if senha is None:
        raise HTTPException(422, "Cabeçalho X-Senha-Mestra obrigatório")
    if not 1 <= len(senha) <= 1024:
        raise HTTPException(401, "senha-mestra incorreta")
    cofre = banco.buscar_cofre(str(cofre_id))
    if cofre is None:
        raise HTTPException(404, "cofre não encontrado")
    try:
        chave = cripto.derivar_chave(senha, cripto.de_b64(cofre["kdf_sal"]), cofre["kdf_iteracoes"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(500, "configuração criptográfica do cofre inválida") from None
    try:
        correta = cripto.senha_mestra_correta(
            chave, cofre["verificador_nonce"], cofre["verificador_criptograma"],
            cofre["verificador_etiqueta"], str(cofre_id),
        )
    except (KeyError, TypeError):
        correta = False
    if not correta:
        raise HTTPException(401, "senha-mestra incorreta")
    return CofreAutenticado(str(cofre_id), chave)


Autenticado = Annotated[CofreAutenticado, Depends(autenticar)]


def buscar_segredo(banco: BancoSupabase, cofre_id: str, segredo_id: UUID) -> dict:
    segredo = banco.buscar_segredo(cofre_id, str(segredo_id))
    if segredo is None:
        raise HTTPException(404, "segredo não encontrado")
    return segredo


def campos_cifrados(chave: bytes, senha: str, cofre_id: str, segredo_id: str) -> dict:
    nonce, criptograma, etiqueta = cripto.cifrar(chave, senha, cripto.montar_aad(cofre_id, segredo_id))
    return {"nonce": nonce, "criptograma": criptograma, "etiqueta": etiqueta}


@app.post("/cofres", status_code=201, response_model=Identificador)
def criar_cofre(dados: NovoCofre, banco: Banco):
    cofre_id = str(uuid4())
    sal = cripto.gerar_sal()
    chave = cripto.derivar_chave(dados.senha_mestra.get_secret_value(), sal, cripto.ITERACOES_PADRAO)
    nonce, criptograma, etiqueta = cripto.criar_verificador(chave, cofre_id)
    banco.inserir_cofre({"id": cofre_id, "nome": dados.nome,
                        "kdf_sal": cripto.para_b64(sal), "kdf_iteracoes": cripto.ITERACOES_PADRAO,
                        "verificador_nonce": nonce, "verificador_criptograma": criptograma,
                        "verificador_etiqueta": etiqueta})
    return {"id": cofre_id}


@app.post("/cofres/{cofre_id}/abrir", response_model=Mensagem)
def abrir_cofre(cofre: Autenticado):
    return {"mensagem": "cofre aberto"}


@app.post("/cofres/{cofre_id}/segredos", status_code=201, response_model=Identificador)
def criar_segredo(dados: NovoSegredo, cofre: Autenticado, banco: Banco):
    segredo_id = str(uuid4())
    registro = {"id": segredo_id, "cofre_id": cofre.id, "titulo": dados.titulo,
                "usuario": dados.usuario, "url": dados.url}
    registro.update(campos_cifrados(cofre.chave, dados.senha.get_secret_value(), cofre.id, segredo_id))
    banco.inserir_segredo(registro)
    return {"id": segredo_id}


@app.get("/cofres/{cofre_id}/segredos", response_model=list[MetadadosSegredo])
def listar_segredos(cofre: Autenticado, banco: Banco):
    return banco.listar_segredos(cofre.id)


@app.get("/cofres/{cofre_id}/segredos/{segredo_id}", response_model=SegredoAberto)
def ler_segredo(segredo_id: UUID, cofre: Autenticado, banco: Banco):
    segredo = buscar_segredo(banco, cofre.id, segredo_id)
    try:
        senha = cripto.decifrar(cofre.chave, segredo["nonce"], segredo["criptograma"],
                               segredo["etiqueta"], cripto.montar_aad(cofre.id, str(segredo_id)))
    except (ValueError, KeyError, TypeError):
        raise HTTPException(500, "registro adulterado") from None
    return {**segredo, "senha": senha}


@app.put("/cofres/{cofre_id}/segredos/{segredo_id}", response_model=Mensagem)
def atualizar_segredo(segredo_id: UUID, dados: AtualizarSegredo, cofre: Autenticado, banco: Banco):
    buscar_segredo(banco, cofre.id, segredo_id)
    campos = campos_cifrados(cofre.chave, dados.senha.get_secret_value(), cofre.id, str(segredo_id))
    campos["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    if not banco.atualizar_segredo(cofre.id, str(segredo_id), campos):
        raise HTTPException(404, "segredo não encontrado")
    return {"mensagem": "senha atualizada"}


@app.delete("/cofres/{cofre_id}/segredos/{segredo_id}", response_model=Mensagem)
def remover_segredo(segredo_id: UUID, cofre: Autenticado, banco: Banco):
    if not banco.remover_segredo(cofre.id, str(segredo_id)):
        raise HTTPException(404, "segredo não encontrado")
    return {"mensagem": "segredo removido"}
