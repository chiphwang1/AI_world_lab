# Lab improvements and two-worker retest — 2026-09-21

## Result

The revised configuration passed public HTTP, both dashboards, manual **2 → 4 → 2** scaling, and HPA **2 → 6 → 2** on the existing two workers. Grafana's previous repeated restart behavior did not recur during this retest; the bounded observation interval is recorded below. The documentation and regression-test fixes are implemented locally.

Keep two workers for this per-learner workload. Plan **50–51 minutes with instructor-prepared access and caches**; the modeled cold path can exceed an hour. Full-session Grafana stability, actual first-time learner timing, Luna provisioning/cleanup, and security checks remain release gates.

## Scope

Follow-up to the [reset-and-reinstall rehearsal](rehearsal-2026-09-21.md). That report preserves the original Grafana failure; this report records the approved fixes and subsequent tests. The target remains `oke-bootcamp-rehearsal-20260918` in Phoenix, Kubernetes 1.36.1, with two existing workers. This run upgrades existing releases. It does not measure a new cluster, cold images, first-time CRD creation, or a new load balancer.

The project environment selected the verified rehearsal context. Bash used kubectl 1.36.0 and Helm 4.0.5 from the installed Rancher Desktop tool directory; no permanent PATH changes or tool installations were made. All six lab releases were inspected before changes. Managed Cert Manager and Metrics Server were retained.

## Changes implemented

- Grafana: memory request 256Mi → 512Mi, limit 512Mi → 1Gi, and explicit `GOMEMLIMIT=512MiB`. CPU settings, chart version, anonymous Viewer access, ClusterIP networking, and ephemeral storage are unchanged.
- README: check both normal containers and native sidecars, explain the completed `istio-init` versus running `istio-proxy`, skip generic Grafana admin-login NOTES, and identify traffic logs by pod/timestamp during rollouts. See the [Kubernetes native-sidecar model](https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/).
- Appendix: repeated Grafana failures now lead to memory/restart evidence; repeat-run manual scaling first disables the previous HPA. Normal first-run steps remain in the main flow.
- Instructor guidance: verify the actual Bash-resolved kubectl and [supported client/server skew](https://kubernetes.io/releases/version-skew-policy/), prepare cluster access before class, and keep OCI cluster discovery outside the hour. Automatic OCI token generation remains required.
- Tests: a customized `student.yaml` message no longer fails the chart contract. A separate override test checks message wiring without rewriting the student's file. Upstream rendering checks Grafana's memory request/limit and exactly one explicit Go memory target.
- Monitoring/troubleshooting references distinguish readiness warnings, confirmed OOM kills, dashboard connectivity, and the limits of point-in-time memory measurements.

The writing skill kept exceptional troubleshooting out of the student sequence. The OKE troubleshooting skill guided the evidence-first investigation; its referenced discovery/correlation helper scripts were absent, so scoped direct Kubernetes/OCI reads were used. No node debug pods were needed.

## Grafana diagnosis and fix

| Hypothesis | Confidence | Evidence |
|---|---|---|
| The old 512Mi cap was insufficient for the observed dashboard workload | High | Previous rehearsal recorded `OOMKilled`; the revised container exceeds 512Mi while serving the same dashboard |
| Worker memory shortage caused the confirmed failure | Low | Both nodes reported no MemoryPressure, with substantial allocatable memory unused and no scheduling failures |
| Every earlier disconnect was an OOM, or Grafana has a memory leak | Unproven | Several older exits had only reason `Error`; no heap/profile investigation establishes a leak |

The new Grafana pod became Ready at approximately **17:53:51 UTC**, following a **16.84-second** Helm upgrade. The browser opened on an isolated localhost port (`13001`) at approximately 17:58, with the provisioned 30-minute range and 15-second refresh. Existing user tabs on port 13000 were left untouched and were not connected through this new forward. This avoids intentionally reactivating their old refresh sessions; it is not proof that no other client accessed the in-cluster Service.

Sampled working-set memory rose from 484Mi to 622Mi, then was approximately 618–622Mi through the first load observations. At 18:04, Grafana's own metrics showed roughly 499Mi runtime-managed system memory before subtracting released heap pages, about 365Mi allocated heap, and 710Mi process RSS. These are different measures, not interchangeable container-limit readings. The runtime target leaves room for memory outside Go's accounting; it is not a hard process cap. See the [Go memory-limit guide](https://go.dev/doc/gc-guide#Memory_limit).

The previous chart automatically targeted 90% of the container limit for Go memory. The explicit environment value overrides that behavior, verified in rendered and live configuration. Both limit and runtime target changed together; this test cannot isolate which change contributed how much. No probes were disabled and no extra worker was added. The minimum safe limit has not been established.

A read-only attempt to inspect cgroup peak counters inside the Grafana container could not run because the image has no `sh` executable. No shell, debug container, or package was installed. Memory figures in this report remain sampled observations, not an established maximum over every instant.

Final stability interval and remaining release gates are recorded at the end of this report.

## Measured execution and checkpoints

Times below are command elapsed time, including their internal network/readiness waits. They exclude reading, typing, editing, interpretation, report writing, and browser-control latency. Reusing releases, cached images, and the existing public IP makes these unsuitable as fresh-install timing estimates.

| Operation | Measured elapsed |
|---|---:|
| Grafana resource/config upgrade | 16.84 s |
| Reapply Istio base | 4.96 s |
| Reapply istiod | 3.42 s |
| Reapply Prometheus | 2.71 s |
| Reapply Kiali | 43.06 s |
| Return existing app to two-replica manual mode | 2.72 s |
| Strict app lint | 0.18 s |
| Manual scale 2 → 4 | 16.88 s |
| Manual return 4 → 2 | 2.89 s |
| Enable HPA | 2.81 s |
| Enable bounded CPU burst | 8.96 s |
| Explicitly disable burst mode | 6.20 s |
| **Timed upgrade/lint subtotal** | **111.63 s** |
| Final HPA current-count check, after scale-in | 1.51 s |
| Final app rollout check | 1.48 s |

The manual test returned successful JSON from all four pod names across ten external curls. The customized message stayed `Hello from chip's OKE bootcamp`; the Service retained `132.226.120.202`. Step 3's revised JSONPath correctly showed `web` and `istio-init istio-proxy` in their respective lists.

HPA was created at **18:01:36**. At 18:01:59 its CPU was still unknown; by the **18:02:58** precheck it reported 1% and two replicas, with `ScalingActive=True`. This bounds metric availability; it does not measure the exact instant it became available. The load log began at **18:03:10.856560323**. Six replicas were desired by 18:03:53 and all six were Ready by the 18:04:29 sample. No app container restarts were observed.

`scripts/validate-lab.sh` passed during scale-out in **21.05 seconds**, including waiting for the new app replicas and checking external HTTP. This script checks the app, not dashboard reliability. A Kiali forward opened before Kiali's upgrade lost its old pod; reopening that rehearsal-owned forward restored HTTP access. This was an expected rollout interruption, not a new unexplained crash.

The traffic log recorded automatic completion at **18:08:10.013183472**, **299.157 seconds** after its start line (the generator's deadline uses integer epoch seconds). The explicit flag reset took 6.20 seconds and completed by 18:09:30. HPA's final `lastScaleTime` was **18:09:37**, approximately **87 seconds after burst completion**; the 18:10:00 sample showed two current replicas and a `2/2` Ready Deployment. The final explicit check at 18:11:02 confirmed two app pods, 1% CPU, baseline traffic enabled, and burst mode false. Post-scale-in live validation passed in **11.11 seconds**.

The core retest ran from the 17:58:30 upstream reapplication through the explicit scale-in verification at 18:11:02, **12 minutes 32 seconds of wall time**, plus the earlier Grafana upgrade; the final browser/history check followed. This includes tool/browser orchestration and report work during waits. It is neither a learner stopwatch measurement nor a pure execution subtotal. The command table, actual burst, reconciliation intervals, and human model remain separate; do not add overlapping intervals twice.

Browser checks confirmed anonymous Grafana rendering and a Kiali generator → app path. During load, Grafana showed six scraped proxies and 100% successful requests; Kiali workload details reported Healthy with six app pods. Numerical queries used the dashboard's existing Prometheus data-source proxy, separately from browser verification:

| Phase | Ready app pods | Requests/s | Success | p95 latency | Scraped app proxies |
|---|---:|---:|---:|---:|---:|
| Baseline, approximately 18:00–18:02 | 2 | 0.51 | 100% | 3.44 ms | 2 |
| Load, 18:06:28 | 6 | 9.49 | 100% | 399.54 ms | 6 |
| After scale-in, 18:11:34 | 2 | 0.53 | 100% (browser) | 0.975 ms | 2 |

The final Grafana screenshot showed the six-proxy plateau, subsequent return to two, baseline traffic, and the entire load burst in the 30-minute history without a Grafana restart or forward recovery.

Baseline and load hit different routes (`/` versus `/work`). Their latency difference is not a controlled comparison of autoscaling performance. Short startup readiness warnings cleared as new pods became Ready; they do not prove liveness-triggered restarts or retrospectively explain an earlier Kiali badge.

## Two workers versus three

OCI confirmed a two-node `VM.Standard.E5.Flex` pool, each with **1 OCPU / 16GB RAM / 50GB boot volume**. Each existing node exposes 1,830m CPU and approximately 13.13Gi memory as allocatable, with a 35-pod limit. Two nodes therefore provide 3,660m and approximately 26.27Gi before workload requests. A third identical node would nominally add another 1,830m / 13.13Gi; its own system DaemonSets would consume part of that addition.

Measured six-replica snapshot at approximately 18:04:33:

| Node | CPU requests / allocatable | CPU usage | Memory requests | Memory usage | Memory limits |
|---|---:|---:|---:|---:|---:|
| 10.0.148.15 | 820m / 1830m (44%) | 847m (46%) | 1148Mi | 2861Mi (21%) | 2970Mi |
| 10.0.154.61 | 1030m / 1830m (56%) | 967m (52%) | 2030Mi | 4222Mi (31%) | 6234Mi |

Total CPU requests at six replicas were **1850m of 3660m (~51%)**. Each app pod requests 100m for `web` and 50m for its proxy; growing from two to six adds 600m CPU and 512Mi memory requests. All six were placed, three per worker in this observation. No Pending pods or retained FailedScheduling events were found. Node conditions showed no memory, disk, or PID pressure.

CPU limits summed to 9960m and 8360m on the respective nodes, substantially above physical capacity. Limits are ceilings, not reservations or measured use; Istio's rendered proxy limit contributes to that overcommit. Do not promise simultaneous limit-level performance. These results validate this bounded single-learner workload, not an arbitrary number of learners sharing a cluster. See [Kubernetes requests and limits](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

| Question | Two workers, tested | Three identical workers, estimate only |
|---|---|---|
| Core app, dashboards, and six-pod HPA exercise | Fits observed requests and load | More headroom, but no demonstrated need |
| Grafana container OOM | Addressed at its container/runtime settings | Does not increase that container's limit |
| Fixed five-minute burst / learning objectives | Demonstrates pod scaling without node scaling | Does not shorten the timer or add a required concept |
| Node-loss or maintenance resilience | Not fault-tested; single-replica monitoring can be interrupted | More placement options, but no automatic HA guarantee or proactive rebalance |
| Other workloads / shared learners | Not validated | Could help if measurements show CPU, memory, IP or pod-slot pressure; still needs testing |

**Recommendation: keep two workers for the current per-learner lab.** Consider a third only for a measured capacity constraint or a separately designed node-failure/maintenance exercise. Do not add nodes to treat a container-limit OOM. No pool size, shape, placement, or Terraform variable was changed.

### Incremental cost, USD list prices

Retrieved September 21, 2026 from [Oracle's price list](https://www.oracle.com/cloud/price-list/) and its [USD product-pricing endpoint](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?partNumber=B97384,B97385,B91961,B91962&currencyCode=USD), whose data reported a September 9 update:

- E5 OCPU: $0.03/OCPU-hour; E5 memory: $0.002/GB-hour. One matching node is **$0.062/hour** in compute, or **$0.093 for 90 minutes**.
- At an illustrative 730 compute hours/month: two nodes **$90.52**, three **$135.78**, difference **$45.26/month** in compute.
- With the repository's 50GB boot volume and 10 VPU/GB Balanced configuration: $0.0255/GB-month storage plus 10 × $0.0017/GB-month performance = **$2.125/node-month**. A matching third node adds approximately **$47.39/month** including that boot volume; actual partial-month storage is prorated.

This is a 50% increase in worker compute, **not** the total lab bill. Cluster fees, the existing load balancer, other storage, network charges, taxes, credits, and contract discounts are excluded. No resources were purchased to test the estimate.

## Sixty-minute learner model

This is a planning model, not a measured novice study or artificial sleeps added to commands. The updated student section contains approximately **3,510 non-fenced words** before Instructor notes, including optional recovery. Reading at 180 words/minute is about 19.5 minutes; round to 20 for planning.

| Human activity | Simulated allowance |
|---|---:|
| Reading instructions and cautions | 20 min |
| Entering/checking commands and terminal context | 5 min |
| Editing/saving student YAML | 2 min |
| Dashboard navigation and terminal setup | 3 min |
| Interpreting output and recording observations | 8 min |
| Final debrief | 5 min |
| Gross human time | 43 min |
| Planned overlap with installation/burst waits | −4 min |
| **Net modeled human time** | **39 min** |

Use the previous reset/reinstall run, rather than these faster upgrades, for installation allowances. Its measured command subtotal was roughly three minutes; the five-minute burst, initial HPA metrics wait, scale-in, and telemetry catch-up support an **11–12-minute execution/wait allowance** after accounting for overlap. Human discussion during those waits is subtracted only once above.

- **Prepared/cached first-time learner: approximately 50–51 minutes**, leaving 9–10 minutes within the hour. Being a first-time learner does not imply uncached infrastructure if the instructor has prepared images.
- **Uncached first-time environment: add a simulated 6–10 minutes**, giving approximately **56–61 minutes** before troubleshooting. Fresh image/chart downloads and classroom contention were not measured. Sixty minutes is not defensible as an unconditional cold-start promise.
- Keep image/chart preparation, private-repository access, kubeconfig creation, managed add-on readiness, and the exact Bash toolchain in instructor preflight. Students still perform the Helm installs. Do not add discovery, cleanup, direct Prometheus exploration, or node administration to the core hour.
- Retain minute-23 installation and minute-33 application checkpoints; start the five-minute burst by minute 47 and confirm scale-in by minute 55. Skip optional recovery unless scaling is complete by minute 50. Use the final five minutes for debrief/buffer.
- Test with a real first-time learner on Luna before publishing a guaranteed duration. A slower 140-word/minute reading pace adds roughly 5.5 minutes even before other differences.

## Validation and preservation

- Full Helm render/contract suite passed: 12 tests (6.73 seconds wall initially; final assertion-refinement rerun 5.58 seconds).
- Customized-message regression passed with an actual temporary edit to `student.yaml`: eight local tests passed, four upstream tests explicitly skipped for that invocation. The full upstream suite was run separately. The student file was restored byte-for-byte, not left with a test message.
- Python application and mocked lifecycle/validation tests passed: 18 tests, 9.33 seconds wall.
- Terraform formatting, isolated `init -backend=false -lockfile=readonly`, and validation passed. Dependencies went to a new temporary `TF_DATA_DIR`; no live backend initialization, plan, apply, destroy, or state refresh was performed.
- Kustomize rendered successfully; it was not applied over the Helm release. Bash syntax and whitespace checks passed. Documentation checks parsed 47 Bash blocks and verified 37 local file-link targets without failures; this checks syntax/path existence, not live behavior of every optional command.
- ShellCheck was skipped because the binary is unavailable. Security/vulnerability scans and GitLab jobs were not run; neither is implied by the functional passes.

Local Terraform state and backup retained their preflight SHA-256 hashes:

| File | SHA-256 |
|---|---|
| `.oci-local/terraform/terraform.tfstate` | `6827ef45db928401b33ee5c48f9ddf32fe7f5e1e5b7556c7e94940d14e82ca71` |
| `.oci-local/terraform/terraform.tfstate.backup` | `80e4ce0b7df5419eed3717e84d92c567e70c132f594592e702ee3fa58f599f9a` |
| `helm/values/student.yaml` | `3e2c9ff3ddf792c866c0ba97aef9d21fb62db8d8f3ab3c2af0048b49d1da9566` |

Existing edits were retained and extended only where relevant. No credential files, home kubeconfig, Terraform inputs/state, managed add-ons, or unrelated workloads were changed. No commit or push is part of this work.

## Observation limit and handoff

The final timed Grafana sample at **18:17:00 UTC** showed the same pod UID and container start time (**17:53:36**), **zero restarts**, Ready=True, 615Mi sampled memory, and a successful health endpoint. That is **23 minutes 24 seconds of container uptime**, including approximately **19 minutes with the learner dashboard open and configured for 15-second refresh**. During that period the app completed baseline traffic, manual scaling, the five-minute CPU burst, and scale-in. After the initial rise, sampled Grafana memory remained approximately **613–622Mi**, rather than continuing to rise toward its new 1Gi limit. No later Grafana warning/error log entries were found in the bounded check; one initial readiness refusal remained in events from startup.

This is a successful bounded retest of the revised settings, **not a completed 60-minute memory soak or proof against a memory leak**. Before classroom sign-off, run the full-hour dashboard session at expected learner concurrency on Luna, measure a real first-time learner, verify provisioning and automated cleanup, and complete ShellCheck/security scans. Optional pod recovery was already tested in the earlier reset rehearsal and was not repeated here; no node-loss or cold-cache trial was performed.

All six releases are deployed. The app has two Ready replicas, HPA enabled, baseline traffic enabled, and burst mode explicitly false. Public HTTP remains available at `http://132.226.120.202/`. Both original workers, Cert Manager, and Metrics Server remain Ready. The state/student-file hashes above were checked again at the final observation and matched.

Only this retest's sampling loop, two localhost forwards, and two browser tabs were stopped. Existing user processes/tabs were left alone. Reopen a forward using the verified project environment when next using a dashboard; stopping a forward does not uninstall its release. The retained cluster, workers, and load balancer continue to incur their normal charges.
