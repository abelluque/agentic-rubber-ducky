# 01 — Arquitectura

## 1. Posición de esta demo en la plataforma

Hay **tres** planos. No se mezclan:

| Plano | Dónde | Repositorio | Qué declara |
| --- | --- | --- | --- |
| **Hub MaaS** | Clúster de inferencia | [`rhoai-gitops`](https://github.com/abelluque/rhoai-gitops/tree/rhoai-maas-demo-platform) | Gateway, Kuadrant, `LLMInferenceService` Granite, suscripciones |
| **Spoke agéntico** | OpenShift **distinto** | este repo | LibreChat, Llama Stack `remote-vllm`, orquestador, MCP, operadores |
| **QA** | Opcional, tercer clúster | `sample-app/gitops` | App `orders-qa` |

La demo asume el hub **ya** sirve Granite. El spoke es un cliente HTTPS (`MAAS_HOST` + `sk-oai-…`). Ver [`07-multi-cluster-maas.md`](07-multi-cluster-maas.md).

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

## 5. Relación con el hub GitOps

La plataforma MaaS en el hub usa waves −1…7. **Este repo no se aplica allí.** En el spoke, Argo CD (`platform/gitops`) usa waves 10–20 sobre `kubernetes.default.svc` del spoke. No declara `DataScienceCluster` de MaaS, ni Gateway, ni `LLMInferenceService`.

El manifiesto de referencia del modelo (solo documentación del hub) está en [`gitops/reference/llmisvc-granite.yaml`](../gitops/reference/llmisvc-granite.yaml).

Operadores del spoke: [`docs/06-platform-operators.md`](06-platform-operators.md). Overlay: `gitops/overlays/spoke`.

## 6. Identidad del modelo

| Overlay de plataforma | Recurso | Hardware | Uso en la demo |
| --- | --- | --- | --- |
| `opentlc` | `granite-3-1-2b-instruct` | CPU | Lab / OpenTLC, misma UX, menos calidad de refactor |
| `ocpai-prd-mtz` | `granite-3-0-8b-instruct` | 1× GPU H200, 2 réplicas | Demo recomendada |

El `model` en Chat Completions es el **nombre del `LLMInferenceService`**, no el ID de Hugging Face. Ejemplo: `"model": "granite-3-0-8b-instruct"`.
