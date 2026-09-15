#!/usr/bin/env bash
set -euo pipefail

namespace="oke-lab"
deployment="hello-oke"

echo "Nodes:"
kubectl get nodes
echo
echo "Application:"
kubectl -n "$namespace" rollout status "deployment/$deployment" --timeout=180s
kubectl -n "$namespace" get pods -l app.kubernetes.io/name="$deployment"
echo
echo "Recent events:"
kubectl -n "$namespace" get events --sort-by=.lastTimestamp | tail -n 12
echo
echo "Service endpoint:"
endpoint=$(kubectl -n "$namespace" get service "$deployment" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [[ -z "$endpoint" ]]; then
  echo "Load Balancer endpoint is not assigned yet." >&2
  exit 1
fi
curl --fail --silent --show-error "http://$endpoint/"
echo
