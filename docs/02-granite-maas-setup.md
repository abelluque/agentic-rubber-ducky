# 02 — Consumir IBM Granite desde MaaS

Este documento describe cómo **usar** Granite ya publicado por la plataforma, no cómo reinstalar RHOAI. La instalación de MaaS sigue la [guía por fases](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/index.html) y el GitOps [`rhoai-gitops@rhoai-maas-demo-platform`](https://github.com/abelluque/rhoai-gitops/tree/rhoai-maas-demo-platform).

## 1. Comprobar que la plataforma está lista

En el clúster **hub** (kubeconfig de MaaS, no el spoke):

```bash
oc get gateway maas-default-gateway -n openshift-ingress
oc get llminferenceservice -n ai-models
oc get maasmodelref -n ai-models
oc get maassubscription,maasauthpolicy -n models-as-a-service
```

Esperado en producción:

- `LLMInferenceService/granite-3-0-8b-instruct` → `Ready`
- `MaaSModelRef/granite-3-0-8b-instruct` con tier `free`
- `MaaSSubscription/free-models-subscription` incluyendo ese modelo

Lab OpenTLC: sustituir por `granite-3-1-2b-instruct`.

Verificación E2E de la plataforma (simulador CPU, API keys, 401/429): [Phase 6](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/06-verification.html). No sustituye el probe de Granite de esta demo.

## 2. Contrato HTTP

El Ingress Operator publica `maas.<apps-domain>`. El router de KServe reescribe:

```text
/ai-models/granite-3-0-8b-instruct/v1/chat/completions
        →  /v1/chat/completions   (vLLM)
```

Authorino exige `Authorization: Bearer sk-oai-…`. Sin token: 401/403. Cuota de tokens excedida: 429 (Limitador).

Listado de modelos:

```bash
export MAAS_HOST=https://maas.apps.<HUB_DOMAIN>
export MAAS_API_KEY=sk-oai-...
curl -sk -H "Authorization: Bearer ${MAAS_API_KEY}" "${MAAS_HOST}/v1/models"
```

No uses el dominio de aplicaciones del spoke. `./scripts/probe-maas.sh` exige `MAAS_HOST`.

## 3. Crear una API key para la demo

Las keys **no se versionan**. El script [`scripts/create-maas-key.sh`](../scripts/create-maas-key.sh) llama a `POST /maas-api/v1/api-keys` con el token de `oc whoami -t` y la suscripción `free-models-subscription`.

```bash
export KUBECONFIG=/path/to/hub.kubeconfig
export MAAS_HOST=https://maas.apps.<HUB_DOMAIN>
export MAAS_API_KEY=$(./scripts/create-maas-key.sh | jq -r .key)
```

Guardar el valor en el Secret `demo-maas` del namespace `demo-granite` **en el spoke**. El orquestador y Llama Stack lo montan como `MAAS_API_KEY` / `VLLM_API_TOKEN`.

## 4. Probe de inferencia

```bash
export MAAS_HOST=https://maas.apps.<HUB_DOMAIN>
export MAAS_API_KEY=sk-oai-...
./scripts/probe-maas.sh
```

El script envía un `chat/completions` corto. Si responde 200 con `choices[0].message.content`, el plano de inferencia está listo para los agentes.

## 5. Cableado en Llama Stack (distribution `rh-dev`)

RHOAI 3.4 despliega Llama Stack con el CR `LlamaStackDistribution`. El operador resuelve `distribution.name: rh-dev` a la imagen soportada. Variables relevantes para MaaS:

| Variable | Valor |
| --- | --- |
| `VLLM_URL` | `https://maas.apps.<HUB_DOMAIN>/ai-models/granite-3-0-8b-instruct/v1` |
| `INFERENCE_MODEL` | `granite-3-0-8b-instruct` |
| `VLLM_API_TOKEN` | API key MaaS (Secret en el **spoke**) |
| `VLLM_TLS_VERIFY` | `true` si el cert del hub es de confianza; `false` en labs |
| `POSTGRES_*` | CNPG `llamastack-pg` **en el spoke** |

Manifiesto: [`gitops/base/llamastack-distribution.yaml`](../gitops/base/llamastack-distribution.yaml). Configuración de toolgroups MCP: [`llamastack/config.yaml`](../llamastack/config.yaml).

## 6. Por qué no un `InferenceService` v1beta1

El borrador inicial de la demo usaba `serving.kserve.io/v1beta1 InferenceService` con `modelFormat: vLLM`. En esta plataforma el objeto nativo es:

```yaml
apiVersion: serving.kserve.io/v1alpha1
kind: LLMInferenceService
```

con `spec.router.gateway.refs` apuntando a `maas-default-gateway` en `openshift-ingress`, más `MaaSModelRef` y políticas MaaS. Recrear Granite como `InferenceService` clásico **salta** API keys, rate limit y el catálogo. El manifiesto de referencia en `gitops/reference/` documenta el `LLMInferenceService` alineado con `rhoai-gitops`; no se aplica desde el overlay `demo` para no duplicar el modelo.

## 7. Recursos del modelo (producción)

Valores alineados con `clusters/ocpai-prd-mtz` de la plataforma:

| Campo | Valor |
| --- | --- |
| URI | `hf://ibm-granite/granite-3.0-8b-instruct` |
| GPU | 1× `nvidia.com/gpu`, perfil `gpu` en `redhat-ods-applications` |
| CPU / memoria (limits) | 4 CPU / 32Gi |
| Réplicas | 2 (anti-affinity por hostname) |
| Args vLLM | `--max-model-len=4096 --tensor-parallel-size=1` |
| Hugging Face | Secret `hf-token` en `ai-models` (plataforma, no este repo) |

Lab CPU: `VLLM_CPU_KVCACHE_SPACE=4`, sin GPU Operator.

## 8. LibreChat

LibreChat **no** apunta al gateway MaaS directamente. Apunta al orquestador (`http://orchestrator.demo-granite.svc:8080/v1`) para que cada mensaje dispare el pipeline de agentes. Un segundo endpoint opcional (`Granite Chat (MaaS)`) puede apuntar a Llama Stack Chat Completions para conversación sin tools — útil para contrastar “chat” vs “agente” en la misma UI.
