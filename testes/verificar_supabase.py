"""Execute `python -m testes.verificar_supabase` após configurar o banco real.

Cria e adultera somente registros descartáveis próprios, com senhas aleatórias.
Remove o cofre criado ao terminar e não registra senhas ou chaves.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_urlsafe
from uuid import uuid4

from fastapi.testclient import TestClient

from app import cripto
from app.banco import BancoSupabase, cliente, executar
from app.main import app


def conferir(condicao: bool, mensagem: str):
    if not condicao:
        raise RuntimeError(mensagem)


def verificar():
    banco = BancoSupabase()
    cofre_id = None
    resultados = []
    instante = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destino = Path(__file__).parent / "evidencias" / f"supabase-{instante}.json"
    erro_execucao = None
    with TestClient(app) as api:
        try:
            mestra, senha = token_urlsafe(32), token_urlsafe(32)
            resposta = api.post("/cofres", json={"nome": f"Verificação descartável {uuid4()}", "senha_mestra": mestra})
            conferir(resposta.status_code == 201, "Criação falhou: confira .env, SQL e políticas no Supabase")
            cofre_id = resposta.json()["id"]
            headers = {"X-Senha-Mestra": mestra}
            rota = f"/cofres/{cofre_id}/segredos"
            ids = []
            for titulo in ("Teste A", "Teste B"):
                resposta = api.post(rota, headers=headers, json={"titulo": titulo, "senha": senha})
                conferir(resposta.status_code == 201, "Falha ao inserir segredo de teste")
                ids.append(resposta.json()["id"])
            a, b = (banco.buscar_segredo(cofre_id, sid) for sid in ids)
            conferir(a["nonce"] != b["nonce"] and a["criptograma"] != b["criptograma"], "Teste 1 falhou")
            resultados.append({"teste": 1, "resultado": "aprovado", "observacao": "Nonces e criptogramas distintos"})

            resposta = api.get(f"{rota}/{ids[0]}", headers={"X-Senha-Mestra": token_urlsafe(32)})
            conferir(resposta.status_code == 401 and "senha" not in resposta.json(), "Teste 2 falhou")
            resultados.append({"teste": 2, "resultado": "aprovado", "http": 401})

            dump = json.dumps([a, b, banco.buscar_cofre(cofre_id)])
            conferir(senha not in dump and mestra not in dump and "senha" not in a, "Teste 3 falhou")
            resultados.append({"teste": 3, "resultado": "aprovado", "registros_cifrados": [a, b]})
            resposta = api.get(f"{rota}/{ids[0]}", headers=headers)
            conferir(resposta.status_code == 200 and resposta.json()["senha"] == senha, "Leitura correta falhou")

            alterado = bytearray(cripto.de_b64(a["criptograma"]))
            alterado[0] ^= 1
            banco.atualizar_segredo(cofre_id, ids[0], {"criptograma": cripto.para_b64(bytes(alterado))})
            resposta = api.get(f"{rota}/{ids[0]}", headers=headers)
            conferir(resposta.status_code == 500 and resposta.json() == {"detail": "registro adulterado"}, "Teste 4 falhou")
            resultados.append({"teste": 4, "resultado": "aprovado", "http": 500})
            banco.atualizar_segredo(cofre_id, ids[0], {"criptograma": a["criptograma"]})

            banco.atualizar_segredo(cofre_id, ids[1], {campo: a[campo] for campo in ("nonce", "criptograma", "etiqueta")})
            resposta = api.get(f"{rota}/{ids[1]}", headers=headers)
            conferir(resposta.status_code == 500 and resposta.json() == {"detail": "registro adulterado"}, "Teste 5 falhou")
            resultados.append({"teste": 5, "resultado": "aprovado", "http": 500})

            conferir(api.post(f"/cofres/{cofre_id}/abrir", headers=headers).status_code == 200, "Abertura falhou")
            lista = api.get(rota, headers=headers)
            conferir(lista.status_code == 200 and len(lista.json()) == 2, "Listagem falhou")
            conferir(all(set(r) == {"id", "titulo", "usuario", "url", "criado_em"} for r in lista.json()), "Listagem expôs campos indevidos")
            nova = token_urlsafe(32)
            conferir(api.put(f"{rota}/{ids[0]}", headers=headers, json={"senha": nova}).status_code == 200, "Atualização falhou")
            conferir(banco.buscar_segredo(cofre_id, ids[0])["nonce"] != a["nonce"], "Nonce reutilizado")
            conferir(api.get(f"{rota}/{ids[0]}", headers=headers).json().get("senha") == nova, "Leitura após atualização falhou")
            conferir(api.delete(f"{rota}/{ids[0]}", headers=headers).status_code == 200, "Exclusão falhou")
            conferir(api.get(f"{rota}/{ids[0]}", headers=headers).status_code == 404, "Registro continuou disponível")
            resultados.append({"teste": "rotas adicionais", "resultado": "aprovado"})
        except Exception:
            # Não persistir a exceção bruta: bibliotecas podem incluir dados da consulta.
            erro_execucao = "A verificação falhou. Confira conexão, esquema e último teste aprovado."
        finally:
            limpeza = "nenhum cofre confirmado"
            if cofre_id:
                try:
                    executar(cliente().table("cofres").delete().eq("id", cofre_id))
                    limpeza = "cofre de teste removido com seus segredos"
                except Exception:
                    limpeza = f"limpeza pendente: remova somente o cofre {cofre_id}"
                    erro_execucao = erro_execucao or "Testes concluídos, mas a limpeza falhou."
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps({"executado_em_utc": instante, "ambiente": "Supabase real",
                                          "cofre_de_teste": cofre_id, "resultados": resultados,
                                          "limpeza": limpeza, "erro": erro_execucao},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evidência gravada em {destino.name}")
    print(limpeza)
    if erro_execucao:
        print(erro_execucao)
        return 1
    print("Os cinco testes obrigatórios e o ciclo de operações passaram no Supabase real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(verificar())
