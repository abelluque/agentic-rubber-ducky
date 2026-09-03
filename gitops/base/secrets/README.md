Do not commit filled copies of this file.

1. `cp gitops/base/secrets/demo-secrets.yaml.example /tmp/demo-secrets.yaml`
2. Replace every `CHANGE_ME`.
3. `oc apply -f /tmp/demo-secrets.yaml`

Keys:

- `demo-maas.api-key` — output of `./scripts/create-maas-key.sh`
- `demo-github.token` — PAT limited to the allowlisted repo
- `demo-argocd` — Argo CD of the *QA* cluster
- `demo-target-kubeconfig` — kubeconfig of the ServiceAccount in `gitops/reference/target-cluster-reader.yaml`
- `demo-postgres.password` — Llama Stack database
- `demo-librechat` — `openssl rand -hex 32` for `CREDS_KEY` and `JWT_SECRET`

When using `platform/` operators, also apply `demo-secrets-operators.yaml.example` (`librechat-mongo-user` plus a `mongo-uri` that points at `librechat-mongo-svc`). CloudNativePG creates `llamastack-pg-app`; do not put that password in Git.
