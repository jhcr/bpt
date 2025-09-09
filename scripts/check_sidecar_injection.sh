#!/bin/bash
# Check Istio sidecar injection status for all pods

set -e

NAMESPACE=${1:-app-prod}

echo "🔍 Checking sidecar injection in namespace: $NAMESPACE"
echo "=================================================="

# Check if namespace has istio-injection enabled
INJECTION_ENABLED=$(kubectl get namespace $NAMESPACE -o jsonpath='{.metadata.labels.istio-injection}' 2>/dev/null || echo "not-found")
echo "Namespace injection label: $INJECTION_ENABLED"
echo ""

# List all pods and their sidecar status
kubectl get pods -n $NAMESPACE -o custom-columns=\
"NAME:.metadata.name,\
READY:.status.containerStatuses[*].ready,\
CONTAINERS:.spec.containers[*].name,\
SIDECARS:.spec.containers[?(@.name=='istio-proxy')].name" \
--no-headers | while read line; do
    POD_NAME=$(echo $line | awk '{print $1}')
    READY=$(echo $line | awk '{print $2}')
    CONTAINERS=$(echo $line | awk '{print $3}')
    SIDECAR=$(echo $line | awk '{print $4}')
    
    if [[ "$SIDECAR" == "istio-proxy" ]]; then
        echo "✅ $POD_NAME - Sidecar injected"
    else
        echo "❌ $POD_NAME - No sidecar"
    fi
done

echo ""
echo "🔧 To enable sidecar injection:"
echo "kubectl label namespace $NAMESPACE istio-injection=enabled"