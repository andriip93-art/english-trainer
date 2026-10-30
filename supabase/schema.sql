-- English Trainer: cloud progress. Run once in Supabase -> SQL Editor.
-- One row per user. Access is limited to the row owner by RLS.

create table if not exists public.progress (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  state      jsonb       not null default '{}'::jsonb,  -- { srs, log, bullet, wipedAt }
  version    bigint      not null default 0,            -- optimistic concurrency counter
  updated_at timestamptz not null default now()
);

alter table public.progress enable row level security;

create policy "own row: select" on public.progress
  for select using (auth.uid() = user_id);
create policy "own row: insert" on public.progress
  for insert with check (auth.uid() = user_id);
create policy "own row: update" on public.progress
  for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
-- No delete policy on purpose: the app never deletes the row.

-- Keep updated_at honest
create or replace function public.touch_progress() returns trigger
language plpgsql as $$ begin new.updated_at = now(); return new; end $$;
drop trigger if exists progress_touch on public.progress;
create trigger progress_touch before update on public.progress
  for each row execute function public.touch_progress();

-- Safety net: every overwrite is kept in history, so a bad sync can be rolled back.
create table if not exists public.progress_history (
  id         bigserial primary key,
  user_id    uuid not null,
  state      jsonb not null,
  version    bigint not null,
  saved_at   timestamptz not null default now()
);
alter table public.progress_history enable row level security;
create policy "own history: select" on public.progress_history
  for select using (auth.uid() = user_id);

create or replace function public.archive_progress() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  -- at most one snapshot per user per hour
  if not exists (select 1 from public.progress_history
                 where user_id = old.user_id and saved_at > now() - interval '1 hour') then
    insert into public.progress_history(user_id, state, version) values (old.user_id, old.state, old.version);
  end if;
  return new;
end $$;
drop trigger if exists progress_archive on public.progress;
create trigger progress_archive before update on public.progress
  for each row execute function public.archive_progress();
