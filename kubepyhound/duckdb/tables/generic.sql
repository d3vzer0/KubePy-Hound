CREATE OR REPLACE TABLE resources AS SELECT * FROM read_json(
  [
    'output/cluster/**/*.json',
    'output/cluster_roles/**/*.json',
    'output/cluster_role_bindings/**/*.json',
    'output/namespaces/**/*.json',
    'output/unmapped/**/*.json',
    'output/nodes/**/*.json',

  ],
  columns = {
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    kind: 'VARCHAR',
  }
);