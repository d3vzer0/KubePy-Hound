CREATE OR REPLACE TABLE cluster_role_bindings AS SELECT * FROM read_json(
  'output/cluster_role_bindings/*.json',
  columns = {
    kind: 'VARCHAR',
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    role_ref: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR)',
    subjects: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR, namespace VARCHAR)[]'
  }
);