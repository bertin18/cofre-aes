# Cofre de senhas corporativo

API de laboratório da disciplina de Criptografia Aplicada da PUC Goiás. Armazena senhas com AES-256-GCM e deriva a chave de cada cofre com PBKDF2-HMAC-SHA-256. O Supabase recebe os dados já cifrados.

## Equipe

Trabalho individual.

- Integrante: Gabriel Berti.
- Matrícula: 20221003300891.

O projeto Supabase utilizado é exclusivo deste trabalho.

## Instalação e execução

Ambiente validado: Python 3.12 no Windows. O enunciado permite Python 3.10 ou superior; as versões exatas utilizadas estão em `requirements.txt`.

Na pasta do projeto, com Python instalado:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nesta cópia local, o ambiente virtual já foi criado e as dependências instaladas. Ele é exclusivo desta máquina e não deve ser copiado para o GitHub. Não é necessário ativá-lo ao usar seu executável diretamente.

1. Crie um projeto no [Supabase](https://supabase.com/dashboard). Escolha um projeto gratuito, novo e exclusivo da equipe. A senha administrativa do banco é diferente da senha-mestra de um cofre.
2. No SQL Editor, execute uma única vez o conteúdo de `sql/esquema.sql`. Ele cria tabelas, índice, permissões e políticas do laboratório, sem apagar tabelas existentes.
3. Nas configurações de API do projeto, copie a URL e a chave pública `anon` ou `publishable`. Não use uma chave `service_role` ou `secret`.
4. Preencha o `.env` local já criado. Em uma instalação obtida do GitHub, copie `.env.exemplo` para `.env` primeiro. Não envie o `.env` ao repositório.

```dotenv
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_KEY=SUA-CHAVE-PUBLICA
```

Inicie a aplicação a partir da pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --no-access-log
```

Abra [a documentação interativa](http://127.0.0.1:8000/docs). Também é possível iniciar com `iniciar.ps1`. Em Linux/macOS, substitua o executável do ambiente por `.venv/bin/python`.

O `/docs` abre mesmo sem Supabase configurado; as operações de banco respondem 503 até a configuração estar pronta. Reinicie o servidor se alterar o `.env` após a primeira conexão. `--reload` é destinado ao desenvolvimento.

## Como experimentar

Use apenas credenciais fictícias neste laboratório.

1. Em `POST /cofres`, clique em **Try it out**, preencha nome e senha-mestra e execute. Guarde o `id` retornado.
2. No botão **Authorize**, informe a mesma senha-mestra. Ela será enviada no cabeçalho `X-Senha-Mestra`. A abertura não cria sessão: cada operação verifica a senha novamente.
3. Cadastre uma credencial em `POST /cofres/{cofre_id}/segredos` e guarde o identificador retornado.
4. Liste os metadados e consulte a credencial pela rota individual.
5. Atualize a senha pelo `PUT` e depois teste a exclusão.

As senhas são processadas durante a requisição e não são salvas pela aplicação em logs, sessões ou caches. O Swagger mantém o valor autorizado enquanto a página está aberta; finalize a autorização ao terminar.

## Rotas

| Método | Rota | Resultado |
| --- | --- | --- |
| POST | `/cofres` | Cria cofre e retorna `id`, HTTP 201 |
| POST | `/cofres/{cofre_id}/abrir` | Valida senha-mestra, HTTP 200 |
| POST | `/cofres/{cofre_id}/segredos` | Cifra e cadastra segredo, HTTP 201 |
| GET | `/cofres/{cofre_id}/segredos` | Lista somente id, título, usuário, URL e criação |
| GET | `/cofres/{cofre_id}/segredos/{segredo_id}` | Retorna metadados e senha decifrada |
| PUT | `/cofres/{cofre_id}/segredos/{segredo_id}` | Recebe `senha`, substitui a senha com novo nonce, HTTP 200 |
| DELETE | `/cofres/{cofre_id}/segredos/{segredo_id}` | Remove segredo, HTTP 200 |

Todas as rotas, exceto a criação do cofre, exigem `X-Senha-Mestra`, inclusive a listagem. Essa decisão segue a seção 11.3 do enunciado; a seção 5.4 menciona listagem sem senha-mestra, mas os requisitos de rotas são mais específicos. Um segredo é sempre consultado, atualizado ou excluído com os dois identificadores para impedir acesso cruzado entre cofres.

Exemplo ilustrativo de criação (o valor entre `< >` é um marcador, não uma senha pronta para uso):

```http
POST /cofres
Content-Type: application/json

{"nome":"Equipe","senha_mestra":"<senha-mestra escolhida pela equipe>"}
```

Resposta ilustrativa, HTTP 201:

```json
{"id":"b8374310-b291-4d40-a3ef-4b70b8fcf5f5"}
```

Uma consulta individual usa o cabeçalho `X-Senha-Mestra: <senha-mestra>` e retorna `id`, `titulo`, `usuario`, `url`, `criado_em` e `senha`. Os campos nonce, criptograma e etiqueta não são devolvidos pela API. A listagem nunca retorna `senha`.

Erros: 401 para verificador recusado; 404 para cofre ou segredo inexistente; 422 para entrada inválida ou cabeçalho ausente; 500 para segredo adulterado após autenticação, parâmetros criptográficos corrompidos ou dados do registro incompatíveis com a resposta; 503 para banco sem configuração ou indisponível. Erros de validação omitem valores recebidos e nomes de campos extras, evitando refletir senhas. Falhas na validação da resposta são tratadas sem propagar a exceção com o registro decifrado.

A senha-mestra aceita de 1 a 1.024 caracteres, e a senha protegida de 1 a 10.000 caracteres, tanto no cadastro quanto na atualização. Esses limites são validados no servidor e exibidos no esquema da API.

## Criptografia e parâmetros

- PBKDF2-HMAC-SHA-256, 210.000 iterações, chave derivada de 32 bytes. A senha é convertida explicitamente para UTF-8, suportando caracteres fora do alfabeto latino. O número de iterações é persistido por cofre.
- Sal aleatório de 16 bytes por cofre, público. Individualiza a derivação de chave.
- AES-256-GCM, nonce aleatório de 12 bytes a cada cifragem e etiqueta de autenticação de 16 bytes. A decifragem usa `decrypt_and_verify`; nenhum texto claro é retornado se a autenticação falhar.
- AAD dos segredos: `cofre_id|segredo_id`, codificado em UTF-8. Vincula a informação cifrada ao registro.
- Verificador: frase fixa `cofre-ok`, cifrada com AAD igual ao identificador do cofre.
- Bytes são armazenados em Base64, que é uma codificação e não uma camada adicional de criptografia.
- A API aceita de 210.000 a 2.000.000 iterações. O limite superior impede que um valor adulterado no banco force um cálculo arbitrariamente longo. Para aumentar o limite no futuro, altere conjuntamente a validação e a restrição SQL.

Os parâmetros atendem ao enunciado acadêmico. Não constituem uma recomendação universal para sistemas de produção.

## Organização

```text
app/
  __init__.py
  cripto.py              PBKDF2, AES-GCM, Base64, AAD e verificador
  banco.py               Operações do cliente Supabase
  modelos.py             Validação e contratos de entrada e saída
  main.py                Rotas, autenticação e tratamento HTTP
sql/esquema.sql           Tabelas, índice e políticas do laboratório
testes/
  conftest.py            Banco em memória exclusivo dos testes
  test_cripto.py         Propriedades criptográficas
  test_api.py            Rotas e cenários de segurança
  test_banco.py          Consultas Supabase com transporte HTTP simulado
  verificar_supabase.py  Verificação opcional no Supabase real
  resultados.md          Resultados e pendências de verificação
  roteiro_manual.md     Cinco testes manuais exigidos
  evidencias/            Evidências sem senhas em texto claro
.env.exemplo
.gitignore
requirements.txt
iniciar.ps1
README.md
```

## Testes

Testes locais, sem conexão externa:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=testes/evidencias/pytest-local.xml
```

Eles utilizam a criptografia real e substituem o banco por um armazenamento em memória. Os testes do cliente Supabase utilizam transporte HTTP simulado para verificar filtros e projeção de colunas. Esses testes não comprovam que as tabelas e políticas estejam corretas no Supabase real.

Depois de configurar o `.env` e executar o SQL, rode:

```powershell
.\.venv\Scripts\python.exe -m testes.verificar_supabase
```

O verificador acessa o banco real através da API em um cliente de teste local, executa os cinco cenários e as operações adicionais, e salva evidências em `testes/evidencias/supabase-DATA.json`. Cria um cofre próprio com senhas aleatórias, altera apenas os registros desse cofre e o remove ao terminar. Não grava as senhas nem as chaves nas evidências. Em caso de falha na limpeza, o relatório identifica o cofre descartável pendente. Para testes no navegador e SQL Editor, siga `testes/roteiro_manual.md`.

## Limitações

- Protege a confidencialidade das senhas em uma cópia lógica do banco e detecta alterações em nonce, criptograma, etiqueta e vínculo do registro. Não impede que um invasor apague registros ou restaure versões antigas válidas.
- Não protege contra comprometimento do servidor durante o uso, senha-mestra fraca ou divulgada, nem oferece auditoria individual, recuperação ou troca de senha-mestra.
- Título, usuário, URL e datas ficam em texto claro. Uma cópia do banco revela os sistemas utilizados.
- As políticas `anon` de leitura e escrita amplas reproduzem o laboratório. Quem tem acesso público ao projeto pode ler, alterar e apagar registros; AES-GCM não fornece controle de acesso ou disponibilidade.
- Se o próprio verificador for adulterado, a API também responde 401. O verificador não permite distinguir com certeza essa adulteração de uma senha-mestra errada.
- Senhas e chaves existem temporariamente na memória durante o processamento. Python não garante sobrescrita imediata desses bytes. A aplicação não os retém deliberadamente entre requisições.
- Um nonce aleatório de 96 bits tem probabilidade de colisão muito baixa, mas não nula. Cada operação faz um novo sorteio; não há coordenação global de unicidade.
- A API local usa HTTP em `127.0.0.1`. Uma implantação externa precisaria de HTTPS, políticas restritas por usuário, limitação de tentativas e revisão de segurança. Cabeçalhos não são criptografados por si só e podem ser registrados por intermediários mal configurados.

## Entrega no GitHub

Antes de publicar, complete a identificação da equipe, execute a verificação real e atualize `testes/resultados.md` com o que foi observado. Confira `git status` e mantenha `.env`, `.venv`, credenciais reais e chaves fora do versionamento. O README e as evidências não devem conter senhas reais.

Crie um repositório público vazio em sua conta e, dentro desta pasta, use os comandos abaixo após revisar os arquivos. Substitua os marcadores pelos dados do repositório:

```powershell
git add .
git status
git commit -m "Cofre de senhas com AES-GCM"
git branch -M main
git remote add origin https://github.com/USUARIO/REPOSITORIO.git
git push -u origin main
```

O endereço do repositório é a entrega. O projeto local não foi publicado automaticamente.

## Referências

- Enunciado fornecido: Projeto de Laboratório — Cofre de Senhas Corporativo, PUC Goiás.
- [PyCryptodome — PBKDF2](https://www.pycryptodome.org/src/protocol/kdf)
- [PyCryptodome — AES-GCM](https://www.pycryptodome.org/src/cipher/modern)
- [FastAPI — tratamento de erros](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Supabase — cliente Python](https://supabase.com/docs/reference/python/initializing)
