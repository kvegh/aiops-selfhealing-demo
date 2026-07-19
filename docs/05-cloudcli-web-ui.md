# 07 — CloudCLI Web UI (optional)

Optional web frontend for Claude Code. The self-healing pipeline works without
it — CloudCLI adds browser access to agent sessions and live streaming of
headless runs during demos.

**Component**: [siteboon/claudecodeui](https://github.com/siteboon/claudecodeui)
(aka CloudCLI), AGPL-3.0, installed via npm.

**How it works**: CloudCLI reads and writes Claude Code's native session state
under `~/.claude`. It does not talk to any Anthropic service itself — it spawns
and observes the local Claude Code integration, which in this setup is
authenticated against **Google Vertex AI**. Sessions started in the terminal
appear in the web UI and vice versa. Headless `claude -p` runs (e.g. triggered
by EDA) stream into the UI live as they execute.

## Architecture

```
Phone/Browser
    │ HTTPS (TLS, htpasswd on UI shell, rate limit on login API)
    ▼
nginx on hypervisor host (CLOUDCLI_WEB_HOSTNAME:443)
    │ HTTP, internal network
    ▼
CloudCLI on TRA VM (TRA_VM_IP:3001, systemd --user service, on-demand)
    │ spawns (Claude Agents SDK)
    ▼
Claude Code ──► Vertex AI (gcloud ADC + env vars)
```

Security posture: CloudCLI runs **on demand only** — the systemd user service
starts at SSH login and stops at last logout (no linger), with a 10-hour
runtime cap. When not demoing, nothing listens on port 3001.

## 1. Installation on the TRA VM (as `aaptra`)

Requires Node.js v22+.

```bash
npm config set prefix ~/.npm-global
echo 'export PATH=$HOME/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

npm install -g @cloudcli-ai/cloudcli
which cloudcli && cloudcli --version
```


## 2. systemd user service

`~/.config/systemd/user/cloudcli.service`:

```ini
[Unit]
Description=CloudCLI web UI for Claude Code
After=network-online.target

[Service]
ExecStart=%h/.npm-global/bin/cloudcli --port 3001
Environment=HOST=TRA_VM_IP
Environment=PATH=%h/.local/bin:%h/.npm-global/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin
Environment=CLAUDE_CODE_USE_VERTEX=1
Environment=ANTHROPIC_VERTEX_PROJECT_ID=GCP_PROJECT_ID
Environment=CLOUD_ML_REGION=global
RuntimeMaxSec=10h
Restart=on-failure
WorkingDirectory=/home/aaptra/claude-wd

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable cloudcli
systemctl --user start cloudcli
```

### Why each non-obvious line exists

- **`HOST=TRA_VM_IP`** — binds to the TRA VM's internal-network IP so nginx on
  the hypervisor host can reach it. Not `127.0.0.1` (unreachable from the hypervisor), not
  `0.0.0.0` (no need to listen wider than the internal net).
- **`Environment=PATH=...`** — systemd user units get a minimal PATH
  (`/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin`) that does **not**
  include `~/.local/bin`, where the `claude` binary lives. Without this line
  CloudCLI cannot find Claude Code and reports it as "not authenticated" —
  a misleading symptom of a missing binary.
- **Vertex env vars** — user units do not source `.bashrc`; anything the
  spawned Claude Code needs must be declared here explicitly. Vertex
  credentials themselves come from gcloud Application Default Credentials
  (`~/.config/gcloud/application_default_credentials.json`), which Claude Code
  discovers via `$HOME` — no `GOOGLE_APPLICATION_CREDENTIALS` needed.
- **`RuntimeMaxSec=10h`** — hard cap: the service stops 10 hours after start
  regardless of session state. A clean stop, not a failure, so
  `Restart=on-failure` does not resurrect it.
- **No linger** (`loginctl show-user aaptra -p Linger` → `no`) — the user
  systemd instance, and with it CloudCLI, is torn down when the last aaptra
  session ends. Combined with `WantedBy=default.target` + `enable`, the
  lifecycle is: starts at first SSH login, survives across parallel sessions,
  dies at last logout.

### Lifecycle gotchas (learned the hard way)

- `daemon-reload` re-reads unit files but does **not** apply changes to a
  running process — `systemctl --user restart cloudcli` is required after any
  `Environment=` change. Verify what the live process actually has:
  `cat /proc/$(systemctl --user show cloudcli -p MainPID --value)/environ | tr '\0' '\n'`
- Stale SSH sessions (frozen connections, tmux) count as sessions and keep the
  instance — and CloudCLI — alive past an apparent "last logout". Check with
  `loginctl list-sessions`, reap with `loginctl terminate-session <ID>`.
- `status=200/CHDIR` on start means `WorkingDirectory=` points at a
  nonexistent path.
- An Ansible `become_user: aaptra` with `become_flags: '--login'` does **not**
  start the service: sudo creates a login *shell*, not a PAM/logind login
  *session*, so `user@.service` is never triggered. EDA-driven headless runs
  therefore don't wake the web UI.

## 3. nginx reverse proxy on the hypervisor host

`/etc/nginx/conf.d/claude.conf`:

```nginx
server {
    server_name CLOUDCLI_WEB_HOSTNAME;
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/AAP_WEB_HOSTNAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/AAP_WEB_HOSTNAME/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # API: CloudCLI's own JWT auth, no basic auth (Authorization header conflict)
    location /api/ {
        auth_basic off;
        proxy_pass http://TRA_VM_IP:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # login endpoint: same, plus rate limit (shared zone with AAP login)
    location = /api/auth/login {
        auth_basic off;
        limit_req zone=aap_login burst=6 nodelay;
        limit_req_status 429;
        proxy_pass http://TRA_VM_IP:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_http_version 1.1;
    }

    # page shell + static assets: htpasswd perimeter
    location / {
        auth_basic "HTPASSWD DEMO REALM";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://TRA_VM_IP:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
server {
    listen 80;
    server_name CLOUDCLI_WEB_HOSTNAME;
    return 301 https://$host$request_uri;
}
```

The rate-limit zone is defined once in `/etc/nginx/conf.d/limits.conf`
(http context, shared with the AAP login endpoint):

```nginx
limit_req_zone $binary_remote_addr zone=aap_login:10m rate=6r/m;
```

### Why the split auth

Basic auth and CloudCLI's JWT **both use the `Authorization` header**. With
htpasswd on `/api/`, the browser keeps injecting `Authorization: Basic ...`
into API calls, clobbering the `Bearer` token — the symptom is a login that
succeeds but immediately bounces back to the login page, with 401s on every
subsequent API request. The fix is layering by path:

| Path                | Guard                                   |
| ------------------- | --------------------------------------- |
| `/` (UI shell)      | nginx htpasswd                          |
| `/api/auth/login`   | CloudCLI JWT login + nginx rate limit   |
| `/api/` (all else)  | CloudCLI JWT (bcrypt-12, single user)   |

Also required on the TRA VM: firewalld allowing 3001 from the internal network.

## 4. First run

1. Browse `https://CLOUDCLI_WEB_HOSTNAME` → htpasswd → CloudCLI setup wizard.
2. Register the **single user** (registration locks after the first account;
   the auth DB lives at `~/.cloudcli/auth.db` — to reset:
   `sqlite3 ~/.cloudcli/auth.db "DELETE FROM users;"` and restart).
3. The wizard's agent check reports *"Claude CLI is not authenticated. Run
   claude /login or configure ANTHROPIC_API_KEY."* — this probe does not
   recognize Vertex environment authentication. **It is cosmetic; skip past
   it.** Sessions work; the agents section is optional.
4. Open a project, send a prompt, and confirm the request appears in the GCP
   project's Vertex AI metrics — that is the proof the web path is
   Vertex-backed end to end.

## 5. Operational notes

- **Session sharing**: terminal and web operate on the same session files.
  Hand over (start in terminal, resume in web or vice versa), but do not
  drive one session from both concurrently.
- **Headless runs stream live**: `claude -p` invocations — including
  EDA-triggered ones running as `aaptra` in the same working directory —
  appear in the UI in real time. CloudCLI does not distinguish who spawned
  the process; same user + same host + same project directory is all that
  matters.
- **On-demand operation**: `systemctl --user stop cloudcli` when done, or let
  last-logout / `RuntimeMaxSec` catch it. To invert the default (manual start
  instead of start-at-login): `systemctl --user disable cloudcli` and start
  it as part of the demo ritual.
