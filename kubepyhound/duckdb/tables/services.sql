CREATE OR REPLACE TABLE services AS SELECT * FROM read_json(
  'output/namespaces/**/services/*.json',
  columns = {
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    spec: 'STRUCT(type VARCHAR, selector MAP(VARCHAR, VARCHAR))'
  }
);