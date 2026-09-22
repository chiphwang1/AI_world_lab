# Instructor delivery and release guide

This file contains instructor notes, preparation, debrief answers, and release checks. The student walkthrough is [README.md](../README.md).

Plan for **90 minutes: 30 minutes of lecture and cluster provisioning, followed by 60 minutes of hands-on work and debrief**. Cluster creation starts at workshop minute 0, not before the session. Prepare desktops and repository access beforehand; students clone the repository during the lecture. Students follow [README.md](../README.md); use the same [architecture diagram](architecture.md) in the lecture.

## Published learner handouts

The walkthrough embeds the [architecture PNG](images/oke-lab-architecture.png) and links directly to the printable [completion sheet PDF](completion-sheet.pdf). On Luna, students can use the PDF viewer's download button to save it. Keep the [Markdown completion sheet](completion-sheet.md) as the editable source; the PDF contains no answer key.

After editing the sheet, regenerate its two-page PDF with Python 3 and `reportlab` installed in your maintainer environment:

```bash
python3 scripts/build-completion-sheet.py --output docs/completion-sheet.pdf
```

Render and visually inspect both pages before publishing. The builder rejects unexpected checkpoint/table structure or overflowing paragraphs. Students do not run it or install PDF tooling. Image authoring details are in [the saved generation prompt](images/architecture-prompt.md); verify every arrow against the Helm configuration when revising it. Publish both binary files with their Markdown links and check them in Luna.

## Delivery schedule

“Workshop minute” counts from the start of the lecture. “Lab minute” starts at workshop minute 30. These are facilitation targets, not deadlines for assessing students. Checkpoints assess observed results; intervene early when downloads or cloud readiness threaten the session budget.

| Workshop minute | Activity or readiness gate |
|---|---|
| 0–5 | Start each assigned cluster's provisioning. Have students clone the repository using README step 1. Introduce the app and learning goals. |
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

Prepare the desktop and repository access before the workshop. Download the pinned chart archives in advance where possible, then copy them into each learner's checkout after the learner clones it during the lecture. Start cluster provisioning at workshop minute 0 as planned, then finish chart preparation, cluster authentication, and readiness checks during the lecture. The hands-on clock starts after these checks pass. Never infer the assigned cluster from whatever context happens to be current. See [cluster access](cluster-access.md).

### One materials revision

Publish the immutable, annotated tag `lab-2026-09-22.1` in both GitLab (Luna's source) and the private GitHub distribution repository before distributing these instructions. Both tags must identify the same commit containing these updated instructions and pass the remote checks below. A revision printed in the README does not create a release tag; the student's clone command will fail until that tag is published. This is a versioned materials release; the classroom pilot and other release gates below remain required. Keep Luna's published GitLab branch at this revision during a workshop, and make later edits on a separate branch. Do not move an existing release tag.

Students download a **new** checkout with the pinned clone command in README step 1. After cloning, verify the revision in their checkout before handoff:

```bash
cd "$HOME/oke-bootcamp"
git describe --tags --exact-match HEAD
```

Expect `lab-2026-09-22.1`. Students skip cloning if that folder exists. Inspect its revision and edits; do not reset, pull over, or delete a learner's work. If it is the wrong revision, prepare a separate directory and supply that path. The repository is private: resolve learner access beforehand, avoid credentials in clone URLs, and do not leave an instructor's Git credentials on a shared desktop. An instructor-distributed checkout must retain Git metadata and the release tag for this revision check.

Before publishing or teaching, compare these remote outputs. Both `refs/heads/main` values and both peeled tag values (`^{}`) must match the selected release commit. Stop on a missing or different value; a successful GitLab push alone does not synchronize GitHub.

```bash
git ls-remote origin refs/heads/main 'refs/tags/lab-2026-09-22.1^{}'
git ls-remote github refs/heads/main 'refs/tags/lab-2026-09-22.1^{}'
```

These remote names apply to the maintainer checkout. Verify Luna displays `Materials revision: lab-2026-09-22.1` and that its PDF/PNG links work. Record the resolved commit on the pilot timing sheet. Do not treat the tag itself as evidence that classroom testing passed.

A local commit or tag does not update either remote. When publication is approved, review both remotes for newer work, then push the same reviewed commit and annotated tag to both without force. Use an atomic push per remote so its branch and tag update together. If either push fails, stop distribution until both pass the checks above; atomic pushes do not span two repositories.

The README uses full Luna Lab Steps URLs for its appendix links because Luna rewrites bare `#heading` links into invalid GitLab file requests. Keep those URLs aligned with this lab ID and the target headings. Check at least one appendix jump in the browser after publication; offline readers can scroll to the named heading.

### Prepare downloads and terminals

Before teaching the learner login flow, verify an actual Luna session exposes the **Luna Lab** desktop icon, **OCI Console** quick link, temporary **Credentials**, and **Oracle Cloud → Compartment Name**. Confirm that compartment matches the one supplied to Terraform and that the learner's identity can see the assigned OKE cluster. These are Luna session features, not outputs to implement by exposing passwords in Terraform. Separately verify desktop OCI CLI authentication and cluster access; browser login alone is insufficient. If these session fields are absent, resolve the Luna configuration before handing off the lab.

After a learner clones the repository, run these commands from that checkout before the hands-on clock. Alternatively, copy the matching `.lab-cache/charts/` archives prepared in advance into that checkout, then run `--check` there:

```bash
bash scripts/prepare-charts.sh --download
bash scripts/prepare-charts.sh --check
```

The first command downloads the five pinned upstream chart archives into `.lab-cache/charts/`; the second checks their names and versions without downloads or cluster calls. Matching existing archives are reused, and mismatched files are left untouched for investigation. Students install these local archives with Helm. No releases are preinstalled by this script. See [Helm pull](https://helm.sh/docs/helm/helm_pull/) and [installing from an archive](https://helm.sh/docs/helm/helm_upgrade/).

The ignored chart cache must be prepared separately for every desktop or included in the prepared learner bundle. It contains no container images. Newly created workers still need registry access; if an approved image-prepull process is used, measure it during the provisioning window after workers exist and record which images were cached. Do not deploy student releases merely to warm the cache, or count warm upgrades as first installs.

Verify the actual Bash-resolved OCI CLI, kubectl, Helm, Git, and curl. Supply the assigned cluster name, OCID, region, compartment, expected context, and prepared OCI identity. Guide students through Console-based kubeconfig setup in the README, preferably during the lecture demonstration after their cluster is ready. They obtain their own `~/.kube/oke-lab`; do not distribute an instructor's credentials. Verify any required OCI environment settings in **each fresh terminal**, especially for the Cloud Shell download alternative. Arrange Helm install permissions separately; students do not troubleshoot credentials or permissions during the hour. Open three labeled Bash terminals (commands, Kiali, Grafana), the student values file in the editor, and the completion sheet. Do not start dashboard forwards until their Services exist. Measure the revised setup in the next pilot rather than assuming the five-minute connection target is proven.

At workshop minute 20:

1. Inspect each session's provisioning job. A visible Luna desktop is not proof that OKE is ready. Record pending/failed sessions and assign a helper.
2. For clusters with a reachable API, run the following from the prepared checkout with that learner's kubeconfig and OCI environment. Replace the placeholder with the independently assigned context:

   ```bash
   bash scripts/check-ready.sh --context '<instructor-assigned-context>'
   ```

3. Check the managed Cert Manager and Metrics Server add-ons are healthy and that permissions and image access have been validated. Confirm the materials revision and `prepare-charts.sh --check` in the learner's checkout. The cluster preflight does **not** prove Helm install permissions, all scheduling constraints, or future LoadBalancer availability.
4. Resolve missing authentication, old binaries, add-on readiness, or failed provisioning before minute 30. Re-run preflight in a fresh learner terminal. Do not silently switch a learner to another person's or a production cluster.

Protect the observation and debrief blocks. Use installation waits for the architecture discussion and the five-minute load burst for the metrics-source explanation. If setup runs late, send a helper to resolve it; do not replace the learner's interpretation time with more setup commands or silently mark missing observations complete. Keep the last five minutes for debrief and skip optional recovery when behind.

If a cluster cannot be ready at minute 30, use an already authorized, dedicated spare if one is available. Otherwise use an instructor demonstration and record that learner as **demonstration only**, not completed. Starting their full lab late cannot preserve the 90-minute limit. Provisioning inside 30 minutes remains a release requirement to validate, not a promise established by local rehearsal.

Keep two workers for this tested per-learner workload. Validate allocatable capacity for up to six app pods and their proxies, the generator, observability stack, and system pods. A third worker adds scheduling capacity but does not fix kubeconfig mistakes, slow learner navigation, or a container's memory limit. See the measured [two-versus-three-worker assessment](rehearsal-2026-09-21-improvements.md#two-workers-versus-three).

## Debrief answer guide

Use the [completion sheet](completion-sheet.md) to assess both observations and explanations. At each prediction, wait about 30 seconds before giving the explanation: students state or write a prediction, inspect the existing output, then explain the result to a partner or instructor. Ask "Which value supports that?" before correcting an answer. Use the existing install/load waits and checkpoint time; do not add another quiz. Do not require a peak of six replicas or invent readings for missing panels.

Listen for a reason, not only a correct tool name. For example, a learner should connect HPA CPU input to Metrics Server and identify a request-rate or latency reading supplied by Prometheus. For the Running/Ready question, let the learner distinguish traffic eligibility from restart behavior before confirming that a Running pod can be unready with zero restarts. Reveal the answer guide after the learner has attempted the explanation.

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

The private GitHub mirror and GitLab source must publish the same immutable materials tag, `lab-2026-09-22.1`, and matching main-branch commit for Luna. Publish both explicitly, without force-pushing, and verify the remote hashes as described above. Use GitLab's `ci.skip` push option for documentation/materials publication so it does not launch infrastructure jobs; required security scans remain a separate release gate. Follow [packaging notes](../helm/README.md#github-distribution); exclude credentials, local configuration, Terraform state/plans, and operational logs. Keep the diagram in one file so the lecture and README cannot drift apart.

`terraform/` and CI scripts are instructor-managed; `charts/` and `helm/` contain learner deployment materials. Do not mix the legacy `kubernetes/` manifests into the Helm student workflow. See [CI administration](gitlab-ci.md), [local Terraform workflow](maintainer-infrastructure.md), and [cleanup](cleanup.md).

## Suggested Luna description

Deploy, monitor, and scale an application on a Luna-provisioned Oracle Kubernetes Engine (OKE) cluster. Use Helm, a package manager for Kubernetes, to install and configure your application and monitoring tools. Istio manages application traffic and reports request metrics; Prometheus collects and stores those metrics; Kiali maps service traffic and health; and Grafana charts metrics over time. Generate traffic, compare request rates and latency, and observe manual scaling and CPU-based autoscaling. Optionally, replace one application pod and watch Kubernetes restore the replica count.

### What you will build

- **Application on OKE:** A customized Helm deployment running on your Luna-provisioned cluster, exposed through an OCI LoadBalancer.
- **Istio service mesh:** Proxies alongside your application containers to observe traffic.
- **Prometheus metrics store:** Collects and stores request metrics from Istio for Kiali and Grafana to query.
- **Kiali traffic graph:** Maps communication between services and shows request rates, errors, latency, and workload health.
- **Grafana dashboard:** Plots metrics over time so you can compare baseline traffic, load, and scaling.
- **Traffic and autoscaling:** A traffic generator and Horizontal Pod Autoscaler (HPA) to demonstrate how application replicas respond to CPU demand.

### What you will learn

- Customize and deploy an application with Helm.
- Explain how Kubernetes Services keep an application reachable as pods change.
- Explore service traffic in Kiali and compare baseline and load metrics in Grafana.
- Scale replicas manually and observe CPU-based HPA scale-out and scale-in.
- Distinguish readiness from liveness and investigate health warnings.
- Optionally, replace one application pod and observe Kubernetes restore the desired replica count.

### Before you begin

Have these ready before the hands-on portion:

- Access to your assigned Luna desktop and lab repository or prepared checkout.
- Your assigned cluster details/context and prepared OCI credentials, provided by the instructor; obtain your own kubeconfig using the Console instructions in step 1.
- A Bash terminal with OCI CLI, kubectl, Helm, Git, and curl installed; the instructor prepares these tools.
- Basic familiarity with terminal commands and editing a YAML file.

**Lab duration:** 60 minutes, including hands-on exercises and debrief. Complete the introductory lecture and cluster provisioning before the lab timer starts.

**Note:** Use only your assigned training cluster. No manual infrastructure cleanup is required from students; Luna starts automated cleanup when the session ends or expires.
