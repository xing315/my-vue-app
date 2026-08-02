-- Public, read-only chart bundles. Writes are performed only by the local secret key.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('quant-stock-charts', 'quant-stock-charts', true, 5242880, array['application/gzip'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Public buckets are readable through Storage's public object URL. No anon write
-- policy is created; service_role/secret-key publication bypasses RLS.
