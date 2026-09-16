"""Criptografia independente de HTTP e banco de dados."""

import base64
import binascii

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

ITERACOES_PADRAO = 210_000
TAMANHO_CHAVE = 32
TAMANHO_SAL = 16
TAMANHO_NONCE = 12
TAMANHO_ETIQUETA = 16
FRASE_VERIFICADORA = "cofre-ok"


def para_b64(dados: bytes) -> str:
    return base64.b64encode(dados).decode("ascii")


def de_b64(texto: str) -> bytes:
    try:
        return base64.b64decode(texto, validate=True)
    except (binascii.Error, ValueError, TypeError) as erro:
        raise ValueError("Base64 inválido") from erro


def derivar_chave(senha_mestra: str, sal: bytes, iteracoes: int) -> bytes:
    if len(sal) != TAMANHO_SAL:
        raise ValueError("O sal deve ter 16 bytes")
    if not isinstance(iteracoes, int) or not ITERACOES_PADRAO <= iteracoes <= 2_000_000:
        raise ValueError("Iterações fora da faixa suportada: 210000 a 2000000")
    return PBKDF2(
        senha_mestra.encode("utf-8"), sal, dkLen=TAMANHO_CHAVE,
        count=iteracoes, hmac_hash_module=SHA256,
    )


def gerar_sal() -> bytes:
    return get_random_bytes(TAMANHO_SAL)


def montar_aad(cofre_id: str, segredo_id: str) -> bytes:
    return f"{cofre_id}|{segredo_id}".encode("utf-8")


def cifrar(chave: bytes, texto_claro: str, aad: bytes) -> tuple[str, str, str]:
    if len(chave) != TAMANHO_CHAVE:
        raise ValueError("A chave deve ter 32 bytes")
    nonce = get_random_bytes(TAMANHO_NONCE)
    cifra = AES.new(chave, AES.MODE_GCM, nonce=nonce, mac_len=TAMANHO_ETIQUETA)
    cifra.update(aad)
    criptograma, etiqueta = cifra.encrypt_and_digest(texto_claro.encode("utf-8"))
    return para_b64(nonce), para_b64(criptograma), para_b64(etiqueta)


def decifrar(chave: bytes, nonce_b64: str, cripto_b64: str,
             etiqueta_b64: str, aad: bytes) -> str:
    nonce, criptograma, etiqueta = map(de_b64, (nonce_b64, cripto_b64, etiqueta_b64))
    if len(chave) != TAMANHO_CHAVE or len(nonce) != TAMANHO_NONCE or len(etiqueta) != TAMANHO_ETIQUETA:
        raise ValueError("Parâmetros criptográficos inválidos")
    cifra = AES.new(chave, AES.MODE_GCM, nonce=nonce, mac_len=TAMANHO_ETIQUETA)
    cifra.update(aad)
    return cifra.decrypt_and_verify(criptograma, etiqueta).decode("utf-8")


def criar_verificador(chave: bytes, cofre_id: str) -> tuple[str, str, str]:
    return cifrar(chave, FRASE_VERIFICADORA, cofre_id.encode("utf-8"))


def senha_mestra_correta(chave, nonce, cripto, etiqueta, cofre_id) -> bool:
    try:
        return decifrar(chave, nonce, cripto, etiqueta, cofre_id.encode("utf-8")) == FRASE_VERIFICADORA
    except ValueError:
        return False
