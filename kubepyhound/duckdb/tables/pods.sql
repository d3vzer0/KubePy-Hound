CREATE OR REPLACE TABLE pods AS SELECT * FROM read_json(
  'output/namespaces/**/pods/*.json',
  columns = {
    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
    spec: 'STRUCT(node_name VARCHAR, service_account_name VARCHAR, containers STRUCT(image VARCHAR, security_context STRUCT(allow_privilege_escalation BOOLEAN, privileged BOOLEAN), volume_mounts STRUCT(mount_path VARCHAR, name VARCHAR)[])[])'
  }
);