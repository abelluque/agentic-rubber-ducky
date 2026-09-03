# 03 — Flujo multi-agente

## 1. Objetivo de una sesión

El desarrollador, en LibreChat, pide en un solo turno:

> Optimiza `calculate_order_total` en `sample-app/src/orders/pricing.py`, abre un Pull Request y despliega `orders-qa` en el clúster de QA.

El resultado visible debe incluir:

1. Diff de la función refactorizada (O(n) en lugar de O(n²)).
2. Confirmación de que el AST / `compile()` del archivo es válido.
3. URL del Pull Request (o payload `dry-run`).
4. Estado de sincronización de Argo CD (`Synced` / `Healthy` o simulado).
5. Lista de Pods en `orders-qa` con fase y `Ready`.

## 2. Agentes y herramientas

Cada agente tiene una instrucción de sistema corta y un conjunto **cerrado** de tools. Granite elige argumentos; el runtime ejecuta.

### Code Agent

- **Instrucción:** analista de código Python. No inventa APIs. Conserva la firma pública y los tests.
- **Tools:** `analyze_python_source`, `extract_function`, `validate_python_source`.
- **Modelo:** Granite vía MaaS para proponer el cuerpo nuevo tras ver el informe AST.

El AST se obtiene **antes** de llamar al LLM. El modelo recibe un resumen (complejidad ciclomática aproximada, bucles anidados, nombre de función) y el fuente. Tras la respuesta, `validate_python_source` ejecuta `ast.parse` + `compile`. Si falla, un segundo turno de corrección (máximo 2 reintentos).

### GitHub Agent

- **Instrucción:** solo opera sobre `ALLOWED_REPOS`. Crea rama `agent/granite-<timestamp>`, commit y PR.
- **Tools:** `github_get_file`, `github_create_branch`, `github_commit_files`, `github_create_pr`.
- **Guardas:** org/repo allowlisted; default branch configurable (`main`); no force-push; no merge.

### Deploy Agent (Argo CD + OpenShift destino)

- **Instrucción:** sincroniza **una** Application allowlisted y lee estado; no borra recursos ni cambia proyectos Argo.
- **Tools:** `argocd_get_app`, `argocd_sync_app`, `ocp_list_pods`, `ocp_deployment_status`.
- **Guardas:** `ALLOWED_ARGOCD_APPS`, `ALLOWED_NAMESPACES`; kubeconfig montado en el Pod MCP, no expuesto al modelo.

## 3. Orquestación (supervisor)

El orquestador no deja que un único agente “haga de todo”. Secuencia fija:

```text
1. Resolver contexto
   repo, path, función, app Argo, namespace QA
   (valores por defecto de ConfigMap demo-pipeline)

2. Code Agent
   GET archivo → AST → Granite refactor → validate

3. GitHub Agent
   branch → commit → PR   (omitido si DRY_RUN)

4. Deploy Agent
   sync Application → esperar Healthy (timeout) → listar Pods

5. Resumen
   markdown para LibreChat: diff, enlaces, tabla de Pods
```

Si un paso falla, el pipeline se detiene y devuelve el error al usuario **sin** ejecutar los pasos siguientes (no se hace sync de Argo si el PR no se creó, salvo `SKIP_GIT=true` en labs).

## 4. Contratos de tools (REST)

Todas las tools exponen `GET /health` y `POST /invoke`:

```json
{
  "tool": "analyze_python_source",
  "arguments": {
    "source": "def calculate_order_total(...): ...",
    "function_name": "calculate_order_total"
  }
}
```

Respuesta:

```json
{
  "ok": true,
  "dry_run": false,
  "result": { }
}
```

El mismo proceso sirve MCP Streamable HTTP en `/mcp` para Llama Stack (`remote::model-context-protocol`).

## 5. Prompts de sistema (resumen)

Los textos completos están en [`llamastack/agents.yaml`](../llamastack/agents.yaml) y [`orchestrator/agents.py`](../orchestrator/agents.py).

**Code:** *Eres un ingeniero Python. Refactorizas para claridad y complejidad lineal. No cambias la firma. No añades dependencias. Devuelves solo el archivo completo.*

**GitHub:** *Operas el API de GitHub. Nunca pides tokens. Si el repo no está en allowlist, rechazas.*

**Deploy:** *Eres un operador GitOps. Sync es explícito. Nunca haces prune. Reportas Healthy/Degraded con evidencia de Pods.*

## 6. Sample app (el “problema” que se ve en escena)

`sample-app` es un servicio mínimo de pedidos. `calculate_order_total` cuenta duplicados de SKU con un bucle anidado (O(n²)) para aplicar un 5 % de descuento. Es deliberadamente obvio en una captura de AST y lo suficientemente pequeño para Granite 8B (y 2B en lab).

GitOps de la app: `sample-app/gitops/` → Application Argo CD `orders-qa` en el clúster de destino. El agente Deploy sincroniza **esa** Application, no la de RHOAI.

## 7. Trazas para la demo

El orquestador emite logs JSON por paso (`agent`, `tool`, `duration_ms`, `dry_run`). En la UI, el mensaje final incluye una sección **Pasos** para narrar el flujo sin abrir `oc logs`.
