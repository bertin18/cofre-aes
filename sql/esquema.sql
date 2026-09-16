-- Execute UMA VEZ em um projeto Supabase novo e exclusivo da equipe.
begin;

create table public.cofres (
  id uuid primary key,
  nome text not null,
  kdf_sal text not null,
  kdf_iteracoes integer not null check (kdf_iteracoes between 210000 and 2000000),
  verificador_nonce text not null,
  verificador_criptograma text not null,
  verificador_etiqueta text not null,
  criado_em timestamptz not null default now()
);

create table public.segredos (
  id uuid primary key,
  cofre_id uuid not null references public.cofres(id) on delete cascade,
  titulo text not null,
  usuario text,
  url text,
  nonce text not null,
  criptograma text not null,
  etiqueta text not null,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);

create index idx_segredos_cofre on public.segredos(cofre_id);
alter table public.cofres enable row level security;
alter table public.segredos enable row level security;

-- Políticas amplas exigidas pelo laboratório. Não usar com credenciais reais.
grant usage on schema public to anon;
grant select, insert, update, delete on public.cofres, public.segredos to anon;
create policy "laboratorio" on public.cofres
  for all to anon using (true) with check (true);
create policy "laboratorio" on public.segredos
  for all to anon using (true) with check (true);

commit;
