CREATE OR REPLACE TABLE nodes AS SELECT * FROM read_json(
  'output/nodes/*.json',
  columns = {
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))'
  }
);