# Manifestos do Dev 3 (rascunho para integrar com o Dev 4)

Serviços: `ms-hemocentros` (+ `db-hemocentros`, `mongo`), `ms-orquestrador` (+ `db-orquestrador`), `bff-mobile` e `bff-web`. Namespace `startech`. Ingress, Gateway, Keycloak, RabbitMQ e os serviços Java ficam com o Dev 1, o Dev 2 e o Dev 4.

| Arquivo | Conteúdo |
| --- | --- |
| `base/namespace.yaml` | Namespace `startech` (compartilhado) |
| `base/secrets-dev3.yaml` | Secrets com as URLs com senha e as credenciais dos bancos (**valores só de desenvolvimento**, iguais ao `.env.example`) |
| `databases/db-hemocentros.yaml`, `db-orquestrador.yaml`, `mongo-hemocentros.yaml` | StatefulSet + Service headless + volume persistente (1 Gi) por banco |
| `services/<serviço>.yaml` | ConfigMap + Deployment + Service (ClusterIP) |
| `services/ms-hemocentros-hpa.yaml` | HPA 1→3 réplicas por CPU (demonstração de escalabilidade) |

Os nomes dos Services são os mesmos hosts do Compose (`db-hemocentros`, `mongo`, `ms-hemocentros:8000`, `ms-orquestrador:8003`, `bff-mobile:8001`, `bff-web:8002`), então nenhuma configuração muda entre Compose e Kubernetes.

## Aplicar (minikube)

```bash
for s in ms-hemocentros ms-orquestrador bff-mobile bff-web; do
  docker build -t startech/$s:dev ./$s && minikube image load startech/$s:dev
done
kubectl apply -f k8s/base/
kubectl apply -f k8s/databases/
kubectl apply -f k8s/services/
kubectl -n startech get pods -w
```

## O que esperar de cada serviço

- **Probes:** liveness em `/health` (sempre 200), readiness em `/ready`.
  - `ms-hemocentros`: só fica *Ready* com PostgreSQL e MongoDB no ar.
  - `ms-orquestrador`: só fica *Ready* com o PostgreSQL no ar.
  - BFFs: ficam sempre *Ready* (degradam em vez de cair).
- **Sem `CrashLoopBackOff` por dependência fora:**
  - os serviços sobem mesmo sem banco ou RabbitMQ (as migrações são retentadas e o Outbox espera o broker);
  - só não sobem se faltar o Secret, porque as URLs com senha não têm valor padrão.
- **Dependências de outros Devs:**
  - Service `rabbitmq` na porta 5672 (Dev 1/Dev 4);
  - `ms-doadores:8081` e `ms-agendamentos:8082` (Dev 2).
  - Sem elas, o `bff-mobile` degrada e o orquestrador retenta e depois compensa.
- **Segurança:** os contêineres rodam como não-root (uid 10001 do Dockerfile), sem escalada de privilégio, com sistema de arquivos somente leitura e `/tmp` em `emptyDir`.

## Demonstração de escalabilidade (Etapa 3)

```bash
minikube addons enable metrics-server
kubectl -n startech get hpa ms-hemocentros
kubectl -n startech scale deployment ms-hemocentros --replicas=3   # alternativa manual
kubectl -n startech get pods -l app.kubernetes.io/name=ms-hemocentros
kubectl top pods -n startech
```

Justificativa (plano de ação): o `ms-hemocentros` escala horizontalmente para suportar picos de leitura documental sob alerta crítico de sangue O-. Várias réplicas são seguras: o publicador do Outbox usa `SKIP LOCKED` e a projeção no MongoDB é idempotente e versionada. O `ms-orquestrador` também aceita réplicas (reivindicação com prazo, `SKIP LOCKED`, lock otimista), mas fica com 1 por padrão.

## Validação feita

Os 24 recursos passam no schema da API do Kubernetes 1.30 (`kubernetes-validate --strict`). **Ainda não foram aplicados num cluster**: rode o roteiro acima no minikube antes da apresentação. Se algum serviço falhar por gravar em disco, remova `readOnlyRootFilesystem: true` do Deployment dele.
