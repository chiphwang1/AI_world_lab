# Existing-cluster end-to-end rehearsal — 2026-09-21

Historical baseline: the findings and handoff below describe the unmodified reset/reinstall run. See the [subsequent fixes and retest](rehearsal-2026-09-21-improvements.md) for the approved Grafana, documentation, and test changes. The original failure evidence is retained here.

## Result

The application, mesh, public endpoint, manual scaling, HPA **2 → 6 → 2**, and optional pod recovery worked on the existing Phoenix cluster. **The unmodified configuration is not ready for classroom sign-off:** Grafana repeatedly restarted during dashboard use, with the second termination explicitly recorded as `OOMKilled` at its `512Mi` limit. Restarting its local port-forward restored browser access but did not fix the underlying memory problem.

This is a reset-and-reinstall rehearsal, not the earlier 24-second warm health-check continuation. It is still **not a cold-node or Luna rehearsal**. The first-time learner model is **55–60 minutes without troubleshooting**, with insufficient margin for the observed Grafana fault. Final scale-in, timing assumptions, and preservation evidence follow below.

## Scope and initial state

- Repository: `/Users/chipinghwang/Desktop/projects/AI_world_lab`; HEAD `3f7cbe76e7f40a54e09a9f9f58b78bbceba83f63`, with existing uncommitted documentation edits. Tested README SHA-256: `bc7e2d128029c973e9c59458b1b499ab0508f8d58151b0e5917029bc7c1024fd`.
- Cluster: `oke-bootcamp-rehearsal-20260918`, context `context-oke-bootcamp-rehearsal-20260918-ctcyaybtyaq`, region `us-phoenix-1`, Kubernetes `1.36.1`. OCI confirmed the target cluster was ACTIVE.
- Two existing Ready workers: `10.0.148.15` and `10.0.154.61`. No node, cluster, network, volume, or Terraform infrastructure changes were made.
- `.oci-local/env.sh` selected the existing project kubeconfig and OCI authentication. The README's example `~/.kube/oke-lab` does not exist on this workstation; its documented instructor-supplied-path alternative was used in every terminal.
- Before reset, all six lab Helm releases already existed. The application had four Ready replicas and a baseline generator; HPA was absent. Cert Manager and Metrics Server were already installed as managed add-ons and were retained.
- Node inventories showed cached Python, curl, Istio, and monitoring images; Helm repositories/cache were already populated. Application events explicitly reported images already present. No caches were cleared and no workers were recreated.
- Existing `oke-lab` and `istio-system` namespaces were retained. Fifteen Istio CRDs marked with Helm's keep policy were retained. This avoided a broad cluster-scoped deletion, but means first-time CRD creation was not measured.
- Pinned charts: Istio `1.31.0`, Prometheus `29.30.0`, Kiali `2.32.0`, Grafana `13.2.5` / Grafana app `13.2.2`; local application chart `0.2.0`.

Read `AGENTS.md`, `README.md`, `docs/cleanup.md`, `docs/rehearsal-2026-09-18.md`, and the relevant Helm/access/testing files before operating. Existing user edits were preserved; README was not rewritten during the test. The learner message was temporarily customized to `Hello from chip's OKE bootcamp`, installed, then the local student values file was restored byte-for-byte. Subsequent upgrades retained the deployed message with `--reuse-values`.

## Reset, outside the learner clock

Inventory and ownership checks identified only these six student releases for removal. Uninstallation used Helm's normal resource ownership, not namespace or CRD sweeps.

| Release | Measured uninstall elapsed |
|---|---:|
| hello-oke | 18.35 s |
| grafana | 1.63 s |
| kiali-server | 1.64 s |
| prometheus | 1.53 s |
| istiod | 1.78 s |
| istio-base | 1.94 s |
| Total Helm uninstall execution | 26.87 s |

Reset started at `17:22:03 UTC`. The old Kubernetes Service and OCI load balancer at `129.153.93.167` were removed. Its OCI display name matched the old Service UID. Authenticated OCI listing no longer returned it; a direct lookup at `17:22:51` returned 404 after the same credentials had successfully read it before deletion. A second successful list was empty. Remaining terminating lab pods cleared before the learner start at `17:23:23`.

Old ephemeral monitoring history and the previous public IP were intentionally lost. No Terraform destroy/apply/refresh was run. Charges continue for the retained cluster/workers and the newly installed application load balancer.

## Measured learner command execution

Times are `/usr/bin/time -p` real elapsed seconds, including command-side networking/readiness waits. They do **not** include modeled reading, editing, typing, interpretation, or debrief. Short untimed inventory commands and agent/browser orchestration are not silently included in this subtotal. The five-minute burst and HPA reconciliation are separate intervals, not additional Helm execution.

| Operation | Measured elapsed |
|---|---:|
| Initial connection, versions, nodes/metrics and checkout checks | 3.17 s |
| Compatible-client verification after PATH correction | 1.72 s |
| Helm repository setup/update, existing repositories | 1.30 s |
| Install istio-base | 6.36 s |
| Install istiod | 4.80 s |
| Install Prometheus | 35.91 s |
| Install Kiali | 43.18 s |
| Install Grafana | 15.87 s |
| Strict application lint | 0.14 s |
| Install customized application / new LoadBalancer | 35.70 s |
| First public HTTP request | 0.11 s |
| Enable baseline traffic | 6.01 s |
| Manual scale 2 → 4 | 8.68 s |
| Ten external HTTP requests at four replicas | 1.10 s |
| Restore manual count to two | 2.06 s |
| Enable HPA | 2.20 s |
| Enable five-minute load | 6.28 s |
| Explicitly disable burst mode | 5.68 s |
| **Primary timed-command subtotal** | **180.27 s** |
| Final explicit HPA wait, started late in scale-in | 22.74 s |
| Final application rollout check | 1.73 s |
| **Timed-command subtotal including those two checks** | **204.74 s** |

The last two checks overlap the scale-in interval below; do not add them again when constructing an end-to-end estimate. Uninstall, maintainer static checks, optional recovery, and diagnostic commands are outside this table.

Monitoring installation wall interval was `17:23:26–17:25:38` (2m12s); the repository/install command subtotal was 1m47.42s. The difference includes intermediate checks and orchestration. App installation started at `17:26:14`; inventory and successful HTTP were complete at approximately `17:26:53`. Baseline traffic started with the upgrade at `17:29:56` and was checked by `17:30:05`.

Manual scaling began at `17:33:29`. HPA was created at `17:33:49`, initially showed `<unknown>`, and reported valid CPU metrics with `ScalingActive=True` at `17:34:19` (30 seconds). A brief ownership-transfer dip was observed, as the README warns; it settled at two Ready replicas before load.

The traffic log recorded burst start at `17:35:19.047`. HPA rose through 3 to 6 replicas by approximately `17:36:19`; all six were confirmed `2/2 Ready` by `17:36:45`. No workers were added. The load interval and learner model are below.

## Checkpoint evidence

| Checkpoint | Evidence / result |
|---|---|
| Connection | Correct context; two Ready nodes; numeric CPU metrics |
| Mesh/monitoring installation | All five releases deployed, all monitoring pods initially Ready |
| Customized application | Two `2/2` pods; public JSON included the customized message and pod name |
| New public endpoint | `132.226.120.202`; first curl succeeded, without retry |
| Sidecar injection | `web` is in `spec.containers`; `istio-proxy` is a restartable native sidecar in `spec.initContainers` |
| Baseline generator | Ready generator; logs contained successful `/` responses approximately every two seconds |
| Kiali browser | Namespace `oke-lab`, last five minutes, refresh enabled; green generator → service → app graph, 100% success |
| Grafana browser | Anonymous Viewer access; provisioned dashboard, last 30 minutes, 15-second refresh; baseline and load panels rendered |
| Manual scaling | 2 → 4 → 2; all four Ready; ten successful curls returned all four pod names; public IP unchanged |
| HPA scale-out | Valid `web` CPU metric, target 60%; peak six Ready app pods; public HTTP still succeeded |
| HPA scale-in | 6 → 3 → 2; two Ready application pods, CPU 1%; burst flag false |
| Final Grafana observation | After forward recovery, browser showed 0.49 requests/s, 100% success, two proxies and the historical six-proxy peak |
| Optional pod recovery | One named application pod replaced; two Ready pods and successful HTTP afterward |
| Dashboard reliability | Failed: recurring Grafana container exits interrupted its forward; one explicitly OOMKilled |

### Recorded observations

The API values below use the exact provisioned dashboard PromQL, queried through Grafana's anonymous data-source proxy to obtain reproducible numerical latency values. Browser rendering was separately verified; API results were not substituted for browser verification. Grafana uses one-minute rates while Kiali was displaying a five-minute window, so their rates need not match.

| Phase | HPA / Ready app pods | Requests/s | Success | p95 latency | App proxies up |
|---|---|---:|---:|---:|---:|
| Baseline | HPA absent / 2 | 0.48 (browser) | 100% | 0.975 ms (query at 17:31:00) | 2 |
| Load, 17:38:09 UTC | 6 / 6 | 9.756 | 100% | 427.289 ms | 6 |
| After scale-in, approximately 17:43 UTC | 2 / 2 | 0.49 (browser) | 100% | 0.996 ms (query at 17:43:48) | 2 |

At `17:42:22`, after Kubernetes had returned to two replicas, the query still counted five proxies; it reached two by `17:43:12`. This demonstrates discovery/scrape lag rather than a failed HPA scale-in.

During the rise, the Grafana browser showed 6.71 requests/s and only four scraped proxies while Kubernetes had already reached six. Kiali retained the green generator edge during load. An `unknown` source also appeared after external curls; this is expected for traffic without a source mesh identity, not proof of failure. The expensive `/work` phase is a different workload from baseline `/`; latency differences do not isolate the benefit of scaling.

## Findings and recommended changes — not applied

### 1. Grafana memory is a release blocker

The OKE troubleshooting skill guided a read-only investigation of pod state, previous logs, events, node conditions, and resource metrics. Its discovery/correlation helper scripts were missing at their referenced paths, so already-verified cluster identity and scoped direct commands were used. No node debug pods or infrastructure changes were made.

| Rank | Hypothesis | Confidence / score | Evidence |
|---|---|---|---|
| 1 | Grafana's current memory allowance is insufficient for the observed dashboard workload, killing the container and breaking its forward | High / 10 | At 17:36:58 the runtime recorded `OOMKilled`, exit 137, limit 512Mi; shortly before, `kubectl top` showed 497Mi; the forward failed at 17:36:59 |
| 2 | The first restart had the same memory cause | Medium / 7 | First exit at 17:32:58 was 137 but reason was only `Error`; later repeat was explicitly OOMKilled |
| 3 | Readiness/liveness probes themselves caused the confirmed second restart | Low / 1 | Readiness failures occurred during unavailable/startup periods; decisive termination reason was OOMKilled, not a recorded liveness kill |

Timeline: first restart `17:32:58`, forward lost `17:32:59`; recovered forward verified `17:34:51`. Second OOM `17:36:58`, forward lost `17:36:59`, container running again `17:37:10`. Local forward restarted again at `17:37:51`. Nodes remained Ready with MemoryPressure=False. Previous Grafana logs showed successful queries shortly before termination, without an application exception explaining the kill.

A third termination at `17:39:43` was recorded as `Error`, exit 137. A final temporary forward allowed verification of the completed graphs at approximately `17:43:24`, then failed again at `17:44:12`. The subsequent inventory caught Grafana in `CrashLoopBackOff`. These additional exits must not be represented as a stable recovery. Only the second exit's OOM reason was established directly; the underlying source of memory growth remains unproven.

Before teaching: reproduce with one fresh learner browser, investigate memory growth, and test a larger request/limit or a verified lower-footprint configuration on the same nodes. For example, 512Mi requested / 1Gi limited is a **candidate experiment, not a tested fix**. Measure memory through at least a full session before choosing values. Existing user dashboard tabs were left open; this was not a controlled single-tab memory test. Neither a memory leak nor the exact minimum safe limit has been established.

Keep Appendix A's listener/HTTP/restart instructions, but add a branch for repeated failures: inspect `restartCount`, `lastState`, limits, and previous logs. Restarting a forward is only a recovery step, not resolution of recurring OOMs. Do not disable probes. Prometheus did not restart, so telemetry history remained available after Grafana recovery.

### 2. Native-sidecar check omits the proxy

The step 3 JSONPath only displays `spec.containers`, which returned `web` despite `2/2 Ready`. Replace it in a follow-up README change with a check covering both lists:

```bash
kubectl -n oke-lab get pods -l app=hello-oke \
  -o jsonpath='{range .items[*]}{.metadata.name}{": containers="}{.spec.containers[*].name}{"; initContainers="}{.spec.initContainers[*].name}{"\n"}{end}'
```

Explain that a native sidecar can appear under initContainers and remain running; distinguish it from the completed `istio-init` container. Do not teach students that the missing name means injection failed.

### 3. Verify the actual Bash toolchain

Non-login Bash initially resolved kubectl `1.34.3`, while OKE runs `1.36.1`; this is outside the supported one-minor client skew. The installed Rancher Desktop kubectl `1.36.0` was selected by a process-local PATH change. Helm changed from `4.0.4` to the available `4.0.5` with that PATH. No software or permanent shell configuration was changed. Monitoring installed using the original toolchain; application/scaling used the corrected one. See the [Kubernetes version-skew policy](https://kubernetes.io/releases/version-skew-policy/).

Instructor preflight should verify `command -v kubectl`, `kubectl version`, and `helm version` in the exact Bash environment students will use. Working in zsh does not prove Bash resolves the same binaries. Provide a prepared, verified kubeconfig path in every dashboard terminal.

### 4. Smaller clarity/test issues

- Grafana chart NOTES print administrator-login commands even though the lab correctly requires no login. Tell students to follow the lab's Viewer URL and ignore those generic NOTES; do not retrieve the admin secret.
- Immediately after enabling burst mode, `kubectl logs deployment/hello-oke-traffic` selected the old terminating baseline pod. A later invocation correctly selected the new pod and showed `CPU load started`. Add a brief rollout/log-selection note in the appendix; stale baseline logs do not prove burst mode failed.
- Startup app readiness warnings (HTTP 500) cleared, and all Ready app containers had zero restarts. A transient probe warning or Kiali badge is not sufficient to diagnose liveness failure.
- The maintainer chart test hard-codes the default student message. It failed while the prescribed student customization was present, then passed after restoring the file. Make the test use its own fixture/explicit value instead of depending on an untouched learner file. This does not affect `helm lint` or the deployed exercise.
- Shell comments paste correctly in the required Bash terminal. Preserve the repository-root and fresh-terminal setup guidance already moved to Appendix A.

## Static and supplemental validation

- Passed Terraform formatting, `init -backend=false -lockfile=readonly`, and `validate`. Initialization used a new temporary `TF_DATA_DIR`; live local state/backend was not initialized or modified.
- Passed Kustomize rendering only; legacy manifests were **not** applied over the Helm app.
- Passed full Helm lint/render contract suite: 11 tests, including upstream charts, 8.46 seconds for the successful invocation. The first invocation had one default-message assertion failure described above; it is not hidden by the rerun.
- Passed 18 Python regression tests, 8.33 seconds wall time.
- Passed Bash syntax checks and `git diff --check`.
- `scripts/validate-lab.sh` passed during six-replica load in 11.49 seconds, checking nodes, app rollout, events, and external HTTP. It does not validate Grafana reliability.
- The same live validation passed again after optional recovery in 11.54 seconds, returning the replacement pod's name through the public endpoint.
- ShellCheck skipped: binary not installed. Bash syntax checking is not a substitute.
- Vulnerability/security scanners and GitLab security jobs were not run. Existing analyzer-image restrictions remain unverified; functional success is not a security assessment.

## Final cycle, timing model, and preservation

### Completed scaling and optional recovery

- Automatic load completion: `17:40:19.156 UTC`, **300.109 seconds** after the start log. Successful low-rate `/` responses followed immediately.
- Explicit burst reset: upgrade started `17:40:56`, finished `17:41:02`, **5.68 seconds**. Final release values have `traffic.enabled=true`, `traffic.loadEnabled=false`, and `autoscaling.enabled=true`.
- HPA's final `lastScaleTime`: `17:41:50`, approximately **91 seconds after automatic burst completion**. The watch showed six, then three, then two replicas.
- At `17:42:09`, HPA current count was two at 1% CPU and the Deployment rollout was complete, with two Ready non-terminating app pods. One removed pod was still terminating in the raw listing. By `17:43:08`, only the two app pods and one generator remained.
- Grafana's final browser verification at approximately `17:43:24` showed two proxies, 0.49 requests/s, 100% success, Istiod scrape health 1, and both burst and scaling history. No manual dashboard import/login was needed.
- Learner-path wall interval: `17:23:23–approximately 17:43:24`, **about 20 minutes**. This includes agent/browser control delays, diagnostic interruptions, and report drafting during the burst. It is **not** a stopwatch measurement of a student completing the lesson, nor a pure execution subtotal. Two early browser automation calls alone took about 143 seconds.
- Optional recovery was tested separately after the core observations, not included in the 60-minute core model: `17:43:52–17:44:30` (**38 seconds wall**). Pod `hello-oke-69d76c6f7f-99wgl` was explicitly resolved as an app ReplicaSet member, deleted normally, and replaced by `hello-oke-69d76c6f7f-fk5l2`. Delete waited 32.92 seconds; rollout check took 1.79 seconds. Two pods were `2/2 Ready`, HPA remained at two, and the same public IP returned the customized message. This proves recovery and post-recovery reachability, not uninterrupted availability throughout deletion.

### Simulated human delays, explicitly separate

These are planning assumptions, **not measured human behavior and not artificial sleep time added to commands**. They assume a learner comfortable navigating a terminal, pasting commands, and editing YAML, as the README requires.

| Learner activity | Modeled time | Basis |
|---|---:|---|
| Read instructions, vocabulary, tables and cautions | 19 min | About 3,429 non-fenced words before instructor notes, including optional instructions, at approximately 180 words/minute |
| Enter/check commands and terminal environment | 5 min | Copy/paste, check context/directory, stop watches correctly |
| Edit/save student YAML | 2 min | Open editor, change one message, preserve indentation |
| Open/navigate dashboards and terminals | 3 min | Start two forwards, select namespace/range, find panels |
| Interpret output, record observations and answer predictions | 8 min | Distinguish proxies/pods, metrics sources, CPU requests and scaling |
| Final debrief | 5 min | Complete the five end-of-lab questions |
| **Gross human allowance** | **42 min** | No claim that an actual novice was observed |
| Planned overlap with installation/load waits | **−4 min** | Read component/probe notes and discuss metrics during existing waits; not extra waiting |
| **Net modeled human time** | **38 min** | Do not subtract additional overlaps elsewhere |

For planning, allow **11–12 minutes** for commands and essential cluster/telemetry waits, derived from the measured roughly 3-minute primary command subtotal, five-minute burst, initial HPA metrics delay, roughly 110 seconds to confirm scale-in, and roughly one minute for final proxy telemetry to catch up. This is a rounded critical-path allowance, not a second measured command total; the burst-reset and final explicit wait are counted within their overlapping intervals.

- **Prepared/cached, fault-free learner estimate: 49–50 minutes** (38 human + 11–12 execution/waits).
- **Additional first-time allowance: 6–10 minutes** for uncached image/chart transfer, CRD setup, registry variability, and slower cloud load-balancer readiness. This allowance is simulated; fresh image pulls and classroom network contention were not measured. This run created a new LB, so it does not reuse the old LB's readiness time.
- **First-time, fault-free estimate: 55–60 minutes.** Repeated Grafana failures, missing credentials, slower reading, or registry delays can push it beyond an hour. Reading at 140 rather than 180 words/minute alone adds about 5.5 minutes.
- Optional recovery adds about **five learner minutes**, despite its much shorter measured command time; retain the README's minute-50 gate. It is not promised as part of the core hour.

### Adjustments to make 60 minutes defensible

1. Resolve and soak-test Grafana's memory problem first. A working screenshot after a restart is insufficient for classroom readiness.
2. Prepare the exact Bash toolchain, repository access/checkout, kubeconfig in fresh terminals, managed add-ons, and capacity before the clock starts. Keep OCI CLI for kubeconfig authentication; cluster discovery and cleanup OCI calls in this report are maintainer operations, not extra student exercises.
3. Prefer instructor-prepulled images for the hour-long lab while keeping the Helm installations as student tasks. That preserves the learning objective and recovers the modeled 6–10-minute cold-cache risk. If cold nodes are required, reserve a longer session until a true cold Luna trial supports the timing.
4. Retain installation/app checkpoints at minutes 23 and 33. Aim to start the CPU burst by minute 47, finish its five minutes by 52, and verify scale-in by 55; preserve the final five minutes for debrief. Intervene before these gates slip rather than shortening the five-minute observation.
5. Fix the native-sidecar command, clarify Grafana NOTES, and keep exceptional PATH, stale-log and recurring-OOM diagnostics in the appendix. Do not move troubleshooting back into the main learner flow.
6. Run the revised version with a real first-time learner and the expected Luna concurrency. Validate Luna provisioning and session-end cleanup separately; neither was exercised here. Record a tested repository revision, not just chart versions.

### Preservation and handoff

All six lab releases are left installed. The application has two Ready replicas, HPA is enabled, baseline traffic continues, and burst mode is disabled. Both original nodes, managed Cert Manager, and Metrics Server remain Ready. Istiod, Prometheus and Kiali remained healthy with zero restarts in the final inventory. **Grafana remains an unresolved reliability issue; no resource-limit change or rollout restart was applied.**

Only rehearsal-owned local watches/forwards were stopped; Grafana forwards had already exited on container failures. Only rehearsal-created browser tabs were closed. Existing user tabs/processes were not killed. Dashboard localhost URLs require a new forward when next used. The application remains reachable at `http://132.226.120.202/` while these resources remain running.

Pre-existing edits to `AGENTS.md`, `README.md`, `docs/monitoring.md`, `docs/troubleshooting.md`, `helm/README.md`, and the untracked `docs/cluster-access.md` were retained. Their SHA-256 values matched the preflight baseline, as did the restored `helm/values/student.yaml`. This report is the only retained source/documentation change from the rehearsal; normal tool caches and a temporary Terraform validation directory may remain. Nothing was committed or pushed.

Local infrastructure-state hashes remained unchanged:

| File | SHA-256 |
|---|---|
| `.oci-local/terraform/terraform.tfstate` | `6827ef45db928401b33ee5c48f9ddf32fe7f5e1e5b7556c7e94940d14e82ca71` |
| `.oci-local/terraform/terraform.tfstate.backup` | `80e4ce0b7df5419eed3717e84d92c567e70c132f594592e702ee3fa58f599f9a` |

No cluster recreation, infrastructure destruction, credentials export/commit, Terraform state mutation, or cleanup of unrelated resources occurred. The approved reset removed the previous student workloads, Helm release history, ephemeral telemetry and old LB; reinstallation restored the workload stack with a new public IP, not the old history.
