# Resultados de verificação

## Situação da execução

Validação local revisada em 15/09/2026: **51 testes aprovados**, com Python 3.12, AES-GCM e PBKDF2 reais. A persistência da API foi substituída por banco em memória nos testes locais. As consultas do cliente Supabase foram verificadas separadamente com transporte HTTP simulado.

A execução apresentou dois avisos de descontinuação internos de Starlette/AnyIO relativos ao cliente de testes, sem falhas. O comando `pip check` não identificou dependências incompatíveis. A aplicação também foi iniciada com Uvicorn e respondeu HTTP 200 em `/docs` e `/openapi.json`.

A integração com Supabase real foi validada em 16/09/2026, às 18h46 (America/Sao_Paulo). Os cinco cenários obrigatórios e o ciclo de operações passaram com as tabelas e permissões configuradas no projeto da equipe. A API foi exercitada por TestClient local com conexão real ao Supabase; esta execução não representa uma implantação pública da API.

## Cenários do enunciado

| Teste | Resultado observado localmente | Supabase real |
| --- | --- | --- |
| 1. Nonces distintos | A mesma senha gerou nonces e criptogramas diferentes | Aprovado: valores distintos nos dois registros reais |
| 2. Senha-mestra incorreta | HTTP 401 sem conteúdo do segredo | Aprovado: HTTP 401 sem campo de senha |
| 3. Conteúdo do banco | Senha-mestra e senha protegida ausentes dos registros persistidos; campos cifrados em Base64 | Aprovado: registros reais consultados sem senhas em texto claro |
| 4. Registro adulterado | Alterações em criptograma, nonce ou etiqueta causaram HTTP 500 sem senha | Aprovado: alteração de um bit do criptograma produziu HTTP 500 com registro adulterado |
| 5. Troca entre registros | Copiar os três campos de um segredo para outro causou HTTP 500 | Aprovado: cópia entre registros recusada com HTTP 500 |

## Verificações adicionais

Os testes cobrem ciclo de criação, abertura, leitura, atualização e exclusão; novo nonce nas atualizações; autenticação na listagem e nas operações; isolamento entre cofres; respostas 404 e 422; ausência de senhas nas mensagens de erro; Base64 inválido; parâmetros KDF adulterados; PBKDF2 comparado com a implementação independente `hashlib`; Unicode na criptografia; e consultas do Supabase com filtro por cofre e segredo.

A revisão conforme `AGENTS.md` acrescentou testes para impedir reflexão de nomes de campos extras e propagação de exceções contendo registros decifrados. Os dois testes reproduziram falhas antes da correção e passaram depois. Também foram verificados os limites mínimo e máximo das senhas nos três modelos de entrada e seu mascaramento na serialização. A arquitetura, os parâmetros criptográficos e os cinco cenários originais foram preservados.

Evidência executável: `evidencias/pytest-local.xml`. Para reproduzir:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=testes/evidencias/pytest-local.xml
```

## Validação real no Supabase

Execução: `python -m testes.verificar_supabase`, com o Python do ambiente virtual. Resultado: código de saída 0. O verificador utilizou senhas aleatórias temporárias e gravou somente resultados e registros cifrados no relatório.

- Data: 16/09/2026, início às 21h46min05s UTC (18h46min05s em São Paulo).
- Evidência: [supabase-20260916T214605Z.json](evidencias/supabase-20260916T214605Z.json).
- Testes 1 a 5: aprovados.
- Operações adicionais: criação e abertura do cofre; cadastro, listagem restrita aos metadados, leitura, atualização com nonce novo e exclusão de segredo; HTTP 404 após exclusão.
- Tabelas, permissões e integração: funcionais para as operações verificadas. Não foi realizada auditoria administrativa das políticas.
- Limpeza: cofre descartável removido com seus segredos. Uma consulta independente posterior confirmou ausência do cofre e zero segredos vinculados. Nenhum registro anterior foi alterado.

Para reproduzir, execute o mesmo comando ou siga `roteiro_manual.md`. Cada execução gera seu próprio relatório e seus próprios registros descartáveis. Os 51 testes locais correspondem à execução anterior; não foram reexecutados nesta validação de integração, que não alterou o código da aplicação.

Revise a ausência de senhas nas capturas antes de publicar o repositório.
