# 06 — Operadores, Helm y CRDs

La demo necesita runtime **además** de MaaS: operador Llama Stack, PostgreSQL para metadatos, MongoDB para LibreChat, y el chart de LibreChat. Todo eso vive en [`platform/`](../platform/README.md).

## 1. Llama Stack Operator (RHOAI 3.4)

No se instala un CSV suelto si OpenShift AI ya está en el clúster. El procedimiento soportado es activar el componente en el `DataScienceCluster`:

```yaml
spec:
  components:
    llamastackoperator:
      managementState: Managed
```

El Job `enable-llamastack-operator` hace un **merge patch** de esa única clave sobre `default-dsc`. No reescribe el resto del DSC.

Verificación:

```bash
oc get datasciencecluster default-dsc \
  -o jsonpath='{.spec.components.llamastackoperator.managementState}'
oc -n redhat-ods-applications get pods -l name=llama-stack-k8s-operator
oc get crd llamastackdistributions.llamastack.io
```

Fallback (solo labs **sin** RHOAI gestionando el operador): `platform/operators/llamastack/subscription-community.yaml`. No está en el `kustomization` por defecto para no duplicar el operador.

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

El Job del DSC necesita `patch` sobre `datascienceclusters` (ClusterRole). Las Subscriptions las aplica un usuario `cluster-admin` o Argo CD con el mismo privilegio que ya usa el GitOps de RHOAI.

No se instala Service Mesh 3. MongoDB Community y CNPG declaran SCC/anyuid en sus CSV; no añadir SCC extra salvo que el cluster lo exija.
