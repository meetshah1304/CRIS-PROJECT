create extension if not exists vector;

create table if not exists fir_documents (
  doc_id text primary key,
  file_name text not null,
  source_path text not null,
  file_type text not null,
  file_hash text,
  last_modified timestamptz,
  processing_status text default 'pending',
  raw_text text,
  ocr_confidence double precision,
  parser_confidence double precision,
  page_count integer,
  extraction_method text,
  extraction_notes jsonb default '[]'::jsonb,
  fir_number text,
  police_station text,
  district text,
  state text,
  incident_date text,
  report_date text,
  crime_type text,
  ipc_sections jsonb default '[]'::jsonb,
  accused_names jsonb default '[]'::jsonb,
  victim_names jsonb default '[]'::jsonb,
  witness_names jsonb default '[]'::jsonb,
  locations jsonb default '[]'::jsonb,
  evidence_items jsonb default '[]'::jsonb,
  narrative_summary text,
  embedding vector(1024),
  created_at timestamptz default now()
);

create table if not exists fir_feature_rows (
  doc_id text primary key references fir_documents(doc_id) on delete cascade,
  crime_type text,
  police_station text,
  district text,
  incident_date text,
  entity_count integer default 0,
  location_count integer default 0,
  section_count integer default 0,
  narrative_length integer default 0,
  link_signature text,
  created_at timestamptz default now()
);

create table if not exists fir_relationship_edges (
  edge_id bigserial primary key,
  source_doc_id text references fir_documents(doc_id) on delete cascade,
  target_doc_id text references fir_documents(doc_id) on delete cascade,
  edge_weight double precision not null,
  reasons text,
  created_at timestamptz default now()
);

create or replace function match_fir_documents (
  query_embedding vector(1024),
  match_threshold float,
  match_count int
)
returns table (
  doc_id text,
  crime_type text,
  similarity float
)
language sql
as $$
  select
    fir_documents.doc_id,
    fir_documents.crime_type,
    1 - (fir_documents.embedding <=> query_embedding) as similarity
  from fir_documents
  where 1 - (fir_documents.embedding <=> query_embedding) > match_threshold
  order by fir_documents.embedding <=> query_embedding
  limit match_count;
$$;
