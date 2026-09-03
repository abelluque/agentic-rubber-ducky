# RHOAI Granite Code Demo — agentes DevOps sobre MaaS

Demo de **IA agéntica** sobre **Red Hat OpenShift AI (RHOAI) 3.4** y **Models as a Service (MaaS)**. Un desarrollador describe un cambio en lenguaje natural desde **LibreChat**. **Llama Stack** orquesta tres agentes especializados. El razonamiento y la generación de código los ejecuta **IBM Granite 3.0 8B Instruct**, consumido como modelo de plataforma a través del gateway MaaS (API OpenAI-compatible, API key `sk-oai-…`, rate limiting y políticas de Kuadrant).

Este repositorio **no reinstala la plataforma MaaS**. Consume el plano de inferencia declarado en:

- GitOps de plataforma: [`abelluque/rhoai-gitops`](https://github.com/abelluque/rhoai-gitops/tree/rhoai-maas-demo-platform) (rama `rhoai-maas-demo-platform`)
- Guía de despliegue: [RHOAI Models-as-a-Service Guide](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/index.html)

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
                 [ LibreChat ]
                       │  OpenAI-compatible
                       ▼
          [ Orchestrator / Llama Stack ]
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
[ Code Agent ]  [ GitHub Agent ]  [ ArgoCD & OCP Agent ]
       │               │               │
       └───────────────┴───────────────┘
                       │
                       ▼
             [ RHOAI MaaS Platform ]
         (Inferencia: IBM Granite LLM)
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  [ GitHub Repos ] [ ArgoCD ] [ OpenShift Target Cluster ]
```

## Qué hay en este repositorio

| Ruta | Contenido |
| --- | --- |
| `docs/` | Arquitectura, consumo de Granite vía MaaS, flujo multi-agente, guion de demo y seguridad. |
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

MaaS/Granite ya están en el GitOps de plataforma. Lo que falta en el cluster para esta demo (Llama Stack Operator, Postgres, MongoDB, LibreChat) está en [`platform/`](platform/README.md):

```bash
./platform/scripts/install-platform.sh
```

Detalle: [`docs/06-platform-operators.md`](docs/06-platform-operators.md). Overlay que consume esos operadores: `gitops/overlays/demo-with-operators`.

## Prerrequisitos

- Clúster OpenShift **4.19+** con RHOAI **3.4** y MaaS ya instalados (GitOps de plataforma o [guía MaaS](https://rh-aiservices-bu.github.io/rhoai-maas-guide/modules/main/index.html)).
- `LLMInferenceService` Granite listo (`granite-3-0-8b-instruct` en GPU, o `granite-3-1-2b-instruct` en lab CPU).
- `oc`, `curl`, `jq`. Para el flujo completo: token GitHub, token Argo CD y kubeconfig del clúster QA (secrets, no Git).
- Operador **Llama Stack**: se activa con `platform/operators` (`llamastackoperator: Managed` en el DSC). Distribution `rh-dev`.
- Ruta con operadores: CloudNativePG, MongoDB Community (OLM) y el chart Helm de LibreChat (`./platform/scripts/install-platform.sh`).

## Arranque rápido

```bash
# 1. Autenticarse en el clúster hub (donde vive MaaS)
oc whoami

# 2. Comprobar Granite a través del gateway MaaS
./scripts/probe-maas.sh
MODEL=granite-3-0-8b-instruct ./scripts/probe-maas.sh

# 3. Crear una API key de suscripción free (no se versiona)
./scripts/create-maas-key.sh

# 4. Rellenar secretos a partir de los ejemplos
cp gitops/base/secrets/demo-secrets.yaml.example /tmp/demo-secrets.yaml
# editar /tmp/demo-secrets.yaml  →  oc apply -f /tmp/demo-secrets.yaml

# 5. Desplegar la capa agéntica
oc apply -k gitops/overlays/demo
```

Guion de la sesión en [`docs/04-demo-script.md`](docs/04-demo-script.md). Arquitectura detallada en [`docs/01-architecture.md`](docs/01-architecture.md).

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
