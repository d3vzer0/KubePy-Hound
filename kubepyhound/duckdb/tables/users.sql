CREATE OR REPLACE TABLE users AS SELECT * FROM read_json(
  'output/user/*.json',
  columns = {
    name: 'VARCHAR',
    api_group: 'VARCHAR',
    uid: 'VARCHAR',
    groups: 'VARCHAR[]'
  }
);