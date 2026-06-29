# Issues Tackled & Resolutions

## 1. Runner Pod Ephemeral Lifecycle
**Issue:** `kubectl exec` into runner pod failed with `NotFound` because ephemeral runner pods die immediately after a job completes.

**Resolution:** This is expected behavior. Use `kubectl get pods -n actions-runner-system -w` to watch pods and exec in while a job is running.

---

## 2. DNS Resolution for ArgoCD Ingress
**Issue:** `curl -k https://argocd-server.argocd.test.com` failed with `Could not resolve host`.

**Resolution:** The correct hostname was `argocd.test.com` (from ingress). Added it to `/etc/hosts`:
```bash
echo "127.0.0.1 argocd.test.com" | sudo tee -a /etc/hosts
```

---

## 3. Exposed GitHub PAT Token
**Issue:** GitHub PAT token was accidentally shared in terminal output.

**Resolution:** Revoked the token at `https://github.com/settings/tokens`, created a new one with `repo` and `workflow` scopes, updated the Kubernetes secret:
```bash
kubectl delete secret controller-manager -n actions-runner-system
kubectl create secret generic controller-manager \
  -n actions-runner-system \
  --from-literal=github_token=<new-token>
kubectl rollout restart deployment/actions-runner-controller -n actions-runner-system
```

---

## 4. Runner Crash Loop — "Registration Deleted" Error
**Issue:** Runners were spinning up every ~18s and dying with:
```
Failed to create a session. The runner registration has been deleted from the server
```
Hundreds of stale offline runners accumulated on GitHub.

**Resolution:**
- Scaled down controller to stop new runners spawning
- Bulk deleted all offline runners via GitHub CLI:
```bash
gh api repos/salimnextdev/pe-python-app/actions/runners --paginate | \
  jq '.runners[].id' | \
  xargs -I{} gh api -X DELETE repos/salimnextdev/pe-python-app/actions/runners/{}
```
- Disabled ephemeral mode:
```bash
kubectl patch runnerdeployment self-hosted-runners -n actions-runner-system \
  --type=merge -p '{"spec":{"template":{"spec":{"ephemeral":false}}}}'
```

---

## 5. Docker Daemon Not Available in Runner
**Issue:** Runner failed with `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`.

**Resolution:** Disabled Docker in the runner since the `cd` job doesn't need it:
```bash
kubectl patch runnerdeployment self-hosted-runners -n actions-runner-system \
  --type=merge -p '{"spec":{"template":{"spec":{"dockerdWithinRunnerContainer":false,"dockerEnabled":false}}}}'
```

---

## 6. Runner Image Pull Failure (kind DNS)
**Issue:** Runner pod stuck in `ImagePullBackOff` — kubelet couldn't resolve `registry-1.docker.io` using node DNS `192.168.65.254`.

**Resolution:** Fixed DNS on the kind control plane node:
```bash
docker exec kind-control-plane bash -c "echo 'nameserver 8.8.8.8' > /etc/resolv.conf"
```

---

## 7. `runs-on` Typo
**Issue:** Workflow had `runs-on: sefl-hosted` instead of `runs-on: self-hosted`, so no runner matched the job.

**Resolution:** Fixed the typo in `cicd.yaml`.

---

## 8. ArgoCD CLI Download Failure
**Issue:** Multiple problems with downloading argocd CLI in the pipeline:
- Wrong filename (`argocd-linux-amd64` vs `argocd`)
- Malformed URL with a space
- Runner filesystem read-only
- No internet access from runner pod

**Resolution:** Replaced argocd CLI download with direct ArgoCD REST API calls using curl:
```yaml
run: |
  TOKEN=$(curl -ks https://argocd-server.argocd/api/v1/session \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"'${{ secrets.ARGOCD_PASS }}'"}' \
  | grep -o '"token":"[^"]*' | cut -d'"' -f4)
  curl -ks -X POST https://argocd-server.argocd/api/v1/applications/python-app/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```
