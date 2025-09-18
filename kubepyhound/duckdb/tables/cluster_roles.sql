CREATE OR REPLACE TABLE cluster_roles AS SELECT * FROM read_json(
  'output/cluster_roles/*.json',
  columns = {
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    rules: 'STRUCT(api_groups VARCHAR[], resources VARCHAR[], verbs VARCHAR[], resource_names VARCHAR[])[]'
  }
);