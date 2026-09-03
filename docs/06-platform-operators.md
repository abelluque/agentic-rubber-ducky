# 06 — Operadores, Helm y CRDs

La demo necesita runtime **además** de MaaS: operador Llama Stack, PostgreSQL para metadatos, MongoDB para LibreChat, y el chart de LibreChat. Todo eso vive en [`platform/`](../platform/README.md).

## 1. Llama Stack Operator (spoke, sin MaaS)

Por defecto el spoke **no** tiene OpenShift AI. `platform/operators` instala `llama-stack-k8s-operator` desde `community-operators` en `llama-stack-system`. La `LlamaStackDistribution` usa `distribution.name: remote-vllm` y `VLLM_URL` apuntando al gateway del **hub**.

Si el spoke ya tiene RHOAI y se quiere el operador in-tree:

```bash
oc apply -k platform/operators-with-rhoai
```

Eso parchea `llamastackoperator.managementState: Managed` y **quita** la Subscription community. No aplicar ambos.

Verificación (spoke):

```bash
oc get crd llamastackdistributions.llamastack.io
oc -n llama-stack-system get csv,pods
```

CRD vendorizada: `platform/crds/llamastack.io_llamastackdistributions.yaml` (snapshot de [opendatahub-io/llama-stack-k8s-operator](https://github.com/opendatahub-io/llama-stack-k8s-operator)). En un cluster vivo el operador reconcilia la CRD; aplicar el snapshot a mano solo tiene sentido en air-gap o para que Argo conozca el esquema antes del CSV.

RHOAI 3.5 renombra Llama Stack a **OGX** (`OGXServer`, `ogx.io`). Esta demo está anclada a **3.4** (`LlamaStackDistribution`).

## 2. CloudNativePG

OLM:

- Catalog: `community-operators` (o `certified-operators` / EDB si el cluster lo tiene)
- Package: `cloudnative-pg`
- Channel: `stable-v1` (ajustar si OperatorHub muestra `stable`)
- Namespace: `cnpg-system` (AllNamespaces vía OperatorGroup)

CR: `postgresql.cnpg.io/v1 Cluster` llamado `llamastack-pg` en `demo-granite`. Servicio de escritura: `llamastack-pg-rw:5432`. Secret de aplicación: `llamastack-pg-app` (claves `username`, `password`, `dbname`).

## 3. MongoDB Community Operator

OLM:

- Catalog: `community-operators`
- Package: `mongodb-community-operator`
- Channel: `stable`
- Namespace: `mongodb-operator` (watch all namespaces)

CR: `mongodbcommunity.mongodb.com/v1 MongoDBCommunity` `librechat-mongo` (1 miembro, suficiente para demo). LibreChat usa el Secret de conexión que genera el operador.

## 4. Helm

| Chart | Propósito |
| --- | --- |
| `demo-operators` | Equivalente Helm de las Subscriptions OLM (alternativa a `oc apply -k platform/operators`) |
| `llamastack-postgres` | `Cluster` CNPG |
| `librechat-mongodb` | `MongoDBCommunity` |
| `librechat` | Deployment + Service + Route + ConfigMap (endpoint orquestador Granite) |
| `granite-agent-stack` | Umbrella de los tres últimos |

`helm dependency update platform/charts/granite-agent-stack` no es necesario: las dependencias son `file://`.

## 5. Orden y RBAC

Las Subscriptions las aplica un `cluster-admin` del **spoke** (o Argo CD en ese clúster). El overlay `with-rhoai` es el único que necesita `patch` sobre `datascienceclusters`.

No se instala Service Mesh 3. No se instala el plano MaaS en el spoke.
