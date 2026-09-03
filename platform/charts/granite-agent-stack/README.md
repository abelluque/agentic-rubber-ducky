1. Apply `platform/operators` (OLM + DataScienceCluster patch).
2. Wait for CRDs: `llamastackdistributions.llamastack.io`, `clusters.postgresql.cnpg.io`, `mongodbcommunity.mongodbcommunity.mongodb.com`.
3. Install this chart (or the individual charts) in `demo-granite`.
4. Apply `gitops/overlays/demo-with-operators`.

Run `helm dependency update` in this directory before Argo CD can render file:// subcharts.
