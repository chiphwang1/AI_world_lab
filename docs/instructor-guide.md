# Instructor delivery and release guide

This file contains instructor notes, preparation, debrief answers, and release checks. The student walkthrough is [README.md](../README.md).

Plan for **90 minutes: 30 minutes of lecture and cluster provisioning, followed by 60 minutes of hands-on work and debrief**. In the README's **Before hands-on** section, students start Luna at workshop minute 0; Luna automatically creates a cluster for each session. Cloning, Console sign-in, kubeconfig creation, chart downloads, and readiness checks belong to hands-on step 1. Prepare desktop tools and repository access beforehand. Students follow [README.md](../README.md); use the same [architecture diagram](architecture.md) in the lecture.

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
| 0–5 | Have students start Luna to begin automatic cluster provisioning. Introduce the app and learning goals. |
| 5–15 | Trace requests and dashboard telemetry on the shared diagram. Identify HPA as an optional extension. |
| 15–20 | Explain Deployment → Pods → Service, chart versus release, and readiness versus liveness. |
| 20 | A helper checks provisioning status and identifies sessions needing intervention. Continue the lecture. |
| 20–30 | Explain desired state and manual scaling; demonstrate repository root, kubeconfig, and the three-terminal layout. |
| 30–40 / lab 0–10 | Begin hands-on step 1: clone, sign in, create kubeconfig, run preflight, and download/check charts. |
| 58 / lab 28 | Mesh and monitoring installed. Intervene on blocked installations. |
| 70 / lab 40 | Public app and baseline traffic working. Intervene before dashboard exploration. |
| 78 / lab 48 | Baseline dashboard observations recorded; begin manual scaling. |
| 85 / lab 55 | Core work ends; record any blocked checkpoint honestly. |
| 85–90 | Debrief using the completion sheet; absorb small delays. |

HPA and pod recovery are optional and do not affect core completion. Offer pod recovery as the shorter, five-minute extension if the core is complete by minute 50. Offer HPA only with at least 15 minutes before debrief (core complete by minute 40). These are early-finisher options, not additional targets for the scheduled core. Otherwise offer a follow-up session with an authorized lab environment. Protect dashboard observation and debrief time. Do not promise that an expired Luna session remains available. Direct Prometheus queries, outages, and OCI alarms are outside this session.

## Before class and the minute-20 check

Prepare desktop tools and verify repository and chart-repository access before the workshop. Students start Luna at workshop minute 0 and do no further setup during the lecture. Students download the charts in hands-on step 1, when they also generate their kubeconfig and check readiness. See [cluster access](cluster-access.md). The revised ten-minute setup target includes downloads; it and the rest of the schedule still need a beginner pilot.

### Luna load balancer quota

Configure each lab session for one flexible load balancer with 10 Mbps bandwidth: `lb-flexible-count=1` and `lb-flexible-bandwidth-sum=10`. The app Service requests this load balancer; Kiali, Grafana, and Prometheus remain internal and need no additional load balancers.

In the September 30 Luna rehearsal, the app Service failed with `QuotaExceeded` for `lb-flexible-bandwidth-sum`. Updating Luna's configuration did not change the active session's quota. A fresh session with the updated allocation successfully created the load balancer and served HTTP. Verify quota changes with a fresh-session deployment before class; students should not need to change quotas or restart their lab to complete the exercise.

### One materials revision

Publish the immutable, annotated tag `lab-2026-09-30.5` in both GitLab (Luna's source) and the public GitHub distribution repository before distributing these instructions. Both tags must contain the same reviewed learner materials and pass the checks below. GitLab and GitHub can retain different commit histories and infrastructure files; do not copy unrelated private history merely to make their commit IDs match. A revision printed in the README does not create a release tag; the student's clone command will fail until that tag is published. This is a versioned materials release; the classroom pilot and other release gates below remain required. Keep the learner files on Luna's published GitLab branch identical to this release during a workshop, and make later materials edits on a separate branch. Do not move an existing release tag.

Students download a **new** checkout with the pinned clone command at the start of hands-on step 1. After cloning, verify the revision in their checkout:

```bash
cd "$HOME/oke-bootcamp"
git describe --tags --exact-match HEAD
```

Expect `lab-2026-09-30.5`. Students skip cloning if that folder exists. Inspect its revision and edits; do not reset, pull over, or delete a learner's work. If it is the wrong revision, prepare a separate directory and supply that path. The GitHub distribution repository is public; its HTTPS clone should not request credentials. Verify unauthenticated access from Luna before class. Do not put credentials in clone URLs or leave an instructor's Git credentials on a shared desktop. An instructor-distributed checkout must retain Git metadata and the release tag for this revision check.

Before publishing or teaching, confirm that both immutable tags exist:

```bash
git ls-remote origin 'refs/tags/lab-2026-09-30.5^{}'
git ls-remote github 'refs/tags/lab-2026-09-30.5^{}'
```

These remote names apply to the maintainer checkout. Different commit IDs are allowed because the repositories can have different histories. Compare the learner files themselves before distributing a release. With read access to both repositories, fetch their tags into separate local refs so neither overwrites the other:

```bash
git fetch origin refs/tags/lab-2026-09-30.5:refs/materials/gitlab
git fetch github refs/tags/lab-2026-09-30.5:refs/materials/github
git diff --exit-code refs/materials/gitlab refs/materials/github -- \
  README.md charts helm \
  docs/architecture.md docs/images/oke-lab-architecture.png \
  docs/cluster-access.md docs/completion-sheet.md docs/completion-sheet.pdf \
  docs/monitoring.md docs/troubleshooting.md docs/instructor-guide.md \
  scripts/check-ready.sh scripts/prepare-charts.sh scripts/validate-lab.sh \
  scripts/test-helm.sh scripts/build-completion-sheet.py \
  scripts/tests/check_mesh_charts.py scripts/tests/test_bootcamp_app.py \
  scripts/tests/test_check_ready.py scripts/tests/test_prepare_charts.py \
  scripts/tests/test_validate_lab.py scripts/tests/test_cluster_access_materials.py \
  scripts/tests/test_lab_materials.py
```

The comparison must produce no differences. Stop distribution if a tag is missing or any listed file differs. If command-line access is unavailable, download and compare these specific files from the authenticated GitLab interface and the GitHub release checkout. Do not export unrelated private project data or publish infrastructure changes as part of a learner-materials update.

Verify Luna displays `Materials revision: lab-2026-09-30.5` and that its PDF/PNG links work. Its learner files must match the GitLab tag. Record both resolved commits on the pilot timing sheet. Do not treat the tags themselves as evidence that classroom testing passed.

A local commit or tag does not update either remote. Review newer work on each remote, publish only the intended materials, and never force-push or move an existing release tag. Complete publication to both repositories and verify the file comparison before distributing the new clone command.

The README uses full Luna Lab Steps URLs for its appendix links because Luna rewrites bare `#heading` links into invalid GitLab file requests. Keep those URLs aligned with this lab ID and the target headings. Check at least one appendix jump in the browser after publication; offline readers can scroll to the named heading.

### Prepare downloads and terminals

Before teaching the learner login flow, verify an actual Luna session exposes the **Luna Lab** desktop icon, **OCI Console** quick link, temporary **Credentials**, and **Oracle Cloud → Compartment Name**. Confirm that compartment matches the one supplied to Terraform and that the learner's identity can see the assigned OKE cluster. These are Luna session features, not outputs to implement by exposing passwords in Terraform. Separately verify desktop OCI CLI authentication and cluster access; browser login alone is insufficient. If these session fields are absent, resolve the Luna configuration before handing off the lab.

During rehearsal, verify these student commands in a fresh checkout of the materials revision:

```bash
bash scripts/prepare-charts.sh --download
bash scripts/prepare-charts.sh --check
```

The first command downloads the five pinned upstream chart archives into `.lab-cache/charts/`; the second checks their names and versions without downloads or cluster calls. Matching existing archives are reused, and mismatched files are left untouched for investigation. Students install these local archives with Helm. No releases are preinstalled by this script. See [Helm pull](https://helm.sh/docs/helm/helm_pull/) and [installing from an archive](https://helm.sh/docs/helm/helm_upgrade/).

Git does not include the ignored chart cache. The student download command populates each new checkout's `.lab-cache/charts/` directory; no instructor file delivery is required. Verify download access and timing from Luna during the pilot, including expected classroom concurrency. Record any preloaded cache so it is not mistaken for a fresh download.

The cache contains no container images. Newly created workers still need registry access; if an approved image-prepull process is used, measure it during the provisioning window after workers exist and record which images were cached. Do not deploy student releases merely to warm the cache, or count warm upgrades as first installs.

During rehearsal, verify the Bash-resolved OCI CLI, kubectl, Helm, Git, and curl, plus the session's OCI authentication and permissions for the full Helm installation. Students find their region and compartment in Luna and their cluster OCID in the Console; no instructor-assigned cluster or context name is required. In hands-on step 1, they generate their own `~/.kube/config`. Verify required OCI environment settings in **each fresh terminal**, especially for the Cloud Shell download alternative. Keep terminal 1 open for connection settings and chart-version variables; open dashboard terminals when the walkthrough calls for them. Do not distribute an instructor's credentials.

At workshop minute 20:

1. Inspect each session's provisioning job. A visible Luna desktop is not proof that OKE is ready. Record pending/failed sessions and assign a helper.
2. Investigate failed provisioning while the lecture continues. Students do not need a kubeconfig or repository checkout yet, and there is no instructor readiness sign-off.

During hands-on step 1, students run `bash scripts/check-ready.sh` using their kubeconfig's current context, then download and check the charts. Help with reported failures before they proceed to installation. Preflight does **not** prove Helm install permissions, all scheduling constraints, or future LoadBalancer availability; validate the lab configuration, managed add-ons, and image access during rehearsal.

Protect the observation and debrief blocks. Use installation waits for the architecture discussion and the manual-scaling wait for readiness and liveness. No extra deployment or deliberate failure is needed for the probe discussion. If setup runs late, send a helper to resolve it; do not replace interpretation time with more commands or silently mark missing observations complete. Keep the last five minutes for debrief and skip both extensions when behind. If an HPA attempt runs short, have the learner reset `traffic.loadEnabled=false` before recording it as blocked; stopping a watch does not stop the burst.

In step 3, have students reach their customized HTTP response before opening detailed pod descriptions. Use the diagram to identify `web` and `istio-proxy`; Appendix B contains optional JSONPath, native-sidecar, and restart-policy checks. Use that appendix for troubleshooting or follow-up study, not as another required checkpoint.

If a cluster cannot be ready at minute 30, use an already authorized, dedicated spare if one is available. Otherwise use an instructor demonstration and record that learner as **demonstration only**, not completed. Starting their full lab late cannot preserve the 90-minute limit. Provisioning inside 30 minutes remains a release requirement to validate, not a promise established by local rehearsal.

Keep two workers for this tested per-learner workload. Validate allocatable capacity for up to six app pods and their proxies, the generator, observability stack, and system pods. A third worker adds scheduling capacity but does not fix kubeconfig mistakes, slow learner navigation, or a container's memory limit. See the measured [two-versus-three-worker assessment](rehearsal-2026-09-21-improvements.md#two-workers-versus-three).

## Debrief answer guide

Use the [completion sheet](completion-sheet.md) to record successful checks and observed values during the walkthrough. Keep students moving through each action and its expected result; save discussion questions for the final debrief.

Use only these three questions for the core debrief:

| Question | What a successful explanation includes |
|---|---|
| What changed when you scaled from two to four pods? | Helm changed the desired app replica count, and Kubernetes created additional pods. The worker count and Service IP stayed unchanged. |
| How do Kiali and Grafana help you understand the application? | Kiali maps service traffic; Grafana charts metrics over time. Both use Prometheus data. Learners can point to the traffic edge and one request-rate, success-rate, or latency reading. |
| What is the difference between a pod and a worker node? | A worker is a machine that runs pods. Each app pod here contains the web app and its Istio proxy. Scaling pods does not add workers. |

Use Ready pod counts to verify scaling; dashboard proxy counts can lag. The baseline generator keeps its two-second request interval as replicas change, so do not require a latency improvement or higher request rate. The learner's curl requests can briefly add traffic.

HPA and recovery remain optional. For an HPA attempt, verify numeric CPU metrics, scale-out above two, return to two Ready app pods, and an explicit load reset. Do not require a peak of six replicas or invented readings for missing panels. These are success checks, not additional debrief questions.

Measure the revised schedule in a beginner pilot; simpler instructions alone do not prove the hour is achievable.

Core completion requires the customized public response, mesh traffic, baseline dashboard readings, manual 2→4→2 scaling observations with unchanged workers and Service IP, and the core debrief. No HPA resource, load burst, or automatic scale-in is required. Missing core evidence needs follow-up, not a checked box. Record HPA and recovery separately as skipped, completed, or blocked; any attempted burst must still be reset. A partner discussion can assess explanations without another quiz.

## Classroom pilot and release gates

**Not yet completed:** a real beginner's full 90-minute Luna run, session-end cleanup with the full workload, expected classroom concurrency, a full-hour dashboard refresh test after the Grafana memory fix, and required security scans. Local tests and this checklist do not substitute for those results. The CI scanner-image allowlist blocker also needs resolution before release.

Run the pilot in a separately authorized, disposable Luna session. Do not reset an existing rehearsal cluster or destroy locally tracked infrastructure merely to satisfy this checklist.

- [ ] Record the repository revision, desktop tools, node shape/count, permissions, and exact provisioning start/Ready/metrics-ready times. Verify provisioning overlaps the lecture and finishes by minute 30.
- [ ] Have a Kubernetes beginner follow the README, including chart downloads after cloning. Record prompts for help, navigation errors, step 1 setup time, and each checkpoint time. Confirm the learner can explain Deployment, Pod, and Service roles and interpret one dashboard change; copying output alone does not demonstrate understanding.
- [ ] Inventory already-installed add-ons/releases and cached charts/images. Measure clean student installs; label any warm reuse. Do not compare a cached upgrade directly with a fresh install.
- [ ] Verify a fresh session receives the configured load balancer count and bandwidth quotas. Deploy the app Service and confirm a public IP and successful HTTP response; preflight alone does not test this allocation.
- [ ] Record command execution/waits separately from reading, editing, typing, and interpreting results. Actual learner delays are measured human time; simulated allowances must be labeled as estimates. Account for overlap once, not twice.
- [ ] Verify both dashboard UIs and manual 2→4→2 scaling with HPA disabled throughout. Finish core work by lab minute 55 and debrief by workshop minute 90. Confirm a student who skips both extensions can complete every core requirement.
- [ ] Separately rehearse optional HPA: numeric CPU metrics, the bounded burst, scale-out, explicit load reset, and scale-in. Measure its duration and test an interrupted attempt's reset. This remains a maintainer release check, not a core student requirement. Verify pod recovery also works without HPA.
- [ ] Run a separate 60-minute dashboard soak before release, since dashboards open partway through the classroom lab. Refresh the lab dashboard every 15 seconds; sample Grafana pod UID, restart count, memory, and events before, during, and after. Require no OOM kills or unexplained restarts and investigate failed queries or broken forwards. Grafana currently requests 512Mi and is limited to 1Gi, with `GOMEMLIMIT=512MiB`.
- [ ] In the authorized pilot, leave releases installed and let Luna's session-end cleanup run. Monitor it through completion and verify the app's OCI LoadBalancer is removed before infrastructure destruction. Confirm no billable leftovers; students must not run a manual uninstall. Follow [cleanup responsibilities](cleanup.md).
- [ ] Test the expected number of simultaneous learner sessions for OCI quotas, launch time, image/chart access, scheduling, and cleanup. One healthy cluster does not validate classroom capacity.
- [ ] Run static/chart/unit checks from [AGENTS.md](../AGENTS.md) and [Helm validation](../helm/README.md#validation-and-release), plus the required security scans. Record skipped/blocked checks explicitly; functional tests are not a security result.

Pilot timing record:

| Phase | Start/end on workshop clock | Measured command/wait time | Measured human time | Overlap | Simulated allowance, if any | Result/blocker |
|---|---|---|---|---|---|---|
| Provisioning + lecture | ___ | ___ | ___ | ___ | ___ | ___ |
| Step 1: clone, access, chart downloads/checks, connection | ___ | ___ | ___ | ___ | ___ | ___ |
| Install components | ___ | ___ | ___ | ___ | ___ | ___ |
| Configure/deploy | ___ | ___ | ___ | ___ | ___ | ___ |
| Observe | ___ | ___ | ___ | ___ | ___ | ___ |
| Manual scaling 2→4→2 | ___ | ___ | ___ | ___ | ___ | ___ |
| Debrief | ___ | ___ | ___ | ___ | ___ | ___ |
| Optional HPA (separate timing) | ___ | ___ | ___ | ___ | ___ | ___ |

Count all step 1 setup within the hands-on hour, including chart downloads and any access troubleshooting. Only provisioning overlaps the lecture. The earlier model included required HPA and was approximately 50–51 minutes with prepared caches and simulated human allowances, or 56–61 with simulated cold-download allowances before troubleshooting. These are not measurements of the revised core. Test the ten-minute setup allowance and protected observation/debrief time with a beginner before claiming that the new schedule fits.

## Maintenance and distribution

The [September 18 rehearsal](rehearsal-2026-09-18.md), [September 21 reset/reinstall](rehearsal-2026-09-21.md), and [follow-up retest](rehearsal-2026-09-21-improvements.md) preserve measured execution times and the Grafana failure/fix. Keep historical measurements distinct from later estimates.

The preflight compatibility check follows the pinned Istio 1.31.x range, Kubernetes 1.32–1.36, and kubectl's one-minor-version skew rule. Review the script and its tests whenever changing these pins. Sources: [Istio supported releases](https://istio.io/latest/docs/releases/supported-releases/) and [kubectl version skew policy](https://kubernetes.io/releases/version-skew-policy/#kubectl).

The public GitHub distribution and GitLab source must publish the same immutable materials tag, `lab-2026-09-30.5`, with matching learner files. Keep unrelated infrastructure and repository history on their existing remotes. Publish both explicitly, without force-pushing, and verify the file comparison described above. Use GitLab's `ci.skip` push option for documentation/materials publication so it does not launch infrastructure jobs; required security scans remain a separate release gate. Follow [packaging notes](../helm/README.md#github-distribution); exclude credentials, local configuration, Terraform state/plans, and operational logs. Keep the diagram in one file so the lecture and README cannot drift apart.

`terraform/` and CI scripts are instructor-managed; `charts/` and `helm/` contain learner deployment materials. Do not mix the legacy `kubernetes/` manifests into the Helm student workflow. See [CI administration](gitlab-ci.md), [local Terraform workflow](maintainer-infrastructure.md), and [cleanup](cleanup.md).

## Suggested Luna description

**Luna title:** OKE Bootcamp: Deploy, Monitor, and Scale an Application

Maintain the Luna Overview using the description below. When publishing lab updates, check both Overview and Lab Steps; updating the README does not update the separately maintained Overview.

Learn the process of deploying, monitoring, and scaling an application on Oracle Kubernetes Engine (OKE), OCI's managed Kubernetes service. You'll use Helm to deploy a customized web application, observe its traffic with Istio, Prometheus, Kiali, and Grafana, and scale its replicas manually. These are common open-source tools for managing and monitoring applications on Kubernetes. Luna creates your cluster and starts cleanup when your session ends.

### What you will build

- **Web application:** A customized application with a public endpoint through an OCI LoadBalancer, installed with Helm, a Kubernetes package manager.
- **Istio service mesh:** Proxies alongside your application containers to manage traffic and report request metrics.
- **Prometheus:** Collects and stores those metrics for Kiali and Grafana to query.
- **Kiali:** Displays service traffic and workload health.
- **Grafana:** Charts metrics over time so you can compare baseline traffic and manual scaling.

A traffic generator sends requests while you explore the dashboards and change the number of application replicas.

### What you will learn

- Customize and deploy an application with Helm.
- Explain how Kubernetes Services keep an application reachable as pods change.
- Follow service traffic in Kiali and interpret request rate, success rate, and latency in Grafana.
- Scale application replicas from two to four and back without changing worker count or Service IP.
- Distinguish readiness from liveness and investigate health warnings.

### Optional extensions

If time permits after the core exercises, use the Horizontal Pod Autoscaler (HPA) to adjust replicas from CPU demand, or replace one pod and observe Kubernetes restore the desired count. Neither extension is required to complete the lab; save them for a follow-up session if needed.

### Before you begin

Launch the lab at the beginning of the lecture so Luna can create your cluster. No other preparation steps are required during the lecture.

During hands-on step 1, you'll download the repository, create the kubeconfig for your own cluster, check readiness, and download the Helm charts. Run commands in a Bash terminal on the Luna desktop, which has the required tools installed.

You should be comfortable copying terminal commands and editing a YAML value. No application coding or container-image build is required.

**Lab duration:** 90 minutes total: a 30-minute lecture while the cluster provisions, followed by 60 minutes of core exercises and debrief. Follow the time guidance in Lab Steps before starting an optional extension.

**Cleanup:** Follow the Finish the lab instructions. Leave the application and Helm releases installed; Luna starts automated cleanup when the session ends or expires.
