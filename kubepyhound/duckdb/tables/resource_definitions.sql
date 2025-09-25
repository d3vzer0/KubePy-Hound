CREATE OR REPLACE TABLE resource_definitions AS SELECT * FROM read_json(
  [ 'output/resource_definitions/**/*.json',
    'output/custom_resource_definitions/**/*.json',
  ],
  columns = {
    name: 'VARCHAR',
    categories: 'VARCHAR[]',
    kind: 'VARCHAR',
    'group': 'VARCHAR',
    singular_name: 'VARCHAR',
    namespaced: 'BOOLEAN',
    uid: 'VARCHAR',
    api_group_name: 'VARCHAR',
    api_group_uid: 'VARCHAR'
  }
);