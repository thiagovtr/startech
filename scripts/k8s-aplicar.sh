#!/usr/bin/env bash
# Sobe a stack StarTech num cluster Kubernetes local (minikube ou kind), do zero:
#   1. constrói as imagens locais (startech/<serviço>:dev) e as carrega no cluster;
#   2. aplica os manifestos na ordem base -> databases -> services -> ingress;
#   3. espera os pods ficarem Ready.
#
# Uso: scripts/k8s-aplicar.sh                (CLUSTER=minikube, padrão)
#      CLUSTER=kind KIND_NOME=startech scripts/k8s-aplicar.sh
#      SEM_BUILD=1 scripts/k8s-aplicar.sh    (reaplica sem reconstruir as imagens)
#      SEM_OLLAMA=1 scripts/k8s-aplicar.sh   (não sobe o Ollama: economiza ~3 GB de RAM)
set -euo pipefail
cd "$(dirname "$0")/.."

CLUSTER="${CLUSTER:-minikube}"
NS=startech
SERVICOS=(gateway keycloak ms-doadores ms-agendamentos ms-hemocentros ms-orquestrador ms-comunicacao ms-rag bff-mobile bff-web)

carregar() {
  case "$CLUSTER" in
    minikube) minikube image load "$1" ;;
    kind) kind load docker-image "$1" --name "${KIND_NOME:-startech}" ;;
    *) echo "CLUSTER inválido: $CLUSTER (use minikube ou kind)"; exit 1 ;;
  esac
}

if [ "${SEM_BUILD:-0}" != "1" ]; then
  for s in "${SERVICOS[@]}"; do
    echo ">> imagem startech/$s:dev"
    docker build -q -t "startech/$s:dev" "./$s" >/dev/null
    carregar "startech/$s:dev"
  done
fi

echo ">> base (namespace e Secrets)"
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/

echo ">> bancos e broker"
kubectl apply -f k8s/databases/
kubectl -n "$NS" rollout status statefulset --timeout=300s

echo ">> serviços"
for f in k8s/services/*.yaml; do
  [ "${SEM_OLLAMA:-0}" = "1" ] && [ "$(basename "$f")" = "ollama.yaml" ] && continue
  kubectl apply -f "$f"
done
kubectl apply -f k8s/ingress.yaml || echo "   (Ingress não aplicado: habilite o controlador NGINX; ver k8s/README.md)"

echo ">> aguardando os Deployments"
kubectl -n "$NS" rollout status deployment --timeout=600s
[ "${SEM_OLLAMA:-0}" = "1" ] || kubectl -n "$NS" wait --for=condition=complete job/ollama-pull --timeout=900s

kubectl -n "$NS" get pods -o wide
echo ">> pronto. Teste de fumaça: scripts/k8s-fumaca.sh"
