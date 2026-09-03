# 07 — Multi-clúster: spoke consume MaaS del hub

Este repositorio se despliega en un OpenShift **distinto** del que declara [`rhoai-gitops@rhoai-maas-demo-platform`](https://github.com/abelluque/rhoai-gitops/tree/rhoai-maas-demo-platform). El hub **sirve** Granite. El spoke **consume** el gateway HTTPS de MaaS. No se copian `LLMInferenceService`, Gateway, Kuadrant ni suscripciones MaaS al spoke.

```text
┌─────────────────────────────────────────────────────────────────┐
│  HUB  (rhoai-gitops)                                            │
│  RHOAI 3.4 · MaaS · LLMInferenceService granite-3-0-8b-instruct │
│  https://maas.apps.<HUB_DOMAIN>/ai-models/.../v1                │
│  Authorino: Bearer sk-oai-… · rate limit · /maas-api            │
└─────────────────────────────────────────────────────────────────┘
                    │ HTTPS :443  (internet / red corporativa)
                    │ Authorization: Bearer sk-oai-<key>
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  SPOKE  (este repo · agentic-rubber-ducky)                      │
│  LibreChat · Llama Stack (remote-vllm) · orchestrator · MCP     │
│  CloudNativePG · MongoDB Community · OpenShift GitOps           │
│  Sin GPU de inferencia. Sin DataScienceCluster de MaaS.         │
└─────────────────────────────────────────────────────────────────┘
                    │ kubeconfig / Argo CD token (opcional)
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  QA (opcional, tercer clúster)                                  │
│  sample-app / Application Argo CD orders-qa                     │
└─────────────────────────────────────────────────────────────────┘
```

## Qué corre en cada clúster

| Clúster | Kubeconfig | Qué se aplica |
| --- | --- | --- |
| **Hub** | Solo para emitir la API key MaaS y probar Granite | Nada de este repo |
| **Spoke** | Contexto por defecto de `install-platform.sh` | `platform/operators`, operands, LibreChat, `gitops/overlays/spoke` |
| **QA** | Secret `demo-target-kubeconfig` en el spoke | `sample-app/gitops` vía Argo CD del QA |

## Red

Los pods `orchestrator` y `llamastack` en `demo-granite` deben resolver y alcanzar `maas.apps.<HUB_DOMAIN>:443`. Si el hub usa certificados del Ingress interno, o bien:

- `MAAS_TLS_VERIFY=false` (labs), o
- montar la CA del hub en los pods (no está en el overlay por defecto).

No hace falta Service Mesh ni un Gateway MaaS en el spoke. El tráfico es un cliente OpenAI-compatible hacia una Route/Gateway **externa**.

Comprobar desde una workstation que vea el hub (no hace falta `oc` del spoke):

```bash
export MAAS_HOST=https://maas.apps.<HUB_DOMAIN>
export MAAS_API_KEY=sk-oai-...
./scripts/probe-maas.sh
```

Desde el spoke, el mismo `MAAS_HOST` (el dominio **del hub**, nunca `oc get ingresses` del spoke):

```bash
./scripts/probe-maas-from-spoke.sh
```

## API key

La key se crea **en el hub** (usuario con acceso a `POST /maas-api/v1/api-keys`):

```bash
export KUBECONFIG=/path/to/hub.kubeconfig
export MAAS_HOST=https://maas.apps.<HUB_DOMAIN>
./scripts/create-maas-key.sh
```

Copiar `key` al Secret `demo-maas` **del spoke** (`oc --context spoke apply -f /tmp/demo-secrets.yaml`). El spoke no habla con `maas-api` para emitir keys: solo usa el Bearer en Chat Completions.

Suscripción de referencia en el hub: `free-models-subscription` (Granite 8B). El grupo del usuario que crea la key debe coincidir con la `MaaSSubscription` / `MaaSAuthPolicy` del hub.

## Overlay y operadores en el spoke

| Recurso | Ruta | Notas |
| --- | --- | --- |
| Operadores OLM | `platform/operators` | Llama Stack **community** + CNPG + MongoDB. **No** parchea `DataScienceCluster`. |
| CRs de datos | `platform/operands` | Postgres Llama Stack, Mongo LibreChat |
| Agentes + LSD | `gitops/overlays/spoke` | `distribution.name: remote-vllm`, `VLLM_URL` = gateway del hub |
| Argo CD Applications | `platform/gitops` | `destination.server: https://kubernetes.default.svc` = **spoke** |

Si el spoke **ya** tiene OpenShift AI y se prefiere el operador in-tree:

```bash
oc apply -k platform/operators-with-rhoai
```

Ese overlay **elimina** la Subscription community y activa `llamastackoperator: Managed`. No mezclar ambos.

## Qué no instalar en el spoke

- Charts/apps de `rhoai-gitops` (RHOAI DSC de MaaS, `llmisvc-*`, `maas-subscriptions`, Gateway `maas-default-gateway`)
- GPU Operator solo para esta demo (no hay inferencia local)
- Service Mesh 3

## Sustituir el hostname del hub

En `gitops/overlays/spoke/kustomization.yaml` y `gitops/overlays/demo-with-operators/kustomization.yaml`, reemplazar `maas.apps.CHANGE_ME.example.com` por el hostname real del Route/Gateway MaaS del hub:

```bash
oc --kubeconfig hub.kubeconfig get route -n openshift-ingress | grep maas
# o
oc --kubeconfig hub.kubeconfig get ingresses.config/cluster -o jsonpath='{.spec.domain}'
```

El host suele ser `https://maas.apps.<domain>`.
