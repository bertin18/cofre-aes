# AGENTS.md

## Context
- Leia somente arquivos necessários para a tarefa.
- Comece pela menor área possível e expanda apenas quando necessário.
- Não analise o projeto inteiro sem justificativa.
- Não repita código não alterado.
- Faça mudanças pequenas e localizadas.
- Não refatore código fora do escopo.
- Use documentação externa somente quando necessário confirmar APIs ou versões.

## Frontend
- Reutilize componentes existentes antes de criar novos.
- Prefira HTML semântico e acessível.
- Preserve o design system existente.
- Minimize estado global e JavaScript desnecessário.
- Evite dependências quando recursos nativos ou existentes forem suficientes.
- Mantenha responsividade e acessibilidade.

## Organization
- Preserve a arquitetura existente.
- Organize código por responsabilidade/domínio.
- Evite duplicação e abstrações prematuras.
- Remova imports, código morto e logs temporários.
- Use nomes que expressem intenção.

## Documentation
- Atualize README/docs somente quando a mudança afetar uso, instalação,
  configuração, API ou arquitetura.
- Comentários devem explicar "por quê", não repetir o código.
- Não documente código trivial.

## Security
- Nunca exponha secrets, tokens, senhas ou credenciais.
- Considere todo código frontend público.
- Não armazene dados sensíveis em localStorage.
- Não confie apenas em validação frontend.
- Evite innerHTML, eval e execução dinâmica.
- Não enfraqueça autenticação, CORS, TLS ou validações para corrigir erros.
- Verifique dependências antes de adicioná-las.

## Before finishing
- Revise o diff.
- Execute testes/lint/typecheck relevantes.
- Confirme que somente arquivos necessários foram alterados.
- Verifique secrets, logs e código temporário.