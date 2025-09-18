CREATE OR REPLACE TABLE groups AS SELECT * FROM read_json(
  'output/group/*.json',
  columns = {
    name: 'VARCHAR',
    api_group: 'VARCHAR',
    uid: 'VARCHAR',
    members: 'VARCHAR[]'
  }
);