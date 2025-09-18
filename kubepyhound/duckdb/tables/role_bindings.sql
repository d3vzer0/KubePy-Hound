CREATE OR REPLACE TABLE role_bindings AS SELECT * FROM read_json(
  'output/namespaces/**/role_bindings/*.json',
  columns = {
    kind: 'VARCHAR',
    subjects: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR, namespace VARCHAR)[]',
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    role_ref: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR)'
  }
);