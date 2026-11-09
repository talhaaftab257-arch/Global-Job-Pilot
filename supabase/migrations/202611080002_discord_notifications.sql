alter table public.job_preferences
  add column if not exists discord_enabled boolean not null default false;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'job_preferences' and column_name = 'telegram_enabled'
  ) then
    update public.job_preferences set discord_enabled = telegram_enabled;
  end if;
end $$;

alter table public.job_preferences
  drop column if exists telegram_enabled;

alter table public.notifications
  drop constraint if exists notifications_channel_check;

update public.notifications
set channel = 'legacy'
where channel = 'telegram';

alter table public.notifications
  add constraint notifications_channel_check
  check (channel in ('discord', 'email', 'legacy'));
