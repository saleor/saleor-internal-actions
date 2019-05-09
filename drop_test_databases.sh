#!/usr/bin/env sh

generate_gateways() {
  local db_name
  local EOF="
  "

  for i in {1..20} ; do
    db_name="\"test_saleor-tenants_gw$i\""
    echo \
        "SELECT pg_terminate_backend(pg_stat_activity.pid)" \
        "FROM pg_stat_activity" \
        "WHERE pg_stat_activity.datname = ${db_name}" \
        "AND pid <> pg_backend_pid();"
    echo "DROP DATABASE ${db_name};"
  done
}

gateways=$(generate_gateways)

drop_dbs() {
  psql postgres://saleor:cloud@localhost:5432/postgres 2>&1 <<EOF
    DROP DATABASE "test_saleor-tenants";
    ${gateways}
EOF
}

drop_dbs | grep -vF "
does not exist
LINE"
