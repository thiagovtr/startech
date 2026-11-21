#!/usr/bin/env bash
# Database per service: um contêiner e um volume por banco, cada serviço com o seu.
source "$(dirname "$0")/comum.sh"

titulo "contêineres de banco"
"${COMPOSE[@]}" ps --format 'table {{.Service}}\t{{.Image}}\t{{.Status}}' | grep -E "SERVICE|^db-|^mongo"
titulo "volumes persistentes"
docker volume ls --format '{{.Name}}' | grep -E "startech_(db-|mongo)" | sed 's/^/   /'
titulo "tabelas de cada banco"
for par in "db-doadores doadores" "db-agendamentos agendamentos" "db-hemocentros hemocentros" \
           "db-orquestrador orquestrador" "db-comunicacao comunicacao"; do
  set -- $par
  echo "   $1: $(sql_valor "$1" "$2" "$2" "SELECT string_agg(tablename, ', ' ORDER BY tablename) FROM pg_tables WHERE schemaname = 'public'")"
done
echo "   mongo (leitura do CQRS do ms-hemocentros): $("${COMPOSE[@]}" exec -T mongo mongosh --quiet hemocentros --eval 'db.getCollectionNames().join(", ")')"
titulo "quem usa cada banco (variáveis de conexão)"
for s in ms-doadores ms-agendamentos ms-hemocentros ms-orquestrador ms-comunicacao; do
  "${COMPOSE[@]}" exec -T "$s" sh -c 'env | grep -E "(DB_URL|POSTGRES_URL|MONGO_URL)=" | sed -E "s#//([^:]+):[^@]*@#//\1:***@#"' \
    | sed "s/^/   $s: /"
done
