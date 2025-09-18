CREATE OR REPLACE TABLE roles AS SELECT * FROM read_json(
  'output/namespaces/**/roles/*.json',
  columns = {
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    rules: 'STRUCT(api_groups VARCHAR[], resources VARCHAR[], verbs VARCHAR[], resource_names VARCHAR[])[]'
  }
);