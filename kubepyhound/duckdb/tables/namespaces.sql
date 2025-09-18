CREATE OR REPLACE TABLE namespaces AS SELECT * FROM read_json(
  'output/namespaces/*.json',
  columns = {
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))'
  }
);