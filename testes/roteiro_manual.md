# Roteiro de verificação no Supabase

Execute depois de configurar o `.env`, criar as tabelas e iniciar a API. Use somente dados fictícios. Registre capturas ou saídas sem exibir senha-mestra, senha decifrada ou credenciais do `.env`.

## Preparação

No `/docs`, crie um cofre de laboratório. No botão Authorize, informe sua senha-mestra. Cadastre dois segredos com títulos diferentes e a mesma senha fictícia. Anote o identificador do cofre e os dois identificadores dos segredos.

Nos comandos abaixo, substitua os marcadores `ID_DO_COFRE`, `ID_DO_SEGREDO_A` e `ID_DO_SEGREDO_B` pelos UUIDs reais. Use apenas os registros descartáveis criados para este teste.

## Teste 1 Nonces distintos

No SQL Editor:

```sql
select id, titulo, nonce, criptograma
from public.segredos
where cofre_id = 'ID_DO_COFRE'::uuid;
```

Resultado esperado: dois nonces e dois criptogramas diferentes, mesmo com senhas iguais. Salve a evidência como `01-nonces-distintos.png` ou uma saída de terminal equivalente.

## Teste 2 Senha mestra incorreta

Troque temporariamente o valor no botão Authorize por uma senha incorreta. Consulte um segredo existente pelo GET individual. Resultado esperado: HTTP 401, sem conteúdo do segredo. Salve `02-senha-incorreta.png` e restaure a senha correta.

## Teste 3 Conteúdo visível no banco

```sql
select titulo, usuario, nonce, criptograma, etiqueta
from public.segredos
where cofre_id = 'ID_DO_COFRE'::uuid;
```

Resultado esperado: título e usuário legíveis, mas a senha aparece somente como criptograma em Base64. O nonce e a etiqueta também estão em Base64. Salve `03-dados-cifrados.png`.

## Teste 4 Adulteração detectada

Altere o primeiro caractere do criptograma do segredo A. O CASE garante que o valor realmente mude:

```sql
update public.segredos
set criptograma =
  (case when left(criptograma, 1) = 'A' then 'B' else 'A' end)
  || substring(criptograma from 2)
where cofre_id = 'ID_DO_COFRE'::uuid
  and id = 'ID_DO_SEGREDO_A'::uuid;
```

Consulte o segredo A com a senha-mestra correta. Resultado esperado: HTTP 500 com `registro adulterado`, sem texto claro. Salve `04-adulteracao.png`.

Antes de prosseguir, use PUT no segredo A para substituir a senha fictícia. Essa operação gera uma nova cifragem válida. Confirme que a leitura volta a funcionar.

## Teste 5 Troca de criptogramas detectada

Copie somente nonce, criptograma e etiqueta do segredo A para o segredo B:

```sql
update public.segredos as destino
set nonce = origem.nonce,
    criptograma = origem.criptograma,
    etiqueta = origem.etiqueta
from public.segredos as origem
where origem.cofre_id = 'ID_DO_COFRE'::uuid
  and destino.cofre_id = origem.cofre_id
  and origem.id = 'ID_DO_SEGREDO_A'::uuid
  and destino.id = 'ID_DO_SEGREDO_B'::uuid;
```

Consulte o segredo B pela API com a senha correta. Resultado esperado: HTTP 500 com `registro adulterado`, pois o AAD do segredo B difere do utilizado na cifragem original. Salve `05-troca-de-registros.png`.

## Registrar a entrega

Atualize `resultados.md` com a data, resultado observado de cada teste e o nome da evidência correspondente. Não marque um teste real como concluído apenas porque o teste local passou. Os registros descartáveis podem ser removidos depois de guardar as evidências.
