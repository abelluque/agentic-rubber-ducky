# RHOAI Granite Code Demo — agentes DevOps sobre MaaS

Demo de **IA agéntica** sobre **Red Hat OpenShift AI (RHOAI) 3.4** y **Models as a Service (MaaS)**. Un desarrollador describe un cambio en lenguaje natural desde **LibreChat**. **Llama Stack** orquesta tres agentes especializados. El razonamiento y la generación de código los ejecuta **IBM Granite 3.0 8B Instruct**, consumido como modelo de plataforma a través del gateway MaaS (API OpenAI-compatible, API key `sk-oai-…`, rate limiting y políticas de Kuadrant).

Este repositorio **no se instala en el clúster MaaS**. Se despliega en un OpenShift **spoke** y consume el gateway HTTPS del hub:

- Hub (inferencia): [`abelluque/rhoai-gitops`](https://github.com/abelluque/rhoai-gitops/tree/rhoai-maas-demo-platform) (rama `rhoai-maas-demo-platform`)
- Spoke (esta demo): [`abelluque/agentic-rubber-ducky`](https://github.com/abelluque/agentic-rubber-ducky)
- Guía MaaS: [RHOAI Models-as-a-Service Guide](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/index.html)

Detalle multi-clúster: [`docs/07-multi-cluster-maas.md`](docs/07-multi-cluster-maas.md).

## El problema

El inner loop de un servicio Python en OpenShift no es un único ticket: es un flujo fragmentado entre tres planos.

1. **Código** — localizar un hotspot (complejidad, bucles anidados, deuda), reescribirlo y validar sintaxis.
2. **Git** — rama, commit, Pull Request y revisión.
3. **GitOps / clúster** — sincronizar Argo CD y comprobar que los Pods del clúster de QA están `Ready`.

Ese recorrido exige cambiar de contexto (IDE → GitHub → Argo CD → `oc`), copiar URLs y tokens, y suele quedar en manos de quien ya conoce los tres sistemas. El coste no es el LLM: es la orquestación segura de herramientas sobre un modelo **gobernado** (cuotas, identidad, auditoría) y no sobre una API pública.

## La solución

Un asistente DevOps en LibreChat. El usuario pide, en una sola frase, optimizar una función, abrir un PR y desplegar en QA. Llama Stack coordina:

| Agente | Herramienta MCP | Acción |
| --- | --- | --- |
| **Code Agent** | `ast_analyzer` | Parsea el AST de Python, detecta hotspots y pide a Granite la refactorización. Valida que el resultado compile. |
| **GitHub Agent** | `github_tool` | Crea rama, commit y Pull Request en el repositorio allowlisted. |
| **Argo CD & OCP Agent** | `argocd_tool`, `target_ocp_checker` | Sincroniza la Application de Argo CD y consulta el clúster de destino. |

Todas las inferencias pasan por el **gateway MaaS** (`maas.<cluster-domain>`), con `LLMInferenceService/granite-3-0-8b-instruct` en el namespace `ai-models` (tier *free* en el overlay de producción). No hay un vLLM “suelto”: hay suscripción, API key y políticas de Authorino/Limitador.

```text
               [ Desarrollador ]
                       │
                       ▼
         [ SPOKE: LibreChat + Llama Stack + agents ]
                       │  HTTPS Bearer sk-oai-…
                       ▼
         [ HUB: RHOAI MaaS · IBM Granite LLM ]
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  [ GitHub Repos ] [ ArgoCD ] [ OpenShift QA ]
```

## Qué hay en este repositorio

| Ruta | Contenido |
| --- | --- |
| `docs/` | Arquitectura, MaaS remoto, flujo multi-agente, guion, operadores, **multi-clúster**. |
| `gitops/` | Kustomize para LibreChat, Llama Stack (`LlamaStackDistribution` `rh-dev`), orquestador y servidores MCP. |
| `llamastack/` | `run.yaml` y definición de agentes / toolgroups MCP. |
| `librechat/` | Endpoint custom apuntando al orquestador. |
| `mcp-servers/` | Herramientas (AST, GitHub, Argo CD, OpenShift destino) con REST + MCP. |
| `orchestrator/` | Adaptador OpenAI-compatible para LibreChat; pipeline E2E con Granite. |
| `sample-app/` | Microservicio Python **con un hotspot deliberado** que la demo refactoriza y despliega en QA. |
| `scripts/` | API key MaaS, probe de inferencia, despliegue y smoke test. |
| `platform/` | Operadores OLM, CRDs, Helm (LibreChat, CloudNativePG, MongoDB) y operands. |

Por defecto las herramientas corren en **`DRY_RUN=true`**: simulan PR, sync y `oc` sin mutar sistemas reales. La demo en vivo pone `DRY_RUN=false` y allowlists explícitas.

### Operadores y Helm (capa agéntica)

MaaS/Granite viven en el **hub**. En el **spoke** se instalan Llama Stack (OLM community), Postgres, MongoDB y LibreChat:

```bash
# kubeconfig = spoke
./platform/scripts/install-platform.sh
```

Detalle: [`docs/06-platform-operators.md`](docs/06-platform-operators.md), [`docs/07-multi-cluster-maas.md`](docs/07-multi-cluster-maas.md). Overlay: `gitops/overlays/spoke`.

## Prerrequisitos

- **Hub:** OpenShift con RHOAI 3.4 + MaaS y Granite `Ready` ([guía](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/index.html) o `rhoai-gitops`). El gateway `https://maas.apps.<HUB_DOMAIN>` debe ser alcanzable desde el spoke (`:443`).
- **Spoke:** OpenShift **distinto** (4.19+), cluster-admin, `oc`/`helm`/`jq`. No requiere GPU ni el plano MaaS.
- `oc`, `curl`, `jq`. Flujo GitOps completo: token GitHub, token Argo CD del QA, kubeconfig del clúster QA (secrets, no Git).
- En el spoke: operadores de `platform/operators` (Llama Stack community, CloudNativePG, MongoDB Community).

## Arranque rápido

```bash
# A. Hub — emitir API key y probar Granite
export KUBECONFIG=/path/to/hub.kubeconfig
export MAAS_HOST=https://maas.apps.<HUB_DOMAIN>
export MAAS_API_KEY="$(./scripts/create-maas-key.sh | jq -r .key)"
./scripts/probe-maas.sh

# B. Spoke — secretos + stack agéntico
export KUBECONFIG=/path/to/spoke.kubeconfig
cp gitops/base/secrets/demo-secrets.yaml.example /tmp/demo-secrets.yaml
# pegar MAAS_API_KEY en demo-maas.api-key; sustituir CHANGE_ME del overlay spoke
./platform/scripts/install-platform.sh
./scripts/probe-maas-from-spoke.sh
```

Guion de la sesión en [`docs/04-demo-script.md`](docs/04-demo-script.md). Topología hub/spoke en [`docs/07-multi-cluster-maas.md`](docs/07-multi-cluster-maas.md). Arquitectura en [`docs/01-architecture.md`](docs/01-architecture.md).

## Contrato con la plataforma MaaS

El modelo **no** se declara aquí como un `InferenceService` KServe clásico. En RHOAI 3.4 + MaaS el contrato es:

| Recurso | Namespace | Rol |
| --- | --- | --- |
| `LLMInferenceService/granite-3-0-8b-instruct` | `ai-models` | vLLM + llm-d, Gateway `maas-default-gateway` |
| `MaaSModelRef/granite-3-0-8b-instruct` | `ai-models` | Registro del modelo en el catálogo MaaS |
| `MaaSSubscription/free-models-subscription` | `models-as-a-service` | Tier free, rate limit de tokens |
| `MaaSAuthPolicy` | `models-as-a-service` | Authorino valida `Authorization: Bearer sk-oai-…` |

Inferencia:

```text
POST https://maas.<apps-domain>/ai-models/granite-3-0-8b-instruct/v1/chat/completions
Authorization: Bearer sk-oai-<key>
```

La guía oficial de verificación está en [Phase 6: MaaS Verification](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/06-verification.html).

## Estado del repositorio

Remoto: [`abelluque/agentic-rubber-ducky`](https://github.com/abelluque/agentic-rubber-ducky). No hay credenciales en Git.
