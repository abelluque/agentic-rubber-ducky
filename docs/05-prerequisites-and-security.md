# 05 — Prerrequisitos, secretos y seguridad

## Prerrequisitos de plataforma

- OpenShift 4.19+ (producción de referencia: 4.22).
- RHOAI 3.4 con MaaS (Gateway `maas-default-gateway`, Kuadrant, Authorino).
- Granite publicado como `LLMInferenceService` + `MaaSModelRef`.
- Operador Llama Stack (CRD `LlamaStackDistribution`).
- OpenShift GitOps en el **clúster de destino** (Application `orders-qa`), no necesariamente el mismo Argo que reconcilia RHOAI.

No instalar OpenShift Service Mesh 3: el Ingress Operator es el controlador Gateway API (`openshift.io/gateway-controller/v1`). Ver arquitectura de [`rhoai-gitops`](https://github.com/abelluque/rhoai-gitops/tree/rhoai-maas-demo-platform).

## Secretos (nunca en Git)

Partir de [`gitops/base/secrets/demo-secrets.yaml.example`](../gitops/base/secrets/demo-secrets.yaml.example):

| Secret | Claves | Uso |
| --- | --- | --- |
| `demo-maas` | `api-key` | Bearer MaaS (`sk-oai-…`) |
| `demo-github` | `token` | PAT con `contents:write` y `pull_requests:write` en el repo allowlisted |
| `demo-argocd` | `server`, `token` | API de Argo CD del clúster QA |
| `demo-target-kubeconfig` | `kubeconfig` | Kubeconfig **del clúster QA**, cuenta de solo lectura + `get/list` pods |
| `demo-postgres` | `password` | Postgres de Llama Stack |
| `demo-librechat` | `CREDS_KEY`, `JWT_SECRET`, `mongo-uri` | LibreChat |

Crear fuera de banda:

```bash
cp gitops/base/secrets/demo-secrets.yaml.example /tmp/demo-secrets.yaml
# editar
oc apply -f /tmp/demo-secrets.yaml
```

## Allowlists (ConfigMap `demo-pipeline`)

| Variable | Ejemplo | Efecto |
| --- | --- | --- |
| `DRY_RUN` | `true` | No muta GitHub ni Argo |
| `ALLOWED_REPOS` | `myorg/orders` | Único repo en el que el GitHub Agent escribe |
| `ALLOWED_ARGOCD_APPS` | `orders-qa` | Única Application sincronizable |
| `ALLOWED_NAMESPACES` | `orders-qa` | Único namespace consultable en QA |
| `DEFAULT_FILE_PATH` | `sample-app/src/orders/pricing.py` | Archivo del prompt por defecto |
| `DEFAULT_FUNCTION` | `calculate_order_total` | Función objetivo |

Cualquier tool que reciba un repo/app/namespace fuera de lista responde `ok: false` sin llamar a la API externa.

## RBAC del clúster QA

El kubeconfig debe apuntar a un ServiceAccount **restringido** (ejemplo en `gitops/reference/target-cluster-reader.yaml`):

- `get`, `list`, `watch` sobre `pods`, `pods/log`, `deployments`, `replicasets`, `events` en `orders-qa`.
- Sin `create/update/delete`. El cambio de workload lo hace Argo CD, no el agente.

## SCC / OpenShift

LibreChat y MongoDB pueden requerir `anyuid` en `demo-granite` en labs. Preferir imágenes UBI y `restricted-v2` cuando sea posible. Los servidores MCP y el orquestador corren como non-root (UID 1001) en UBI9 Python.

## Datos que ve el modelo

Granite recibe: fuente Python, informe AST, mensajes de error de `compile()`, nombres de Application/namespace. **No** recibe PAT, kubeconfig ni API keys MaaS. Esos valores viven en env de los Pods tool.

## Auditoría mínima

Logs JSON del orquestador (`agent`, `tool`, `ok`, `dry_run`). No registrar cuerpos de secretos ni headers `Authorization`. Rotar la API key MaaS después de demos públicas (la API MaaS permite expiración, p. ej. `expiresIn: 24h`).
