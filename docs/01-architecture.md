# 01 — Arquitectura

## 1. Posición de esta demo en la plataforma

Hay dos planos que no se deben mezclar:

| Plano | Repositorio | Qué declara |
| --- | --- | --- |
| **Plataforma MaaS** | [`rhoai-gitops`](https://github.com/abelluque/rhoai-gitops/tree/rhoai-maas-demo-platform) (rama `rhoai-maas-demo-platform`) | Operadores, Gateway API, Kuadrant/Authorino, `maas-api`, `LLMInferenceService` Granite, suscripciones |
| **Aplicación agéntica** | este repo (`rhoai-granite-code-demo`) | LibreChat, Llama Stack, orquestador, MCP tools, sample-app de QA |

La guía [RHOAI Models-as-a-Service](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/index.html) describe las fases 1–6 de la plataforma (prerrequisitos → modelo → verificación). Esta demo asume esas fases **completadas**. Consume Granite como un tenant más del gateway.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  Clientes de inferencia  (LibreChat, SDK OpenAI, curl, Dashboard RHOAI)  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │ HTTPS  Bearer sk-oai-…
┌──────────────────────────────────────────────────────────────────────────┐
│  Gateway MaaS  maas.<apps-domain>                                        │
│  Route → GatewayClass openshift-default → RHCL / Authorino / Limitador   │
└──────────────────────────────────────────────────────────────────────────┘
          │                                         │
          ▼                                         ▼
┌─────────────────────────┐           ┌────────────────────────────────────┐
│  maas-api + PostgreSQL  │           │  LLMInferenceService               │
│  API keys, /v1/models   │           │  granite-3-0-8b-instruct (vLLM)    │
└─────────────────────────┘           └────────────────────────────────────┘
```

En laboratorio (overlay `opentlc`) el modelo es **Granite 3.1 2B Instruct en CPU**. En producción (`ocpai-prd-mtz`) es **Granite 3.0 8B Instruct en GPU H200**, con Qwen2.5-Coder y DeepSeek-Coder en tier premium. La demo usa el modelo **free** (Granite) para el razonamiento del agente; no requiere el tier premium.

## 2. Flujo agéntico

```text
               [ Desarrollador ]
                       │
                       ▼
                 [ LibreChat ]
                       │  /v1/chat/completions
                       ▼
          [ Orchestrator  :8080 ]
          (adaptador LibreChat ↔ agentes)
                       │
                       ▼
          [ Llama Stack  :8321  |  distribution rh-dev ]
                       │
       ┌───────────────┼──────────────────────────┐
       ▼               ▼                          ▼
[ Code Agent ]  [ GitHub Agent ]        [ Deploy Agent ]
 tools: AST      tools: GitHub PR       tools: Argo CD + oc
       │               │                          │
       └───────────────┴──────────────────────────┘
                       │
                       ▼
             [ RHOAI MaaS — IBM Granite ]
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  [ GitHub Repos ] [ Argo CD ] [ OpenShift QA ]
```

### Por qué un orquestador además de Llama Stack

LibreChat habla **Chat Completions** OpenAI-compatible. Llama Stack en RHOAI 3.4 expone Chat Completions y, en Developer Preview, Agents / Responses API. El servicio `orchestrator`:

1. Recibe el turno de LibreChat (`POST /v1/chat/completions`).
2. Ejecuta el pipeline multi-agente (Code → GitHub → Deploy) usando Granite vía MaaS.
3. Invoca las herramientas MCP/REST con allowlists.
4. Devuelve un único mensaje de resumen (código, URL del PR, salud de Pods) que LibreChat renderiza.

Llama Stack sigue siendo el runtime oficial de agentes (`LlamaStackDistribution`, toolgroups `remote::model-context-protocol`). El orquestador es el **adaptador de UI**, no un segundo plano de inferencia.

## 3. Componentes en el namespace `demo-granite`

| Workload | Imagen / CR | Puerto | Función |
| --- | --- | --- | --- |
| `llamastack` | `LlamaStackDistribution` `rh-dev` | 8321 | Orquestación de agentes, registro MCP |
| `llamastack-postgres` | PostgreSQL 16 | 5432 | Metadatos de Llama Stack |
| `orchestrator` | UBI Python (este repo) | 8080 | Pipeline E2E + API OpenAI-compatible |
| `mcp-ast`, `mcp-github`, `mcp-argocd`, `mcp-ocp` | UBI Python (este repo) | 8000 | Herramientas con REST + MCP SSE |
| `librechat` | LibreChat | 3080 | UI |
| `librechat-mongo` | MongoDB 7 | 27017 | Persistencia de conversaciones |

El clúster **QA** no ejecuta Granite. Solo ejecuta `sample-app` (namespace `orders-qa`), sincronizado por Argo CD. El agente Deploy usa un kubeconfig de ese clúster (Secret, no Git).

## 4. Modelo de confianza

```text
LibreChat  ──(red cluster)──►  Orchestrator
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              MaaS API key    GitHub token   Argo CD token
              (Secret)        (Secret)       + kubeconfig QA
```

- Granite **nunca** ve los tokens de GitHub/Argo/oc: el modelo solo recibe código y descripciones; las tools firman las llamadas.
- Cada tool tiene allowlist (`ALLOWED_REPOS`, `ALLOWED_ARGOCD_APPS`, `ALLOWED_NAMESPACES`).
- `DRY_RUN=true` por defecto: las mutaciones se registran y se devuelve un payload simulado.
- La API key MaaS (`sk-oai-…`) autentica **solo** inferencia. No abre GitHub ni el clúster QA.

## 5. Relación con sync-waves de la plataforma

La plataforma GitOps instala MaaS en waves −1…7 (cert-manager → RHCL → Gateway → Postgres → RHOAI → `llmisvc-*` → `maas-subscriptions`). Esta demo es una **Application hija posterior** (wave 20, proyecto `demo-granite`). No declara `DataScienceCluster`, ni Gateway, ni `LLMInferenceService` de Granite: asume que ya están `Synced/Healthy`.

Si se necesita un overlay de referencia del modelo (documentación, no fuente de verdad), está en [`gitops/reference/llmisvc-granite.yaml`](../gitops/reference/llmisvc-granite.yaml). El manifiesto canónico vive en `rhoai-gitops`.

Operadores, CRDs y Helm de la capa agéntica: [`docs/06-platform-operators.md`](06-platform-operators.md) y [`platform/`](../platform/README.md). Overlay `gitops/overlays/demo-with-operators` elimina Postgres/Mongo/LibreChat embebidos y apunta Llama Stack al Cluster CNPG.

## 6. Identidad del modelo

| Overlay de plataforma | Recurso | Hardware | Uso en la demo |
| --- | --- | --- | --- |
| `opentlc` | `granite-3-1-2b-instruct` | CPU | Lab / OpenTLC, misma UX, menos calidad de refactor |
| `ocpai-prd-mtz` | `granite-3-0-8b-instruct` | 1× GPU H200, 2 réplicas | Demo recomendada |

El `model` en Chat Completions es el **nombre del `LLMInferenceService`**, no el ID de Hugging Face. Ejemplo: `"model": "granite-3-0-8b-instruct"`.
