CREATE OR REPLACE TABLE serviceaccounts AS SELECT * FROM read_json(
  'output/namespaces/**/serviceaccounts/*.json',
  columns = {
    kind: 'VARCHAR',
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    automount_service_account_token: 'BOOLEAN',
    secrets: 'STRUCT(name VARCHAR)[]',
    exists: 'BOOLEAN'
  }
);