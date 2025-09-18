CREATE OR REPLACE TABLE api_groups AS SELECT * FROM read_json(
  'output/api_groups/*.json',
  columns = {
    name: 'VARCHAR',
    api_version: 'VARCHAR',
    preferred_version: 'STRUCT(group_version VARCHAR, version VARCHAR)',
    versions: 'STRUCT(group_version VARCHAR, version VARCHAR)[]',
    uid: 'VARCHAR'
  }
);