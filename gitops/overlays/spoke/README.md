# Overlay for the *spoke* OpenShift cluster (LibreChat, Llama Stack, agents).
#
# Replace CHANGE_ME.example.com with the *hub* apps domain from rhoai-gitops
# (the cluster that publishes maas.<domain>), not this cluster's domain.
#
#   kustomize build gitops/overlays/spoke
#   oc apply -k gitops/overlays/spoke   # kubeconfig = spoke
