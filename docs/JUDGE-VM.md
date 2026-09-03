# Judging on a dedicated VM

How the production deployment splits CodeArena across two machines: a **host**
that serves the web tier, and a **judge VM** that is the only place contestant
code ever executes.

This is the topology behind `SCORING_MODE=docker` + Redis/RQ described in
[DEPLOY.md](DEPLOY.md). Read that first for the scoring model itself (time
limits, sandbox flags, capacity knobs); this document only covers the split.

All addresses below are the libvirt defaults (`virbr0`, `192.168.122.0/24`) and
a `192.168.1.0/24` home LAN. Substitute your own.

## Why a VM and not just a container

The RQ worker mounts `/var/run/docker.sock` - it has to, because that is how it
launches one throwaway sandbox per submission. **A Docker socket mount is
root-equivalent on whatever holds it**: a process that can talk to the daemon
can start a privileged container, bind-mount `/`, and own the machine.

So the question is never "is the worker safe" but "what does the worker's
compromise cost". Three arrangements, in increasing order of blast radius
containment:

| Where the worker runs | Cost of a worker compromise |
| --- | --- |
| In-process in the backend (`REDIS_URL` unset) | The web container, which holds `SECRET_KEY` and SMTP credentials. Admin-token forgery, mail relay. |
| Its own container on the host, with `docker.sock` | The host: every other container, the uploads, the DB volume, the LAN. |
| **Its own VM (this document)** | The VM, plus whatever its database role reaches. No host, no LAN, no app secret - but see the warning below: the role is the part that has to be narrowed by hand. |

The last one is what the topology below buys. Two properties make it worth the
extra moving parts:

- **The VM holds no application secret.** Its `.env` has exactly two lines,
  `DATABASE_URL` and `REDIS_URL`. No `SECRET_KEY` (so no forged admin JWT), no
  SMTP credentials (so no mail relay), no `METRICS_TOKEN`.
- **Its database identity is not the owner.** The workers connect as `judge`,
  which has no `CREATE` on `public`: it cannot add a table, drop one, read
  `pg_authid`, or migrate the schema out from under the app.

> **The VM split alone does not protect the application.** Moving judging into
> a VM contains the *machine*; the database role is what decides whether it
> also contains the *app*. A `judge` role granted
> `SELECT/INSERT/UPDATE/DELETE` on every table - the state a naive
> `GRANT ... ON ALL TABLES` leaves you in - can read every `password_hash` and
> `totp_secret`, flip `users.is_admin`, and rewrite any password hash. Since
> `backend/auth.py` reads `is_admin` from the row on each request, that is real
> admin access, reached without ever touching the host. Grant the eleven tables
> below and nothing else.

Defence in depth, not a single wall: the contestant's code is already inside a
`--network=none`, read-only, non-root, pid-limited container *inside* the VM.
The VM catches a sandbox escape, the narrowed DB role catches a VM escape, and
the network rules keep either off the LAN.

None of this addresses application-level vulnerabilities - authorization bugs,
upload/archive handling, token handling. The backend still runs on the host
with `SECRET_KEY`, SMTP credentials and the owning DB role, so a serious bug on
those paths remains a host-level problem. Judging isolation and app security
are separate exercises.

## Topology

```
 Internet ──443──▶ nginx (host)
                     │
                     ├──▶ frontend  127.0.0.1:2027   (React, static)
                     └──▶ backend   :8000            (FastAPI, in codearena_default)
                                      │
                          enqueue     │  RQ jobs: "scoring", "lesson-runs"
                                      ▼
                              redis  ─┬─ 192.168.122.1:6379  ◀──────────┐
                              postgres┴─ 192.168.122.1:5432  ◀────────┐ │
                                                                      │ │
 ══════════════════ host ══════════════════════ virbr0 ═══════════════╪═╪══
                                                                      │ │
                    judge01  (libvirt VM, 192.168.122.68)             │ │
                      ├── codearena-judge-worker-{0,1,2}──────────────┘ │
                      │     drain "scoring", cores 0-2  judge role ─────┘
                      ├── codearena-judge-learn-worker
                      │     drains "lesson-runs", core 3
                      └── per-submission sandbox containers
                            --network=none, --read-only, non-root,
                            --pids-limit 128, --memory, --cpus
```

The two Redis/Postgres ports are deliberately published on `192.168.122.1` -
the host's address *on the virtual bridge* - and nowhere else. The VM can reach
them; the LAN cannot.

| Component | Address | Notes |
| --- | --- | --- |
| Backend | container `:8000` | no host port; nginx reaches it through the frontend vhost |
| Frontend | `127.0.0.1:2027` | loopback only, nginx terminates TLS |
| Postgres | `192.168.122.1:5432` | bridge only. `pg_hba`: `scram-sha-256` for every non-local host |
| Redis | `192.168.122.1:6379` | bridge only, `requirepass` set (the password is in `REDIS_URL`) |
| judge01 | `192.168.122.68` | DHCP lease from libvirt's `default` network |

## Host side

The host runs `docker compose` from `/opt/codearena` with **both worker
services scaled to zero** - that is the whole mechanism that keeps judging off
the host. In `.env`:

```dotenv
SCORING_MODE=docker
SCORING_WORKER_REPLICAS=0     # the "scoring" worker runs in the VM instead
LEARN_WORKER_REPLICAS=0       # idem for "lesson-runs"
REDIS_URL=redis://:<password>@redis:6379/0
```

`deploy.replicas: 0` is honoured by plain `docker compose up -d`, so the
workers stay down across restarts without anyone having to remember a flag.

What that leaves running on the host: `backend`, `frontend`, `postgres`,
`redis` (plus `caddy` under the `edge-caddy` profile, which is present but
bypassed here - the host's nginx is the edge).

> **The one-line regression to watch for.** If `REDIS_URL` is ever unset on the
> backend, it silently falls back to an in-process thread pool and judges
> *inside the web container* - which then needs `docker.sock` and the
> `/judge-work` mount back. The compose file carries that warning at the
> `REDIS_URL` line; keep it there. With `SCORING_MODE=docker` and no reachable
> daemon, ICPC judging fails closed rather than running unsandboxed, so the
> failure is loud, but the fallback path is the thing to grep for after any
> `.env` edit.

Publishing Postgres and Redis on the bridge address, in `docker-compose.yml`:

```yaml
  postgres:
    ports:
      - "192.168.122.1:5432:5432"
  redis:
    ports:
      - "192.168.122.1:6379:6379"
    command:
      - redis-server
      # ... persistence flags ...
      # Mandatory here: publishing Redis to the judge VM means an escaped
      # sandbox could otherwise drive the queue unauthenticated.
      - --requirepass
      - ${REDIS_PASSWORD:?REDIS_PASSWORD is required - redis is exposed to the judge VM}
```

> **These three lines are deployment-specific and are NOT in the
> repository's `docker-compose.yml`.** The checked-in file targets a
> single-host deployment where Postgres and Redis stay on the internal
> Docker network and need neither a published port nor a password.
>
> That divergence is a live trap: copying the repo's compose over the
> deployed one silently removes the two publishes and the Redis password.
> Nothing breaks until the next `docker compose up -d`, which recreates
> the containers from the new definition - and then the judge VM loses
> both its database and its queue, while Redis comes back with no
> password at all. Diff before you sync, and keep a backup of the
> deployed file.

### The `judge` database role

Created once, on the host, as the owner. **Grant tables one by one, never
`ON ALL TABLES`** - the workers touch eleven tables
(`scoring_jobs.py`, `scoreboard_cache.py`, `icpc_scoreboard_cache.py`,
`lesson_run_jobs.py`) and have no business reading `users`, `teams`,
`contest_participants`, the audit log or the mail outbox:

```sql
CREATE ROLE judge LOGIN PASSWORD '<judge-password>';
GRANT USAGE ON SCHEMA public TO judge;
REVOKE CREATE ON SCHEMA public FROM judge;

-- read-only: problem statements, tests, languages, runtime config
GRANT SELECT ON problems, testcases, languages, instances,
                lesson_exercises TO judge;

-- contests is read-only too. Both scoreboard caches serialise their
-- writers per contest with a transaction-scoped advisory lock
-- (backend/db_locks.py), which needs no table privilege. Before
-- 2026-09-03 that was a SELECT ... FOR UPDATE on the contest row, and
-- Postgres demands UPDATE for any row-lock clause: a role created from
-- that version of this page holds an UPDATE it no longer needs.
GRANT SELECT ON contests TO judge;
REVOKE UPDATE ON contests FROM judge;

-- the verdict it is there to record
GRANT SELECT, UPDATE         ON submissions            TO judge;
GRANT SELECT, INSERT, UPDATE ON judgings, judging_runs TO judge;
GRANT USAGE, SELECT ON SEQUENCE judgings_id_seq, judging_runs_id_seq TO judge;

-- the materialised scoreboards, rebuilt by the same job that records the
-- verdict (scoring_jobs -> update_entry_for_submission / update_icpc_entry).
-- DELETE included: both caches drop stale rows rather than update in place.
GRANT SELECT, INSERT, UPDATE, DELETE
      ON scoreboard_entries, icpc_scoreboard_entries TO judge;
GRANT USAGE, SELECT ON SEQUENCE scoreboard_entries_id_seq,
                                icpc_scoreboard_entries_id_seq TO judge;
```

Deliberately **no** `ALTER DEFAULT PRIVILEGES`: a blanket default would hand
the role every table a future migration adds. The cost is that a migration
introducing a table on the judging path needs its `GRANT` added here and
replayed - otherwise the worker fails on the new table. That is the right way
round: a loud failure after a migration beats a silent grant on `users`.

Verify what it actually has - the last two must both be refused:

```bash
docker exec codearena-postgres psql -U codearena -d codearena -c "\du judge"
docker exec codearena-postgres psql -U codearena -d codearena -tAc \
  "SELECT has_schema_privilege('judge','public','CREATE');"   # must be false

# these must fail with "permission denied for table users"
docker exec codearena-postgres psql -U judge -d codearena -tAc \
  "SELECT password_hash FROM users LIMIT 1;"
docker exec codearena-postgres psql -U judge -d codearena -tAc \
  "BEGIN; UPDATE users SET is_admin=true; ROLLBACK;"
```

Refusals are only half the check: a role that is too *narrow* fails at the
first submission, not at creation time. Ask Postgres which of the grants
above are missing - the result must be empty:

```bash
docker exec codearena-postgres psql -U codearena -d codearena -c "
SELECT t, p FROM (VALUES
  ('contests','SELECT'),
  ('submissions','SELECT'),('submissions','UPDATE'),
  ('judgings','SELECT'),('judgings','INSERT'),('judgings','UPDATE'),
  ('judging_runs','SELECT'),('judging_runs','INSERT'),('judging_runs','UPDATE'),
  ('scoreboard_entries','SELECT'),('scoreboard_entries','INSERT'),
  ('scoreboard_entries','UPDATE'),('scoreboard_entries','DELETE'),
  ('icpc_scoreboard_entries','SELECT'),('icpc_scoreboard_entries','INSERT'),
  ('icpc_scoreboard_entries','UPDATE'),('icpc_scoreboard_entries','DELETE'),
  ('problems','SELECT'),('testcases','SELECT'),('languages','SELECT'),
  ('instances','SELECT'),('lesson_exercises','SELECT')
) AS v(t,p) WHERE NOT has_table_privilege('judge', t, p)
UNION ALL
SELECT s, 'USAGE' FROM (VALUES
  ('judgings_id_seq'),('judging_runs_id_seq'),
  ('scoreboard_entries_id_seq'),('icpc_scoreboard_entries_id_seq')
) AS w(s) WHERE NOT has_sequence_privilege('judge', s, 'USAGE');"
```

Replay it after every migration and every edit of this page. Then submit one
solution to a live problem and confirm the scoreboard moves - only an
end-to-end judging proves the write path, and it exercises `submissions`,
`judgings`, `judging_runs` and both scoreboard caches in one go.

What a missing grant looks like, so it is recognised next time: the verdict
itself is recorded (the tables the worker writes first are granted), then the
scoreboard cache write is refused and the submission ends up in `error`
carrying `Judge error: ... permission denied for table ...`, while the
scoreboard never moves. This happened on 2026-09-03: the role had been created
without the grants on the two `*_scoreboard_entries` tables and their
sequences, and every judging for two days recorded its verdict and lost its
scoreboard cell. Worker logs are on the VM; the Postgres container log on the
host has the refused statement (`docker compose logs postgres | grep ERROR`).

## VM side

| | |
| --- | --- |
| Name / autostart | `judge01`, `virsh autostart` enabled |
| Guest | Ubuntu 24.04 LTS cloud image, kernel 6.8 |
| Resources | 4 vCPU, 8 GiB RAM, 60 GB qcow2 (`/mnt/ssd/vm/judge01.qcow2`) |
| Network | one virtio NIC on libvirt's `default` network (NAT via `virbr0`) |
| Confinement | AppArmor, `enforcing`, per-domain profile |
| Runtime | Docker Engine + Compose v2, `judge` user, no `ufw` inside |
| Scratch | `/judge-work`, bind-mounted into every worker |

Sizing rationale: one sandbox gets a whole core (`SCORING_CPUS=1.0`) because
verdicts are decided on CPU time but killed on the wall clock - throttling
below a core halves the work a submission can do before the wall limit fires,
and doubles every compile. So the judge count is bounded by cores, not by RAM:
4 vCPU means three contest judges plus the Learn worker, one core each.

**Scale by physical cores, not vCPU.** Handing the VM more vCPU than the host
has physical cores buys nothing here: two vCPU backed by SMT siblings of one
physical core inflate each other's wall clock exactly the way two containers
sharing a core do, and the hard limit is wall-based. Add physical cores to the
host first, then vCPU, then judges.

### `/opt/judge/docker-compose.yml` (in the VM)

Four workers off one image, differing only in which queue they drain and which
core their sandboxes are pinned to. Three drain `scoring`; the fourth drains
`lesson-runs`, so a student clicking "run" on a Learn exercise never waits
behind a multi-minute ICPC judging.

**Declare them as separate services, never `deploy.replicas`.** Every replica
inherits the same environment, therefore the same `SCORING_CPUSET`, so N
replicas would pile N sandboxes onto one core - and since a verdict is decided
on CPU time but killed on the wall clock, that manufactures false TLEs. One
core per judge, spelled out:

```yaml
x-judge-worker: &judge-worker
  image: 16flavio/codearena-backend:latest
  env_file: .env
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - /judge-work:/judge-work
  command: [ "python", "-m", "backend.worker" ]
  restart: unless-stopped

x-judge-env: &judge-env
  SCORING_MODE: docker
  SCORING_ICPC_IMAGE: codearena-icpc-sandbox:latest
  SCORING_IMAGE: 16flavio/codearena-scoring:latest
  SCORING_WORKDIR: /judge-work
  SCORING_MEMORY_MB: "256"
  SCORING_CPUS: "1.0"
  SCORING_TIMELIMIT_OVERSHOOT: 1s|10%
  SCORING_TIMEOUT_SECONDS: "30"
  DB_POOL_SIZE: "2"
  DB_MAX_OVERFLOW: "3"

services:
  worker-0:
    <<: *judge-worker
    container_name: codearena-judge-worker-0
    environment:
      <<: *judge-env
      WORKER_QUEUES: scoring
      SCORING_CPUSET: "0"

  # worker-1 and worker-2 are identical, with SCORING_CPUSET "1" and "2"

  learn-worker:
    <<: *judge-worker
    container_name: codearena-judge-learn-worker
    environment:
      <<: *judge-env
      WORKER_QUEUES: lesson-runs
      SCORING_CPUSET: "3"
```

Check that the fleet actually registered rather than trusting `docker ps` - a
worker whose credentials are wrong starts, stays up, and drains nothing:

```bash
docker exec codearena-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning \
  smembers rq:workers:scoring        # one entry per live judge
```

And the entire `.env` next to it - two lines, `chmod 600`:

```dotenv
REDIS_URL=redis://:<redis-password>@192.168.122.1:6379/0
DATABASE_URL=postgresql+psycopg2://judge:<judge-password>@192.168.122.1:5432/codearena
```

## Network isolation

The VM runs code written by strangers, so it must reach the internet (package
installs during image builds) and the host's two bridge services - and nothing
else on the home network. Docker's own rules make this less obvious than it
looks: the daemon inserts DNAT in `PREROUTING`, *before* filtering, and never
consults UFW. The `DOCKER-USER` chain is the supported hook, but Docker
recreates it on every daemon restart, so the rules live in a oneshot unit
(`/etc/systemd/system/docker-lan-isolation.service`, `PartOf=docker.service`)
that re-applies them:

```sh
LAN_NET=192.168.1.0/24      # your home network
HOST_IP=192.168.1.63        # the host's LAN address
DOCKER_NET=172.16.0.0/12
VM_NET=192.168.122.0/24

# containers -> LAN (inserted in reverse; ESTABLISHED must end up first)
iptables -I DOCKER-USER -s "$DOCKER_NET" -d "$LAN_NET" -j DROP
iptables -I DOCKER-USER -s "$DOCKER_NET" -m conntrack --ctorigdst "$HOST_IP" -j DROP
iptables -I DOCKER-USER -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# VM -> LAN
iptables -I FORWARD 1 -s "$VM_NET" -d "$LAN_NET" -j DROP
iptables -I FORWARD 1 -s "$VM_NET" -m conntrack --ctorigdst "$HOST_IP" -j DROP
```

`--ctorigdst` matches the destination *before* DNAT, which is what catches
traffic aimed at the host's published ports; a plain `-d` would see the
already-translated container address and miss.

Verify from inside the VM - every LAN target must fail, the two bridge services
must answer:

```bash
ssh judge@192.168.122.68 'for t in 192.168.1.1:80 192.168.1.63:443 192.168.122.1:5432; do
  h=${t%:*}; p=${t#*:}
  timeout 3 bash -c "exec 3<>/dev/tcp/$h/$p" 2>/dev/null && echo "$t open" || echo "$t blocked"
done'
```

### Known gap

**These rules match the host by its LAN address only.** The host is also
reachable on its bridge addresses - `192.168.122.1` from the VM,
`172.x.0.1` from any container - and traffic to those goes through `INPUT`,
not `FORWARD`/`DOCKER-USER`. Every port the host binds to `0.0.0.0` is
therefore reachable from the VM and from containers, including any TCP-stream
reverse proxy the host happens to run. If the host proxies a LAN service (an
RDP stream, a management UI), that proxy is a way around the isolation above.

Two ways to close it, either is enough:

- bind host-level proxies to the LAN address (`listen 192.168.1.63:3389`)
  instead of `0.0.0.0`, or
- filter on the bridge interfaces in `INPUT`:
  `iptables -I INPUT -i virbr0 -d 192.168.122.1 -p tcp --dport <port> -j DROP`
  (and `-i br-+` for the Docker bridges), allowing only 5432 and 6379.

## Building it from scratch

Reconstructed from the running deployment - the flow is right, adjust paths and
sizes to taste.

**1. Cloud image + cloud-init seed** (on the host):

```bash
mkdir -p /mnt/ssd/vm/{images,cloudinit,worker}
curl -Lo /mnt/ssd/vm/images/ubuntu-24.04-cloud.img \
  https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

ssh-keygen -t ed25519 -f /root/.ssh/vm-judge -N '' -C 'host->judge01'

cat > /mnt/ssd/vm/cloudinit/user-data <<EOF
#cloud-config
hostname: judge01
manage_etc_hosts: true
users:
  - name: judge
    groups: [sudo]
    sudo: "ALL=(ALL) NOPASSWD:ALL"
    shell: /bin/bash
    lock_passwd: true
    ssh_authorized_keys:
      - $(cat /root/.ssh/vm-judge.pub)
ssh_pwauth: false
package_update: true
packages: [ca-certificates, curl]
EOF

printf 'instance-id: judge01\nlocal-hostname: judge01\n' \
  > /mnt/ssd/vm/cloudinit/meta-data

cloud-localds /mnt/ssd/vm/cloudinit/seed.iso \
  /mnt/ssd/vm/cloudinit/user-data /mnt/ssd/vm/cloudinit/meta-data
```

**2. Create the domain:**

```bash
qemu-img convert -O qcow2 /mnt/ssd/vm/images/ubuntu-24.04-cloud.img \
  /mnt/ssd/vm/judge01.qcow2
qemu-img resize /mnt/ssd/vm/judge01.qcow2 60G

virt-install --name judge01 --memory 8192 --vcpus 4 \
  --machine q35 --osinfo ubuntu24.04 --import \
  --disk /mnt/ssd/vm/judge01.qcow2,bus=virtio \
  --disk /mnt/ssd/vm/cloudinit/seed.iso,device=cdrom \
  --network network=default,model=virtio \
  --graphics none --noautoconsole
virsh autostart judge01
```

**3. Docker inside the VM:**

```bash
ssh -i /root/.ssh/vm-judge judge@<vm-ip> \
  'curl -fsSL https://get.docker.com | sudo sh && sudo mkdir -p /judge-work'
```

**4. Ship the images.** Two of the three are on Docker Hub; the ICPC sandbox is
built locally from `Dockerfile.icpc-sandbox` and has to be piped over:

```bash
ssh -i /root/.ssh/vm-judge judge@<vm-ip> \
  'sudo docker pull 16flavio/codearena-backend:latest &&
   sudo docker pull 16flavio/codearena-scoring:latest'

docker save codearena-icpc-sandbox:latest \
  | ssh -i /root/.ssh/vm-judge judge@<vm-ip> 'sudo docker load'
```

**5. Host-side prerequisites:** create the `judge` role (above), move the
Postgres/Redis publishes to `192.168.122.1`, set both `*_WORKER_REPLICAS=0`,
then `docker compose up -d` to drop the host workers.

**6. Start the workers:** copy `docker-compose.yml` and `.env` into
`/opt/judge` in the VM, then `sudo docker compose up -d`.

## Day-2 operations

```bash
# Deploy a new backend build to the judges (after pushing the image)
ssh judge@<vm-ip> 'cd /opt/judge && sudo docker compose pull && sudo docker compose up -d'

# Are all four workers alive and draining?
ssh judge@<vm-ip> 'sudo docker compose -f /opt/judge/docker-compose.yml ps'
ssh judge@<vm-ip> 'sudo docker logs --tail 20 codearena-judge-worker-0'

# Queue depth, from the host
docker exec codearena-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning \
  llen rq:queue:scoring
docker exec codearena-redis redis-cli -a "$REDIS_PASSWORD" --no-auth-warning \
  smembers rq:workers:scoring     # one entry per live worker

# More judging capacity, in this order:
#   1. physical cores on the host   (vCPU beyond them buys nothing - see above)
#   2. virsh setvcpus judge01 <n> --config   (takes effect on next boot)
#   3. one more worker-N service in /opt/judge/docker-compose.yml,
#      with its own SCORING_CPUSET - never deploy.replicas
```

**When the VM is down**, submissions do not fail - they pile up in the
`scoring` list in Redis and drain when a worker comes back. The user-visible
symptom is a stuck "judging" state, plus `503` on the synchronous paths
(Learn "run", admin rescore, "test this scoring script") after
`LESSON_RUN_WAIT_SECONDS`. Redis persistence governs whether a queued job
survives a host reboot; treat the queue as best-effort and rescore if in doubt.

**After a host reboot**, check ordering: the isolation unit is
`PartOf=docker.service` and re-applies on every daemon restart, but confirm
with `iptables -S DOCKER-USER` that the `ESTABLISHED,RELATED` ACCEPT sits
first - if it drifts below the DROPs, replies to LAN-initiated connections get
dropped and published services look half-broken.

## File map

| Path | What |
| --- | --- |
| `/opt/codearena/` (host) | compose + `.env` for the web tier |
| `/usr/local/sbin/docker-lan-isolation.sh` (host) | the isolation rules |
| `/etc/systemd/system/docker-lan-isolation.service` (host) | re-applies them on daemon restart |
| `/mnt/ssd/vm/judge01.qcow2` (host) | VM disk |
| `/mnt/ssd/vm/cloudinit/` (host) | `user-data`, `meta-data`, `seed.iso` |
| `/mnt/ssd/vm/worker/` (host) | master copy of the VM's compose + `.env` |
| `/root/.ssh/vm-judge` (host) | key for `judge@judge01`; the VM holds no key back |
| `/opt/judge/` (VM) | running compose + `.env` |
| `/judge-work` (VM) | per-submission scratch, bind-mounted into the workers |
