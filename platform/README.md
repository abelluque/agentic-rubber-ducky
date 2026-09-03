# Platform — operadores, Helm y CRDs

Esta carpeta instala **lo que la demo agéntica necesita en el clúster** y que **no** forma parte del plano MaaS (`rhoai-gitops`):

| Componente | Cómo se instala | Qué aporta |
| --- | --- | --- |
| **Llama Stack Operator** | `DataScienceCluster.llamastackoperator.managementState: Managed` (RHOAI 3.4) | CRD `LlamaStackDistribution` (`llamastack.io/v1alpha1`) |
| **CloudNativePG** | OLM Subscription `cloudnative-pg` | CRD `Cluster` (`postgresql.cnpg.io/v1`) para Postgres de Llama Stack |
| **MongoDB Community Operator** | OLM Subscription `mongodb-community-operator` | CRD `MongoDBCommunity` para LibreChat |
| **LibreChat** | Helm chart local `charts/librechat` | UI, Route, ConfigMap del endpoint Granite |
| **Llama Stack Postgres** | Helm chart `charts/llamastack-postgres` | `Cluster` CNPG `llamastack-pg` |
| **LibreChat MongoDB** | Helm chart `charts/librechat-mongodb` | Replica set de 1 miembro para demos |

No reinstala RHOAI, Gateway MaaS ni Granite. Esos siguen en el GitOps de plataforma.

```text
wave 10  platform/operators     OLM + DSC patch (Llama Stack Operator)
wave 11  wait CRDs              llamastackdistributions, clusters.postgresql.cnpg.io, mongodbcommunity
wave 12  Helm charts            Postgres CNPG + MongoDB + LibreChat
wave 20  gitops/overlays/demo-with-operators
                                LlamaStackDistribution, orchestrator, MCP
```

## Arranque

```bash
# 1. Operadores (cluster-admin)
oc apply -k platform/operators

# 2. Esperar CRDs
./platform/scripts/wait-crds.sh

# 3. Charts / operands (Postgres CNPG, MongoDB, LibreChat)
oc apply -k platform/operands
helm upgrade --install librechat platform/charts/librechat \
  -n demo-granite --create-namespace \
  --set fullnameOverride=librechat \
  --set existingSecret=demo-librechat

# 4. Capa agéntica (apunta a CNPG/Mongo del operador, no a Deployments embebidos)
oc apply -k gitops/overlays/demo-with-operators
```

Atajo: `./platform/scripts/install-platform.sh`

## Rutas

| Ruta | Contenido |
| --- | --- |
| `operators/` | Kustomize: namespaces, OperatorGroups, Subscriptions, Job que activa Llama Stack en el DSC |
| `crds/` | CRD `LlamaStackDistribution` vendorizada (el operador es la fuente de verdad en cluster) |
| `operands/` | CRs de datos: `Cluster` CNPG y `MongoDBCommunity` |
| `charts/` | Helm: operadores (opcional), LibreChat, Postgres, MongoDB, umbrella |
| `gitops/` | Applications Argo CD (waves 10–12) |
| `values/demo.yaml` | Valores del umbrella para esta demo |
| `scripts/` | install + wait CRDs |

Detalle y RBAC: [`docs/06-platform-operators.md`](../docs/06-platform-operators.md).
