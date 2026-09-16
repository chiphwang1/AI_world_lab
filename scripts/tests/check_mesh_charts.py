"""Render-only contract checks. No kubeconfig, cluster calls, or live credentials."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ONLY = "--local-only" in sys.argv
if LOCAL_ONLY:
    sys.argv.remove("--local-only")


def render(release, chart, namespace="oke-lab", extra=()):
    result = subprocess.run(
        ["helm", "template", release, chart, "--namespace", namespace,
         "--kube-version", "1.36.1", *extra],
        cwd=ROOT, text=True, capture_output=True, check=True, timeout=120,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def resource(docs, kind, name):
    return next(doc for doc in docs if doc["kind"] == kind
                and doc["metadata"]["name"] == name)


class AppCharts(unittest.TestCase):
    def test_default_app_and_service_match(self):
        docs = render("hello-oke", "./charts/oke-mesh-app")
        self.assertEqual(len(docs), 2)
        app = resource(docs, "Deployment", "hello-oke")["spec"]
        service = resource(docs, "Service", "hello-oke")["spec"]
        self.assertEqual(app["replicas"], 2)
        self.assertEqual(service["type"], "LoadBalancer")
        for key, value in service["selector"].items():
            self.assertEqual(app["template"]["metadata"]["labels"][key], value)
        self.assertEqual(service["ports"][0]["appProtocol"], "http")
        self.assertEqual(app["template"]["metadata"]["labels"]["version"], "v1")

    def test_traffic_is_opt_in_and_targets_release(self):
        docs = render("example", "./charts/oke-mesh-app", extra=("--set", "traffic.enabled=true"))
        self.assertEqual(len(docs), 3)
        traffic = resource(docs, "Deployment", "example-traffic")
        container = traffic["spec"]["template"]["spec"]["containers"][0]
        self.assertIn("http://example:80/", container["args"][0])
        self.assertIn("sleep 2", container["args"][0])
        self.assertTrue(container["securityContext"]["runAsNonRoot"])


@unittest.skipIf(LOCAL_ONLY, "Upstream chart rendering explicitly skipped (--local-only)")
class UpstreamCharts(unittest.TestCase):
    def test_istio_base_and_control_plane(self):
        repo = "https://istio-release.storage.googleapis.com/charts"
        version = os.environ["ISTIO_VERSION"]
        base = render("istio-base", "base", "istio-system",
                      ("--repo", repo, "--version", version, "--include-crds",
                       "--set", "defaultRevision=default"))
        self.assertTrue(any(d["kind"] == "CustomResourceDefinition" for d in base))
        docs = render("istiod", "istiod", "istio-system",
                      ("--repo", repo, "--version", version, "-f", "helm/values/istiod.yaml"))
        deploy = resource(docs, "Deployment", "istiod")
        self.assertEqual(deploy["spec"]["replicas"], 1)
        self.assertEqual(deploy["spec"]["template"]["spec"]["containers"][0]
                         ["resources"]["requests"]["memory"], "256Mi")
        self.assertFalse(any(d["kind"] == "HorizontalPodAutoscaler" for d in docs))
        mesh = yaml.safe_load(resource(docs, "ConfigMap", "istio")["data"]["mesh"])
        self.assertTrue(mesh["defaultConfig"]["holdApplicationUntilProxyStarts"])

    def test_prometheus_is_ephemeral_and_scrapes_mesh(self):
        docs = render("prometheus", "prometheus", "istio-system", (
            "--repo", "https://prometheus-community.github.io/helm-charts",
            "--version", os.environ["PROMETHEUS_CHART_VERSION"],
            "-f", "helm/values/prometheus.yaml"))
        self.assertFalse(any(d["kind"] in ("PersistentVolumeClaim", "Ingress", "DaemonSet") for d in docs))
        service = resource(docs, "Service", "prometheus-server")
        self.assertEqual(service["spec"]["type"], "ClusterIP")
        self.assertEqual(service["spec"]["ports"][0]["port"], 80)
        config = yaml.safe_load(resource(docs, "ConfigMap", "prometheus-server")["data"]["prometheus.yml"])
        jobs = {job["job_name"]: job for job in config["scrape_configs"]}
        self.assertEqual(set(jobs), {"istiod", "istio-workloads"})
        self.assertEqual(jobs["istio-workloads"]["relabel_configs"][0]["regex"], "http-envoy-prom")
        self.assertEqual(jobs["istio-workloads"]["kubernetes_sd_configs"][0]["namespaces"]["names"], ["oke-lab"])

    def test_kiali_is_internal_readonly_and_wired_to_prometheus(self):
        docs = render("kiali-server", "kiali-server", "istio-system", (
            "--repo", "https://kiali.org/helm-charts",
            "--version", os.environ["KIALI_CHART_VERSION"],
            "-f", "helm/values/kiali.yaml"))
        self.assertFalse(any(d["kind"] == "Ingress" for d in docs))
        self.assertEqual(resource(docs, "Service", "kiali")["spec"]["type"], "ClusterIP")
        config = yaml.safe_load(resource(docs, "ConfigMap", "kiali")["data"]["config.yaml"])
        self.assertEqual(config["auth"]["strategy"], "anonymous")
        self.assertTrue(config["deployment"]["view_only_mode"])
        self.assertEqual(config["external_services"]["prometheus"]["url"],
                         "http://prometheus-server.istio-system.svc.cluster.local:80")
        self.assertEqual(config["server"]["web_root"], "/kiali")
        for doc in docs:
            if doc["kind"] in ("ClusterRole", "Role"):
                for rule in doc.get("rules", []):
                    # Upstream viewer role uses API subresources for inspection/auth.
                    if rule.get("resources") in (["pods/portforward"], ["tokenreviews"]):
                        self.assertEqual(rule["verbs"], ["create"])
                        continue
                    self.assertFalse({"create", "update", "patch", "delete", "*"} & set(rule["verbs"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
