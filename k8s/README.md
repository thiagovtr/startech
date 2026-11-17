# Kubernetes — StarTech

Manifestos declarativos da stack completa, no namespace `startech`. Os nomes dos Services são os mesmos hosts do `compose.yaml` (`rabbitmq`, `keycloak`, `gateway`, `ms-doadores:8081`, `ms-agendamentos:8082`, `ms-hemocentros:8000`, `ms-orquestrador:8003`, `ms-comunicacao:8004`, `bff-mobile:8001`, `bff-web:8002`, `ollama:11434`, `db-*`, `mongo`). Por isso nenhuma configuração dos serviços muda entre Compose e Kubernetes.

| Pasta / arquivo | Conteúdo |
| --- | --- |
| `base/namespace.yaml` | Namespace `startech` |
| `base/secrets-dev3.yaml`, `base/secrets-dev4.yaml` | Secrets com credenciais e URLs com senha (**valores só de desenvolvimento**, iguais ao `.env.example`) |
| `databases/` | StatefulSet + Service headless + volume (1 Gi) para cada PostgreSQL (`db-keycloak`, `db-doadores`, `db-agendamentos`, `db-hemocentros`, `db-orquestrador`, `db-comunicacao`), o MongoDB e o RabbitMQ |
| `services/<serviço>.yaml` | ConfigMap + Deployment + Service (ClusterIP) de cada serviço |
| `services/ms-hemocentros-hpa.yaml` | HPA de 1 a 3 réplicas por CPU (demonstração de escalabilidade) |
| `services/ollama.yaml` | StatefulSet do Ollama (volume de 4 Gi para os modelos) + Job `ollama-pull` |
| `ingress.yaml` | Ingress-NGINX (`startech.local`) → **somente o Gateway** |

## Topologia

```
Ingress (startech.local) ──> gateway:8080 ──┬─> bff-mobile:8001 ─┬─> ms-hemocentros ─> db-hemocentros, mongo
                                            │                    ├─> ms-doadores ────> db-doadores
                                            │                    └─> ms-orquestrador ─> db-orquestrador
                                            ├─> bff-web:8002 ───> ms-hemocentros      ├─> ms-agendamentos ─> db-agendamentos
                                            └─> keycloak:8080 ──> db-keycloak         └─> (RabbitMQ) ms-comunicacao ─> db-comunicacao
```

Só o Gateway é exposto, porque os BFFs confiam no `X-User-Id` injetado por ele (ADR-005). O RabbitMQ liga o Outbox do `ms-hemocentros` (CQRS) e os do `ms-orquestrador`/`ms-comunicacao` (SAGA).

## Aplicar

Com um cluster local (minikube ou kind) e `kubectl` configurado:

```bash
minikube start --cpus 6 --memory 12g        # o Ollama sozinho usa ~3 GB
minikube addons enable ingress metrics-server
scripts/k8s-aplicar.sh                      # build + load das imagens, apply em ordem e espera Ready
echo "$(minikube ip) startech.local" | sudo tee -a /etc/hosts
scripts/k8s-fumaca.sh                       # token -> /api/mobile/home -> SAGA até o fim
```

- Com kind: `CLUSTER=kind KIND_NOME=<nome> scripts/k8s-aplicar.sh`. Sem o Ingress configurado, use `kubectl -n startech port-forward svc/gateway 8080` e `BASE=http://localhost:8080 scripts/k8s-fumaca.sh`.
- Pouca memória: `SEM_OLLAMA=1 scripts/k8s-aplicar.sh` (a IA fica de fora).
- Para reaplicar sem reconstruir as imagens: `SEM_BUILD=1`.

## O que esperar de cada serviço

- **Probes:**
  - Python: liveness em `/health` (sempre 200) e readiness em `/ready`. O `ms-hemocentros` só fica Ready com PostgreSQL e MongoDB; o `ms-orquestrador` e o `ms-comunicacao`, com o PostgreSQL; os BFFs, sempre.
  - Java (`ms-doadores`, `ms-agendamentos`): `/health` e `/ready`, com 30 s de atraso inicial pela subida da JVM. O Gateway usa `/health` nas duas probes.
  - Keycloak: `startupProbe` em `/health/started` na porta de management 9000, com até 3 min para importar o realm na primeira subida.
- **Sem `CrashLoopBackOff` por dependência fora:** os serviços Python sobem sem banco ou broker (as migrações são retentadas e o Outbox espera). Só não sobem se faltar o Secret, porque as URLs com senha não têm padrão no código.
- **Segurança:** todos os serviços próprios rodam como não-root (uid 10001; o Keycloak, 1000), sem escalada de privilégio e com `capabilities: drop ALL`. Os serviços próprios também têm sistema de arquivos somente leitura, com `/tmp` em `emptyDir`. O Keycloak fica sem `readOnlyRootFilesystem`, porque grava em `data/`.
- **SAGA:** o ConfigMap do orquestrador usa `ORQUESTRADOR_PASSO3_AGUARDAR_RESPOSTA: "true"` (resposta real do `ms-comunicacao`). Enquanto os endpoints da SAGA nos serviços Java não existirem (Dev 2), as SAGAs terminam recusadas ou compensadas, sem ficar presas.

## Demonstração de escalabilidade

```bash
kubectl -n startech get hpa ms-hemocentros
kubectl -n startech scale deployment ms-hemocentros --replicas=3   # alternativa manual
kubectl -n startech get pods -l app.kubernetes.io/name=ms-hemocentros
kubectl top pods -n startech
```

O `ms-hemocentros` escala horizontalmente para suportar picos de leitura documental sob alerta crítico de sangue O-. Várias réplicas são seguras: o Outbox usa `SKIP LOCKED` e a projeção no MongoDB é idempotente e versionada. `ms-orquestrador` e `ms-comunicacao` também aceitam réplicas (`SKIP LOCKED`, inbox idempotente, lock otimista), mas ficam com 1 por padrão. Os bancos e o RabbitMQ são StatefulSets de 1 réplica: escalam verticalmente ou por pool de conexões.

Relatório completo do teste de estresse e escalabilidade com Grafana k6 e HPA: [`docs/escalabilidade/relatorio-escalabilidade-k6.md`](../docs/escalabilidade/relatorio-escalabilidade-k6.md).

## Recursos (requests → limits)

| Componente | CPU | Memória |
| --- | --- | --- |
| Serviços Python | 100m → 500m | 128Mi → 384Mi |
| Serviços Java e Gateway | 100m → 1 | 256Mi → 512Mi |
| Keycloak | 200m → 1 | 512Mi → 768Mi |
| PostgreSQL (cada) | 100m → 500m | 128Mi → 512Mi |
| RabbitMQ | 100m → 1 | 256Mi → 512Mi |
| Ollama | 500m → 4 | 1,5Gi → 4Gi |

## Validação feita

- **Schema:** os 65 recursos passam no schema da API 1.30 (`docker run ghcr.io/yannh/kubeconform:v0.6.7 -strict -summary -kubernetes-version 1.30.0 /k8s`).
- **Cluster (17/11/2026):** minikube v1.39 (Kubernetes 1.37, driver docker, 8 CPUs e 14 GB). `scripts/k8s-aplicar.sh` subiu os 19 pods em `Running`/`Ready` e o Job `ollama-pull` em `Completed`. `INGRESS_IP=$(minikube ip) scripts/k8s-fumaca.sh` passou pelo Ingress `startech.local`:
  - token do Keycloak;
  - `/api/mobile/home` com o perfil do doador;
  - SAGA até o fim (`RECUSADO`, porque os endpoints da SAGA nos serviços Java ainda não existem);
  - assistente respondendo com `RAG`.
  
  O `kubectl scale deployment ms-hemocentros --replicas=3` levou a 3 réplicas `Ready`.
- **Problema encontrado e corrigido:** o Kubernetes injeta variáveis `<SERVICE>_PORT=tcp://...` para cada Service do namespace. O Service `bff-mobile` gerava `BFF_MOBILE_PORT`, que colidia com a configuração do BFF (`CrashLoopBackOff`). Todos os pods usam `enableServiceLinks: false`.
- **Sem `kubectl` no PATH:** os scripts usam o embutido no minikube (`minikube kubectl --`). Sem editar o `/etc/hosts`, `INGRESS_IP=$(minikube ip)` faz o curl resolver `startech.local`.
