# 04 — Guion de demostración (E2E)

Duración objetivo: **12–15 minutos**. Audiencia: arquitectos de plataforma, AI, y GitOps.

## Antes de abrir LibreChat (3 min)

En una terminal, ya autenticado en el **clúster hub**:

```bash
oc get llminferenceservice -n ai-models
./scripts/probe-maas.sh
oc -n demo-granite get pods
```

Mostrar:

1. `granite-3-0-8b-instruct` (o 2B en lab) `Ready`.
2. Probe MaaS con HTTP 200.
3. Pods `librechat`, `orchestrator`, `llamastack`, `mcp-*` Running.

Comentar en una frase: *el modelo no es un contenedor de la demo; es un servicio de plataforma con API key y cuota.*

Si `DRY_RUN=true` (default), anunciarlo: *las mutaciones están simuladas; el razonamiento es real contra Granite.*

## Prompt único (el momento de la demo)

En LibreChat, modelo **DevOps Agent (IBM Granite MaaS)**:

```text
Optimiza la función calculate_order_total en sample-app/src/orders/pricing.py:
elimina el bucle anidado O(n²), conserva la firma y el descuento por SKU duplicado.
Abre un Pull Request en GitHub y sincroniza la aplicación Argo CD orders-qa.
Confirma que los Pods del namespace orders-qa en el clúster de QA estén Ready.
```

No añadir más contexto. El ConfigMap `demo-pipeline` ya tiene repo, rama y app.

## Qué narrar mientras Granite trabaja

| Paso | Qué decir | Qué aparece en la respuesta |
| --- | --- | --- |
| 1 | LibreChat no llama a GitHub: llama al orquestador. | (espera / streaming) |
| 2 | El Code Agent pide el AST, no “adivina” el archivo. | Informe de nested loops |
| 3 | Granite reescribe; el runtime valida `compile()`. | Diff |
| 4 | GitHub Agent crea rama `agent/granite-…` y PR. | URL del PR o JSON dry-run |
| 5 | Argo CD sync **solo** `orders-qa`. | Synced/Healthy |
| 6 | `oc` contra el kubeconfig de QA, no del hub. | Tabla de Pods |

## Respuesta esperada (estructura)

```markdown
## Refactor
- Complejidad: bucles anidados → indexación por SKU (O(n))
- Validación AST: OK

## GitHub
- PR: https://github.com/<org>/<repo>/pull/<n>

## GitOps
- Application orders-qa: Synced / Healthy

## OpenShift QA
| Pod | Ready | Restarts |
| --- | --- | --- |
| orders-qa-… | 1/1 | 0 |
```

Si `DRY_RUN=true`, cada sección lleva la etiqueta `dry-run` y no hay URL real de PR.

## Preguntas frecuentes en sala

**¿Por qué Granite y no un modelo de código premium?**  
El overlay de producción reserva Qwen/DeepSeek al tier premium. La demo demuestra que el **tier free gobernado** basta para un hotspot acotado, y que MaaS aplica la misma puerta (key, cuota) a todos los consumidores.

**¿El agente puede desplegar RHOAI?**  
No. Allowlists: un repo, una Application Argo, un namespace. El App-of-Apps de plataforma está fuera de alcance.

**¿Dónde está el LLM?**  
`LLMInferenceService` en `ai-models`, detrás de `maas.<domain>`. Llama Stack y LibreChat son clientes.

**¿Qué pasa si Granite genera Python inválido?**  
Hasta dos reintentos con el error de `compile()` inyectado en el siguiente prompt. Si sigue fallando, no hay PR ni sync.

## Cierre (1 min)

Mostrar el PR en el navegador (o el payload dry-run) y `oc get pods -n orders-qa` en el contexto del clúster QA. Volver a LibreChat y subrayar: *un turno de chat, tres sistemas, un modelo de plataforma.*

## Plan B (lab sin GitHub/Argo)

Dejar `DRY_RUN=true` y ejecutar:

```bash
./scripts/smoke-test.sh
```

El smoke test llama al orquestador en-cluster (port-forward) con el mismo prompt y comprueba que el resumen contiene `calculate_order_total` y `dry_run`.
