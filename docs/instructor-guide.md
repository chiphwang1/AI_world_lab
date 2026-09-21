# Instructor delivery and release guide

This file contains instructor notes, preparation, debrief answers, and release checks. The student walkthrough is [README.md](../README.md).

Plan for **90 minutes: 30 minutes of lecture and cluster provisioning, followed by 60 minutes of hands-on work and debrief**. Cluster creation starts at workshop minute 0, not before the session. Desktop and repository preparation can happen beforehand. Students follow [README.md](../README.md); use the same [architecture diagram](architecture.md) in the lecture.

## Delivery schedule

“Workshop minute” counts from the start of the lecture. “Lab minute” starts at workshop minute 30. These are facilitation targets, not deadlines for assessing students. Checkpoints assess observed results; intervene early when downloads or cloud readiness threaten the session budget.

| Workshop minute | Activity or readiness gate |
|---|---|
| 0–5 | Start each assigned cluster's provisioning. Introduce the app and learning goals. |
| 5–15 | Trace requests, dashboard telemetry, and HPA CPU metrics on the shared diagram. |
| 15–20 | Explain Helm releases, Services, and readiness versus liveness. |
| 20 | A helper checks provisioning status and identifies sessions needing intervention. Continue the lecture. |
| 20–30 | Explain CPU requests/limits and HPA; demonstrate repository root, kubeconfig, and the three-terminal layout. Resolve access problems. |
| 30 | Begin the learner clock only if assigned access, two Ready workers, and resource metrics are available. |
| 53 / lab 23 | Mesh and monitoring installed. Intervene on blocked installations. |
| 63 / lab 33 | Public app and baseline traffic working. Intervene before dashboard exploration. |
| 77 / lab 47 | Start the five-minute burst by this point to leave time for scale-in. |
| 85 / lab 55 | Core work ends; record any blocked checkpoint honestly. |
| 85–90 | Debrief using the completion sheet; absorb small delays. |

Only offer pod recovery if core work finishes by lab minute 50. Direct Prometheus queries, outages, and OCI alarms are extensions outside this session.

## Before class and the minute-20 check

Before class, test the actual learner Bash terminal, private-repository access, OCI authentication, and chart downloads. Provide a tested repository commit/tag, the assigned context name, and a prepared kubeconfig path, preferably `~/.kube/oke-lab`. Never infer the intended target from whatever context happens to be current. Arrange the cluster-level Helm installation permissions; students do not need to run RBAC capability checks. See [cluster access](cluster-access.md).

At workshop minute 20:

1. Inspect each session's provisioning job. A visible Luna desktop is not proof that OKE is ready. Record pending/failed sessions and assign a helper.
2. For clusters with a reachable API, run the following from the prepared checkout with that learner's kubeconfig and OCI environment. Replace the placeholder with the independently assigned context:

   ```bash
   bash scripts/check-ready.sh --context '<instructor-assigned-context>'
   ```

3. Check the managed Cert Manager and Metrics Server add-ons are healthy and that permissions and image access have been validated. The script checks repository files, tool presence, selected context, API authentication, version compatibility, two Ready/non-cordoned workers, and numeric node metrics. It does **not** prove chart downloads, Helm install permissions, all scheduling constraints, or future LoadBalancer availability.
4. Resolve missing authentication, old binaries, add-on readiness, or failed provisioning before minute 30. Re-run preflight in a fresh learner terminal. Do not silently switch a learner to another person's or a production cluster.

Prepare chart downloads before the hands-on clock. Newly created workers do not inherit the rehearsal cluster's cached images; if pre-pulling is part of classroom preparation, measure it within the provisioning window once workers exist. Keep the student Helm installations visible. Do not count an already-deployed release's upgrade time as first-install time.

If a cluster cannot be ready at minute 30, use an already authorized, dedicated spare if one is available. Otherwise use an instructor demonstration and record that learner as **demonstration only**, not completed. Starting their full lab late cannot preserve the 90-minute limit. Provisioning inside 30 minutes remains a release requirement to validate, not a promise established by local rehearsal.

Keep two workers for this tested per-learner workload. Validate allocatable capacity for up to six app pods and their proxies, the generator, observability stack, and system pods. A third worker adds scheduling capacity but does not fix kubeconfig mistakes, slow learner navigation, or a container's memory limit. See the measured [two-versus-three-worker assessment](rehearsal-2026-09-21-improvements.md#two-workers-versus-three).

## Debrief answer guide

Use the [completion sheet](completion-sheet.md) to assess both observations and explanations. Do not require a peak of six replicas or invent readings for missing panels.

| Prompt | What a successful explanation includes |
|---|---|
| Stable endpoint | The Service survives pod replacement; its OCI LoadBalancer address remains unchanged during pod scaling. |
| Two metrics paths | Metrics Server supplies this HPA's resource metrics. Prometheus supplies Kiali and Grafana with mesh telemetry. |
| Scaling | Manual scaling and HPA change app replicas; neither changes worker count in this lab. HPA owns the count once enabled. |
| Scale-in evidence | HPA returns to two and two app pods are Ready after CPU falls. Scrape discovery can make Grafana's proxy count lag; it is not a readiness measurement. |
| Probes and Degraded | Readiness excludes an unready pod from normal Service traffic; liveness can restart a failing container. Kiali's label alone does not identify a probe failure: inspect the affected object, pod state, events, and request errors. |
| CPU prediction | 60% of a `200m` request is `120m`. Utilization is relative to the request, not the CPU limit; the HPA here measures `web`, not the sidecar. |
| Optional recovery | The Deployment's ReplicaSet replaces a deleted pod at the same desired count. This is self-healing, not an HPA scale-out. |

Completion requires the customized public response, mesh traffic, baseline/load/scale-in observations, replica growth above two and return to two, and explicit `traffic.loadEnabled=false`. A missing metric or blocked checkpoint needs instructor follow-up, not a checked box. A partner discussion can assess the explanations without another quiz.

## Classroom pilot and release gates

**Not yet completed:** a real beginner's full 90-minute Luna run, session-end cleanup with the full workload, expected classroom concurrency, a full-hour dashboard refresh test after the Grafana memory fix, and required security scans. Local tests and this checklist do not substitute for those results. The CI scanner-image allowlist blocker also needs resolution before release.

Run the pilot in a separately authorized, disposable Luna session. Do not reset an existing rehearsal cluster or destroy locally tracked infrastructure merely to satisfy this checklist.

- [ ] Record the repository revision, desktop tools, node shape/count, permissions, and exact provisioning start/Ready/metrics-ready times. Verify provisioning overlaps the lecture and finishes by minute 30.
- [ ] Have a learner unfamiliar with the lab follow the README without hidden instructor commands. Record prompts for help, navigation errors, and each checkpoint time.
- [ ] Inventory already-installed add-ons/releases and cached charts/images. Measure clean student installs; label any warm reuse. Do not compare a cached upgrade directly with a fresh install.
- [ ] Record command execution/waits separately from reading, editing, typing, and interpreting results. Actual learner delays are measured human time; simulated allowances must be labeled as estimates. Account for overlap once, not twice.
- [ ] Verify both dashboard UIs, manual 2→4→2 scaling, numeric HPA metrics, the bounded burst, scale-out, explicit load reset, and scale-in. Finish core work by lab minute 55 and the debrief by workshop minute 90.
- [ ] Run a separate 60-minute dashboard soak before release, since dashboards open partway through the classroom lab. Refresh the lab dashboard every 15 seconds; sample Grafana pod UID, restart count, memory, and events before, during, and after. Require no OOM kills or unexplained restarts and investigate failed queries or broken forwards. Grafana currently requests 512Mi and is limited to 1Gi, with `GOMEMLIMIT=512MiB`.
- [ ] In the authorized pilot, leave releases installed and let Luna's session-end cleanup run. Monitor it through completion and verify the app's OCI LoadBalancer is removed before infrastructure destruction. Confirm no billable leftovers; students must not run a manual uninstall. Follow [cleanup responsibilities](cleanup.md).
- [ ] Test the expected number of simultaneous learner sessions for OCI quotas, launch time, image/chart access, scheduling, and cleanup. One healthy cluster does not validate classroom capacity.
- [ ] Run static/chart/unit checks from [AGENTS.md](../AGENTS.md) and [Helm validation](../helm/README.md#validation-and-release), plus the required security scans. Record skipped/blocked checks explicitly; functional tests are not a security result.

Pilot timing record:

| Phase | Start/end on workshop clock | Measured command/wait time | Measured human time | Overlap | Simulated allowance, if any | Result/blocker |
|---|---|---|---|---|---|---|
| Provisioning + lecture | ___ | ___ | ___ | ___ | ___ | ___ |
| Connect | ___ | ___ | ___ | ___ | ___ | ___ |
| Install components | ___ | ___ | ___ | ___ | ___ | ___ |
| Build/run | ___ | ___ | ___ | ___ | ___ | ___ |
| Observe | ___ | ___ | ___ | ___ | ___ | ___ |
| Scale-out/in | ___ | ___ | ___ | ___ | ___ | ___ |
| Debrief | ___ | ___ | ___ | ___ | ___ | ___ |

The earlier model was approximately 50–51 minutes with prepared caches and simulated human allowances, or 56–61 with simulated cold-download allowances before troubleshooting. These are not measurements of this revised learner document. Retest rather than claiming that a shorter README proves a faster class.

## Maintenance and distribution

The [September 18 rehearsal](rehearsal-2026-09-18.md), [September 21 reset/reinstall](rehearsal-2026-09-21.md), and [follow-up retest](rehearsal-2026-09-21-improvements.md) preserve measured execution times and the Grafana failure/fix. Keep historical measurements distinct from later estimates.

The preflight compatibility check follows the pinned Istio 1.31.x range, Kubernetes 1.32–1.36, and kubectl's one-minor-version skew rule. Review the script and its tests whenever changing these pins. Sources: [Istio supported releases](https://istio.io/latest/docs/releases/supported-releases/) and [kubectl version skew policy](https://kubernetes.io/releases/version-skew-policy/#kubectl).

The GitHub repository is private and has no established workshop release tag yet. Arrange access or a prepared checkout and record a tested commit/tag before distribution. Follow [packaging notes](../helm/README.md#github-distribution); exclude credentials, local configuration, Terraform state/plans, and operational logs. Keep the diagram in one file so the lecture and README cannot drift apart.

Suggested Luna description: **Build, run, and scale an application on OKE. Cluster creation runs during the opening lecture. Then customize a Helm deployment, expose it through an OCI LoadBalancer, and use Istio, Prometheus, Kiali, and Grafana to observe traffic and scaling. Test manual scaling and CPU-based autoscaling, with optional pod recovery.**

`terraform/` and CI scripts are instructor-managed; `charts/` and `helm/` contain learner deployment materials. Do not mix the legacy `kubernetes/` manifests into the Helm student workflow. See [CI administration](gitlab-ci.md), [local Terraform workflow](maintainer-infrastructure.md), and [cleanup](cleanup.md).
