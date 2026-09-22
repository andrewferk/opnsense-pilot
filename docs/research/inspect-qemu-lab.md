# How should Inspect AI drive a local QEMU lab on the Mac?

Research for [issue #24](https://github.com/andrewferk/opnsense-pilot/issues/24). Researched 2026-09-22. Reading research only: nothing was booted; the probe VM was left stopped and its scripts were read, not run.

Pinned sources:

- **Inspect AI** tag [`0.3.266`](https://github.com/UKGovernmentBEIS/inspect_ai/tree/0.3.266) = commit `ec4dfc6953784dc45b79de3147530c89868c6e26` (PyPI `inspect-ai` 0.3.266, uploaded 2026-09-19, the latest at research time). All Inspect links below point at that tag; the rendered docs at <https://inspect.aisi.org.uk/> track `main`, so the `.qmd` sources at the tag are the citable copies.
- **inspect_proxmox_sandbox** `main` at commit [`53e2646c9fe63d0d9f0c8fada806824475389b01`](https://github.com/UKGovernmentBEIS/inspect_proxmox_sandbox/tree/53e2646c9fe63d0d9f0c8fada806824475389b01) (pushed 2026-09-22). PyPI `inspect-proxmox-sandbox` is stale at 0.0.1 (2025-04-01); Inspect's registry points at the git URL.
- **QEMU** tag `v11.1.1` source and docs (matches the installed Homebrew `qemu-system-x86_64` / `qemu-system-aarch64` 11.1.1; `-netdev help` on this machine lists `socket stream dgram hubport tap user vde bridge vhost-user vmnet-host vmnet-shared vmnet-bridged`). Homebrew's `qemu` formula depends on `vde`; `vde` 2.3.3 is installed and `vde_switch` is at `/opt/homebrew/bin/vde_switch`. Host memory: `hw.memsize` = 25769803776 (24 GiB).
- Probe VM facts (measured, from the resolution of [#12](https://github.com/andrewferk/opnsense-pilot/issues/12)): one `qemu-system-x86_64` per VM under TCG, `-m 3072`, about 1.9 GB resident idle, boot-to-API 48 s, `savevm`/`loadvm` 0.6 s / 0.7 s with a 1.18 GiB state, API correct after `loadvm`, cold reset by replacing the qcow2 overlay.

## Recommendation

**Extension point: a custom `SandboxEnvironment` provider (`@sandboxenv(name="qemu")`) that is a thin adapter over a plain-Python lab controller.** The lab controller (QEMU process management, QMP, overlays, snapshots, sockets) is an ordinary library with no Inspect imports, so pytest and a CLI can drive the same lab. The provider's `sample_init` / `sample_cleanup` / `task_init` / `task_cleanup` / `cli_cleanup` map one-to-one onto the lifecycle the lab needs, and only this extension point gives us `max_sandboxes` throttling, the `interrupted` flag with cancellation-shielded cleanup, `--no-sandbox-cleanup`, `inspect sandbox cleanup qemu`, a fresh environment per retry attempt, and `sandbox("firewall")` access from solvers, scorers and `Task.cleanup`. The firewall VM is a *named* environment (a target), not the default execution sandbox; the Proxmox provider models exactly this with `is_sandbox=False` "router appliance" VMs that have no guest agent but are still returned to Inspect and can gate other VMs via `depends_on`.

**Reset: warm `loadvm` per sample, cold overlay replacement as the fallback and the `cli_cleanup` path.** `sample_init` acquires a VM slot from a small pool (pool size = `default_concurrency()`), restores the scenario's baseline snapshot over QMP (`snapshot-load` job or HMP `loadvm` via `human-monitor-command`), polls the API until it answers, and returns the handles. `sample_cleanup` either restores again or marks the slot dirty; on `interrupted=True` it does the minimum and defers to `task_cleanup`. Inspect places no constraint on what `sample_init` does, and its own checkpoint "snapshots" are file-level restic/tar captures for *resume*, unrelated to VM state, so there is no conflict. What only a prototype can settle is the network side of `loadvm` (host TCP connections and peer VMs see a guest that jumped back in time).

**Networking: keep slirp (`-netdev user`, `restrict=on`, `hostfwd`) for the management NIC; build test segments from unprivileged socket backends.** Two-member segments (firewall LAN to one client): `-netdev dgram` over Unix datagram sockets, or `-netdev stream` over a Unix stream socket. Segments with more than two members: a per-sample `vde_switch` (userspace, no root; QEMU here is built with VDE), or, to be tested first because it needs no extra process, an in-process hub (`-netdev hubport,hubid=N,netdev=<socket netdev>`) inside the firewall's QEMU fanning its LAN NIC out to one point-to-point socket per client. Avoid UDP multicast (`socket,mcast` / `dgram` to a multicast address): it is a real IP multicast group on a host interface, so guest frames can leave the machine, and its behaviour on macOS is unverified. Native arm64 clients (`qemu-system-aarch64 -accel hvf`) join the same sockets because the socket backends carry Ethernet frames regardless of guest architecture. Budget: one firewall slot at about 4 GB and three or four small clients at about 0.5 GB each fit in roughly 6 GB; two firewall slots (`max_sandboxes=2`) in roughly 10 GB, leaving the rest of the 24 GB for macOS, PostgreSQL/Docker and Inspect itself.

## 1. Extension points: what Inspect offers and what each costs

### 1.1 The `SandboxEnvironment` contract (verified in source at `0.3.266`)

Base class: [`src/inspect_ai/util/_sandbox/environment.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/util/_sandbox/environment.py). Docstring: "Environment for executing arbitrary code from tools. Sandbox environments provide both an execution environment as well as a per-sample filesystem context to copy samples files into and resolve relative paths to."

Abstract instance methods (must be implemented):

```python
async def exec(self, cmd: list[str], input: str | bytes | None = None, cwd: str | None = None,
               env: dict[str, str] | None = None, user: str | None = None, timeout: int | None = None,
               timeout_retry: bool = True, concurrency: bool = True) -> ExecResult[str]
async def write_file(self, file: str, contents: str | bytes) -> None
async def read_file(self, file: str, text: bool = True) -> str | bytes
```

Optional instance methods: `connection(self, *, user=None) -> SandboxConnection` (raises `NotImplementedError` by default; used for `inspect view` connection info), `exec_remote(...)` (streaming exec; **injects Inspect's sandbox-tools binaries into the environment on first use**, via `sandbox_with_injected_tools`), `as_type(sandbox_cls)` (typed downcast, raises `TypeError`), `default_polling_interval()`.

`SandboxUnavailableError(RuntimeError)`: "Raised when a provider cannot initiate a sandbox exec request. ... Tool calls turn this into a tool error of type `sandbox_unavailable`, leaving the sample running. Other callers (scorers, solvers, setup code) receive it as an ordinary exception."

Lifecycle class methods (all `async` except where noted; signatures verbatim):

```python
@classmethod
def default_concurrency(cls) -> int | None            # "Default max_sandboxes for this provider (None means no maximum)"
@classmethod
async def task_init(cls, task_name: str, config: SandboxEnvironmentConfigType | None) -> None
@classmethod
async def task_init_environment(cls, config, metadata: dict[str, str]) -> dict[str, str]
@classmethod
async def sample_init(cls, task_name: str, config: SandboxEnvironmentConfigType | None,
                      metadata: dict[str, str]) -> dict[str, "SandboxEnvironment"]
@classmethod
@abc.abstractmethod
async def sample_cleanup(cls, task_name: str, config: SandboxEnvironmentConfigType | None,
                         environments: dict[str, "SandboxEnvironment"], interrupted: bool) -> None
@classmethod
async def task_cleanup(cls, task_name: str, config: SandboxEnvironmentConfigType | None, cleanup: bool) -> None
@classmethod
async def cli_cleanup(cls, id: str | None) -> None
@classmethod
def config_files(cls) -> list[str]
@classmethod
def config_deserialize(cls, config: dict[str, Any]) -> BaseModel   # raises NotImplementedError unless overridden
```

`SandboxEnvironmentConfigType = BaseModel | str`. A custom config model "must be hashable (i.e. `frozen=True`)" ([`extensions-sandboxes.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/extensions-sandboxes.qmd), "Sandbox Usage"). `sample_init`'s docstring: "The environment which represents the default environment (resolved by `sandbox("default")` or `sandbox()`) must be the first key/value pair in the dictionary." `task_cleanup`'s `cleanup` argument is "False if `--no-sandbox-cleanup` was specified". `sample_cleanup`'s `interrupted`: "Was the task interrupted by an error or cancellation".

The docs' lifecycle table ([`extensions-sandboxes.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/extensions-sandboxes.qmd)): `task_init()` "Called once for each unique sandbox environment config before executing the tasks in an `eval()` run" for "Expensive initialisation operations (e.g. pulling or building images)"; `sample_init()` "Called at the beginning of each `Sample`"; `sample_cleanup()` "Called at the end of each `Sample`"; `task_cleanup()` "Called once for each unique sandbox environment config after executing the tasks" as "Last chance handler for any resources not yet cleaned up"; `cli_cleanup()` "Called via `inspect sandbox cleanup`". The same page: "To implement `task_cleanup()` properly, you'll likely need to track running environments using a per-coroutine `ContextVar`" and the CLI form is `inspect sandbox cleanup <type> [<id>]`.

Registration: `@sandboxenv(name="...")` in [`registry.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/util/_sandbox/registry.py) (the decorator also accepts a zero-arg function returning the class, for lazy imports), discovered through a `[project.entry-points.inspect_ai]` entry point ([`extensions-sandboxes.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/extensions-sandboxes.qmd), "Sandbox Registration"). Lookup is by unqualified name; unknown names raise `ValueError` with an install hint for the known third-party packages (`k8s`, `ec2`, `proxmox`, `modal`, `daytona`).

Usage from tasks: `Task(sandbox="qemu")`, `Task(sandbox=("qemu", "lab.yaml"))`, or `Task(sandbox=SandboxEnvironmentSpec("qemu", QemuLabConfig(...)))`; per-sample `Sample(sandbox=...)` overrides ([`sandboxing.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/sandboxing.qmd), "Per Sample Setup": "each sample gets its own sandbox *instance*, even if the sandbox is defined at Task level"). Inside solvers, tools, scorers: `sandbox()` (default), `sandbox("firewall")` (named), `sandbox_default("firewall")` context manager, `sandbox().as_type(QemuVm)` for provider-specific methods ([`context.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/util/_sandbox/context.py)). Every `exec`/`read_file`/`write_file` goes through `SandboxEnvironmentProxy`, which records `SandboxEvent`s into the transcript ([`context.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/util/_sandbox/context.py) `init_sandbox_environments_sample`).

### 1.2 What the per-sample driver actually does (verified in [`_eval/task/sandbox.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/_eval/task/sandbox.py) and [`context.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/util/_sandbox/context.py))

`sandboxenv_context(task_name, sandbox, max_sandboxes, cleanup, sample)`:

1. Resolves the provider class and calls `ensure_sandbox_limiter`: the limit is `max_sandboxes` from the eval config, else the provider's `default_concurrency()`; if a limit exists a process-global, resizable semaphore named `sandboxes/<type>` is created.
2. If a limit is in effect, sleeps `random()` seconds so parallel tasks get a fair shot, then enters `concurrency(sandbox.type, max_sandboxes, f"sandboxes/{sandbox.type}", resizable=True)`. **The semaphore is held for the whole sample**, so `max_sandboxes` is the number of samples concurrently holding lab resources (docs: "when `max_sandboxes` is applied this effectively creates a global `max_samples` limit that is equal to the `max_sandboxes`", [`_container_limits.md`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/_container_limits.md)).
3. Reads `Sample.files` and `Sample.setup`, adds `__sample_id__` to a copy of `Sample.metadata`, and calls `init_sandbox_environments_sample`, which calls `sample_init(task_name, config, metadata)`, validates that at least one environment came back, wraps each in `SandboxEnvironmentProxy`, sets the context vars, copies files (`"name:path"` keys target a named environment), and runs the setup script in the default environment with `INSPECT_SANDBOX_SETUP_TIMEOUT` (default `SANDBOX_SETUP_TIMEOUT = 300` s, [`constants.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/_util/constants.py)). **If files or setup fail, `sample_cleanup(..., interrupted=True)` is called immediately and the exception re-raised.**
4. `yield` (the sample runs: solvers, scoring, `Task.cleanup`).
5. `except anyio.get_cancelled_exc_class(): interrupted = True; raise`, then `finally:` if environments exist and `cleanup` is true, `with anyio.CancelScope(shield=interrupted): await cleanup_sandbox_environments_sample(...)` which calls `sample_cleanup(task_name, config, environments, interrupted)`.

So `interrupted=True` reaches `sample_cleanup` in exactly two cases: a cancellation propagated through the sample (Ctrl+C, eval-level cancel, an operator cancel), or a failure while copying files / running the setup script. An ordinary sample error (exception in a solver or scorer) is handled inside the `yield` and reaches `sample_cleanup` with `interrupted=False`. In [`_eval/task/run.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/_eval/task/run.py) the context manager's `__aexit__` is additionally wrapped with `aexit_shielded_when(..., lambda: cancelled_error is not None)` so that teardown "runs shielded whenever the sample's own cancel was caught upstream". `sample_init` itself has **no framework timeout**; the provider must enforce its own boot deadline (the Proxmox provider has a `deadline.py` for this).

Retries: `task_run_sample` loops over `_task_run_sample_attempt` while `attempt.retries_remaining > 0` ([`run.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/_eval/task/run.py)), and `sandboxenv_cm` is entered inside each attempt, so **`retry_on_error` gives every attempt a fresh `sample_init`/`sample_cleanup` pair**. `Task.cleanup(state)` runs in a `finally` inside the sandbox context under `anyio.CancelScope(shield=True)` and its exceptions are logged as warnings, not raised.

Docs on cleanup semantics ([`sandboxing.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/sandboxing.qmd), "Environment Cleanup"): "When a task is completed, Inspect will automatically cleanup resources associated with the sandbox environment ... If for any reason resources are not cleaned up (e.g. if the cleanup itself is interrupted via Ctrl+C) you can globally cleanup all environments with the `inspect sandbox cleanup` command"; `--no-sandbox-cleanup` / `eval(..., sandbox_cleanup=False)` keeps environments for debugging.

### 1.3 What the third-party providers show about the lifecycle contract

**Docker** ([`docker/docker.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/util/_sandbox/docker/docker.py)): `default_concurrency()` returns `2 * effective_cpu_count()`; `sample_cleanup` does nothing when `interrupted` ("if we were interrupted then wait until the end of the task to cleanup (this enables us to show output for the cleanup operation)") and `task_cleanup` calls `project_cleanup_shutdown(cleanup)`, which sweeps everything tracked in a context var.

**Local** ([`local.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/util/_sandbox/local.py)): the smallest complete provider (about 150 lines): `sample_init` returns `{"default": LocalSandboxEnvironment()}`, `exec` is `subprocess(...)` in a per-sample temp dir, `sample_cleanup` uses a shorter stop timeout when `interrupted`. The docs warn `local` "should *only be used* if you are already running your evaluation in another sandbox".

**Proxmox** ([`_proxmox_sandbox_environment.py`](https://github.com/UKGovernmentBEIS/inspect_proxmox_sandbox/blob/53e2646c9fe63d0d9f0c8fada806824475389b01/src/proxmoxsandbox/_proxmox_sandbox_environment.py), [`schema.py`](https://github.com/UKGovernmentBEIS/inspect_proxmox_sandbox/blob/53e2646c9fe63d0d9f0c8fada806824475389b01/src/proxmoxsandbox/schema.py), [README](https://github.com/UKGovernmentBEIS/inspect_proxmox_sandbox/blob/53e2646c9fe63d0d9f0c8fada806824475389b01/README.md)), the closest analogue to a VM lab:

- **Target VMs without a guest agent are first-class.** `VmConfig.is_sandbox: bool = True`; "if True, the VM will show up as a sandbox. It must have the qemu-guest-agent installed". `sample_init` still builds a `ProxmoxSandboxEnvironment` for every VM and puts it in the returned dict under `vm_config.name`; only the first `is_sandbox=True` VM is aliased to `"default"`. README: "A VM with no guest agent at all (a router appliance) is therefore a valid dependency" for `depends_on`, and the roadmap lists "Normalize having a pfSense VM as the default route for networking". The README's CPU-model note is relevant to us: "Older guest kernels (notably FreeBSD/pfSense) can panic on nested virtualization with `host`; use `qemu64` for those."
- **Readiness of an appliance is weak there.** `healthcheck` "Requires qemu-guest-agent even when is_sandbox is False", so a router appliance is "ready" when Proxmox reports it running. Our provider must poll the OPNsense API instead.
- **Pooling and concurrency.** `default_concurrency()` returns `cls.proxmox_pool.default_concurrency()`; `sample_init` does `instance = await cls.proxmox_pool.acquire_instance(pool_id)` ("blocks if all in use") and wraps VM creation in `concurrency(f"proxmox-{instance.host}", 1)`. README: "Each eval sample acquires one instance from its pool, uses it exclusively, and releases it back when done. Concurrency is automatically limited to the total number of instances."
- **Cleanup discipline.** `sample_cleanup`: when not interrupted, delete SDN and VMs; when interrupted, "Interrupted samples skip cleanup; task_cleanup will sweep orphaned resources"; the instance is returned to the pool only if cleanup succeeded ("Dirty instances would cause the next sample to fail ... This may exhaust the pool but prevents cascading failures"). `task_cleanup(cleanup=True)` sweeps every tracked target; with `cleanup=False` it prints `inspect sandbox cleanup proxmox`. `cli_cleanup(None)` rebuilds the pools and sweeps by naming convention; cleanup by id is not implemented.
- **Snapshots are provider-specific extras.** `create_snapshot` / `restore_snapshot` are instance methods reached via `sandbox().as_type(ProxmoxSandboxEnvironment)` in [`experimental/snapshots.py`](https://github.com/UKGovernmentBEIS/inspect_proxmox_sandbox/blob/53e2646c9fe63d0d9f0c8fada806824475389b01/src/proxmoxsandbox/experimental/snapshots.py); `restore_snapshot` rolls back and then `await_vm(..., requires_guest_agent=True)`. Inspect's base contract has no snapshot API.
- **Exec is the expensive part.** Of roughly 1,300 lines, most implement `exec`/`read_file`/`write_file` over the QEMU guest agent, with size caps, chunking, ISO hot-plug for big writes, Windows paths and retry policy. A provider whose default environment is host-side (or a Linux client over SSH) avoids nearly all of that.

### 1.4 The alternatives

**(b) Task-level hooks only.** `Task(setup=..., cleanup=...)`: `setup` is "Setup step (always run even when the main `solver` is replaced)", a solver or list of solvers run per sample before the main solver; `cleanup` is "Optional cleanup function for task. Called after all solvers and scorers have run for each sample (including if an exception occurs during the run)" with signature `Callable[[TaskState], Awaitable[None]]` ([`task.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/_eval/task/task.py), [`tasks.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/tasks.qmd)). Process-wide `Hooks` ([`extensions-hooks.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/extensions-hooks.qmd)) add `on_task_start/end`, `on_sample_init` ("before its sandbox environments are created"), `on_sample_start`, `on_sample_attempt_start/end`, `on_sample_end`, but the class is instantiated once per process, "any exception raised by a hook is caught and logged as a warning", there is "no teardown event", and hooks are documented for "logging and monitoring frameworks". Nothing in this path gives a concurrency limit tied to lab capacity (a `concurrency()` block inside a setup solver is released when that solver returns), an `interrupted` flag, `--no-sandbox-cleanup`, `inspect sandbox cleanup`, or `SandboxEvent` transcript entries; a Ctrl+C during a setup solver's one-minute boot does reach `Task.cleanup` (it is in the `finally`), but the lab handle would have to travel through `store()`/`state.metadata`.

**(c) Lab managed wholly outside Inspect.** A controller process started before `inspect eval`; the task addresses fixed endpoints and asks the controller for a reset (over a local socket or CLI) from a setup solver. Zero Inspect coupling; the same controller serves pytest and manual use; trivial to `inspect view`. Costs: Inspect cannot size `max_samples` to the lab (must be set by hand and kept in sync), no per-sample cleanup on cancellation unless the controller implements TTLs, no transcript events, and reset must be idempotent and serialized by the controller itself.

### 1.5 Cost comparison

| | (a) custom `SandboxEnvironment` | (b) `Task.setup`/`cleanup` + hooks | (c) lab outside Inspect |
|---|---|---|---|
| Code to write | Provider class: 3 abstract instance methods, `sample_init`, `sample_cleanup`, plus `task_init`, `task_cleanup`, `cli_cleanup`, `default_concurrency`, frozen config model + `config_deserialize`, entry point. Lab controller underneath. | Setup solver + cleanup fn + lab controller | Lab controller + reset RPC + setup solver |
| Per-sample fresh state | `sample_init` per sample **and per retry attempt** | setup solver per attempt (must reset explicitly) | setup solver must call reset |
| Concurrency tied to lab capacity | `default_concurrency()` / `--max-sandboxes`, semaphore held for the whole sample | none; `--max-samples` by hand | none; `--max-samples` by hand |
| Cancel / Ctrl+C | `sample_cleanup(interrupted=True)` under a shielded cancel scope; `task_cleanup` sweep; `inspect sandbox cleanup qemu` | `Task.cleanup` runs shielded; no sweep, no CLI | controller TTL only |
| Keep lab up for debugging | `--no-sandbox-cleanup` (provider prints how to clean up) | ad hoc | natural |
| Transcript evidence | `SandboxEvent` for every `exec`/`read_file`/`write_file` | none unless logged by hand | none |
| Access from scorers | `sandbox("firewall").as_type(QemuVm)` | via `store()`/metadata | via fixed endpoints |
| Reuse from pytest | via the controller library (not via the provider) | same | same |
| Framework churn exposure | medium (0.3.x releases almost daily; the provider surface has been stable since the Docker/k8s/Proxmox providers were written) | low | none |

Recommendation: (a), with the controller kept Inspect-free so that (c) remains available for pytest and manual work at no extra cost.

### 1.6 Shape of the provider for v1

- `sample_init` returns, in this order, `{"default": <host-side or client environment>, "firewall": QemuVm(...), "client-a": QemuVm(...)}`. For v1 (read-only, the agent uses Pilot's MCP/CLI tools from the host) the default can be a host-side environment modelled on `LocalSandboxEnvironment` (subprocess in a per-sample temp dir) so scorers can run `opnsense-pilot inspect ...`; if a scenario needs traffic from inside the LAN, the default becomes an arm64 client with `exec` over SSH through a `hostfwd`.
- `QemuVm.exec` for the firewall: over the serial console (the probe's `console-run.exp` pattern, `/bin/sh` because root's shell is csh) so scorers can read `/conf/config.xml` or run `configctl` as evidence independent of the API; `read_file` via `exec` + base64; `write_file` refuses (raise `PermissionError`) on the firewall to preserve "no mutation path". Whether console exec is reliable enough is a prototype question; the fallback is `SandboxUnavailableError` for the firewall and evidence via the API only.
- Do not use `exec_remote`, `bash_session`, `text_editor` or other tools that inject sandbox-tools binaries against the firewall (they call `sandbox_with_injected_tools`, which would try to run an x86-64 Linux binary in FreeBSD).
- `default_concurrency()` = number of firewall slots the config declares (1 by default on this machine, 2 at most). Per-slot resources (QMP socket, serial socket, hostfwd ports, Unix socket paths) are derived from the slot index, not the sample, so concurrent samples cannot collide.
- `task_init` builds or verifies the per-scenario golden overlays with their baseline snapshot; `task_cleanup(cleanup=True)` stops every QEMU and `vde_switch` recorded in a per-run registry (a `ContextVar` or a run directory of pidfiles); `cli_cleanup(None)` stops everything under the lab run directory; `task_cleanup(cleanup=False)` prints the slot directories and the `inspect sandbox cleanup qemu` command.
- Config model: `class QemuLabConfig(BaseModel, frozen=True)` naming the scenario (image manifest, snapshot tag, topology); `config_deserialize` returns `QemuLabConfig(**config)` so logs round-trip.

## 2. Reset, cleanup on failure or interrupt, concurrency

### 2.1 Per-sample reset

Inspect's contract is only "return environments from `sample_init`, tear them down in `sample_cleanup`"; nothing requires the compute to be created per sample. Three reset mechanisms, all from QEMU docs at v11.1.1:

- **Warm reset by VM snapshot.** [`docs/system/images.rst`](https://github.com/qemu/qemu/blob/v11.1.1/docs/system/images.rst): "VM snapshots are snapshots of the complete virtual machine including CPU state, RAM, device state and the content of all the writable disks. In order to use VM snapshots, you must have at least one non removable and writable block device using the `qcow2` disk image format." HMP `savevm`/`loadvm`/`delvm`/`info snapshots`; the state lives in the first qcow2 device and "the disk image snapshots are stored in every disk image". QMP has job-based equivalents since 6.0: [`snapshot-save`](https://github.com/qemu/qemu/blob/v11.1.1/qapi/migration.json) (`job-id`, `tag`, `vmstate`, `devices`) and `snapshot-load` (same arguments); "Applications should not assume that the snapshot load is complete when this command returns. The job commands / events must be used to determine completion", and "execution of the guest CPUs will be stopped during the time it takes to load the snapshot". The probe used HMP through `human-monitor-command`; the QMP jobs give the provider proper completion and error reporting. Measured on the probe: 0.7 s to restore 1.18 GiB, API correct afterwards. Because the disk reverts with the snapshot, any `config.xml` change made during a sample is undone.
- **Cold reset by overlay replacement.** Delete `run/<slot>.qcow2` and re-create it from the base with `qemu-img create -f qcow2 -b base -F qcow2` (the probe's `start.sh`/`reset.sh`), then boot: about a minute to an answering API. Note that VM snapshots are stored *in* the overlay, so a scenario's baseline snapshot has to be taken once into a per-scenario "configured" overlay and each slot starts from a copy of that file (the probe's `configured.qcow2` checkpoint is exactly this).
- **`-snapshot` mode** ([`images.rst`](https://github.com/qemu/qemu/blob/v11.1.1/docs/system/images.rst)): writes go to a temp file and VM snapshots "are deleted as soon as you exit QEMU". Useful for throwaway boots, not for the per-sample loop.

Proposed loop: `task_init` ensures each slot has a fresh copy of the scenario overlay and a running QEMU at the baseline tag (or boots it and takes the tag); `sample_init` acquires a slot, `snapshot-load` the baseline, waits for `api_ready()` (HTTP GET with a new TLS connection each time; the probe found unauthenticated requests get a 302 and 403s take 65 ms), returns handles; `sample_cleanup(interrupted=False)` leaves the slot marked dirty (the next `sample_init` restores anyway) or restores eagerly if `--no-sandbox-cleanup` is not set; `sample_cleanup(interrupted=True)` only marks the slot dirty and returns quickly (the Docker/Proxmox convention), leaving `task_cleanup` to stop processes. Cold reset is the fallback whenever the API does not answer after a restore, and the mechanism behind `cli_cleanup`.

Inspect's checkpointing ([`checkpointing.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/checkpointing.qmd)) is unrelated: it captures "Filesystem state within sandboxes (home + other configured directories)" with restic or tar so a *retried* sample can resume, "restored from backup into a fresh sandbox container". It never touches VM state, needs `exec` and injected binaries in the sandbox, and should stay disabled for the firewall environment (`sandbox_paths={"firewall": []}` opts a sandbox out).

### 2.2 Cleanup on failure or interrupt (summary of the verified paths)

| Event | What Inspect does | What the provider must do |
|---|---|---|
| Solver/scorer raises, no retries left | sample recorded as error; `Task.cleanup` runs (shielded); `sample_cleanup(interrupted=False)` | normal release |
| Solver/scorer raises, `retry_on_error` left | `sample_cleanup(interrupted=False)`, then a new attempt calls `sample_init` again | normal release, then restore for the next attempt |
| `Sample.files`/`setup` fail | `sample_cleanup(interrupted=True)` from `init_sandbox_environments_sample`, exception re-raised | mark dirty; do not block |
| Ctrl+C / eval cancelled | cancellation propagates; `sample_cleanup(interrupted=True)` under `CancelScope(shield=True)`; then `task_cleanup(cleanup=True)` | fast path: record what is running; `task_cleanup` stops processes and removes sockets/pidfiles |
| Cleanup itself interrupted, or worker crash | nothing further | `inspect sandbox cleanup qemu` (`cli_cleanup(None)`) stops by pidfile directory; a TTL sweeper is our own concern (the handoff asks for "TTL cleanup after worker crashes") |
| `--no-sandbox-cleanup` | `sample_cleanup` skipped entirely (`cleanup` false in `sandboxenv_context`), `task_cleanup(cleanup=False)` | print slot paths, QMP/serial sockets and the cleanup command |

### 2.3 Concurrency

- `eval(..., max_sandboxes: int | None)`: "Maximum number of sandboxes (per-provider) to run in parallel"; `max_samples`: "Maximum number of samples to run in parallel within each task (default is max_connections)" ([`eval.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/src/inspect_ai/_eval/eval.py)). CLI: `--max-sandboxes`, `--max-samples`, `--max-tasks`, `--max-subprocesses`. The provider's `default_concurrency()` applies when `max_sandboxes` is unset; the semaphore is resizable at runtime through the control channel.
- The lab's real capacity is the number of firewall slots, so `default_concurrency()` must return that number and `sample_init` must block (queue) rather than fail when it cannot acquire a slot; with the semaphore held for the whole sample, blocking should not happen unless the operator raises `--max-sandboxes` above the slot count, in which case the provider should raise a clear error.
- Inspect also throttles `subprocess()` calls via `max_subprocesses` (default: processor count) and asks providers to use `concurrency()` for local subprocess-like work ([`parallelism.qmd`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/0.3.266/docs/parallelism.qmd)); all provider I/O must be `async` (anyio) or it stalls the whole eval.
- Warm `loadvm` per sample is compatible with all of this: it is an awaited QMP job inside `sample_init`, well under the sample setup budget, and does not change the number of processes.

## 3. Networking on unprivileged macOS

All option text from [`qemu-options.hx` at v11.1.1](https://github.com/qemu/qemu/blob/v11.1.1/qemu-options.hx) unless stated; behaviour notes from `net/*.c` at the same tag. "Unprivileged" means: no root, no `com.apple.vm.networking` entitlement (rules out `vmnet-*`, see the earlier [Apple Silicon research](https://github.com/andrewferk/opnsense-pilot/blob/research/apple-silicon-lab-viability/docs/research/apple-silicon-lab-viability.md)), no `/dev/tap` (rules out `tap`/`bridge`).

| Backend | Topology | Members | Privileges on macOS | Verified | Notes |
|---|---|---|---|---|---|
| `user` (slirp) | private NAT per VM, `hostfwd` in, `restrict=on` isolates | 1 VM + host | none | yes (probe) | "requires no administrator privilege to run"; `restrict=on`: "the guest will be isolated ... This option does not affect any explicitly set forwarding rules". Cannot join two VMs. Keep for the management NIC. |
| `socket,listen=/connect=` (TCP) | point-to-point | exactly 2 | none | docs + source | [`net/socket.c`](https://github.com/qemu/qemu/blob/v11.1.1/net/socket.c) `net_socket_accept` removes the listen handler after the first accepted connection, so one peer per listener. |
| `socket,mcast=` (UDP multicast) | bus | N | none | docs + source; macOS behaviour unverified | "effectively making a bus for every QEMU with same multicast address maddr and port"; `net_socket_mcast_create` sets `SO_REUSEADDR`, joins with `IP_ADD_MEMBERSHIP`, enables `IP_MULTICAST_LOOP`. A real multicast group on a host interface: frames can leave the machine and need a multicast-capable route. Not recommended. |
| `dgram,remote.type=inet` (multicast) | bus | N | none | docs + source | Same mechanism and caveats as `socket,mcast` in newer syntax ([`net/dgram.c`](https://github.com/qemu/qemu/blob/v11.1.1/net/dgram.c)). |
| `dgram,local.type=unix,local.path=,remote.type=unix,remote.path=` | point-to-point | exactly 2 | none | docs + source | "datagram oriented unix socket"; each side binds its own path and names the peer's. No IP stack, no ports, nothing leaves the host. Best fit for two-member segments. |
| `stream,addr.type=unix` (`server=on|off`, `reconnect-ms`) | point-to-point | exactly 2 | none | docs + source | [`net/stream_data.c`](https://github.com/qemu/qemu/blob/v11.1.1/net/stream_data.c) `net_stream_data_listen` clears the listener's client func after one accept, so one client per server; `reconnect-ms` lets a client outlive a server restart; QMP emits `NETDEV_STREAM_CONNECTED`. Also the documented way to attach `passt`. |
| `vde,sock=` | switch | N | none (userspace daemon) | build verified (`-netdev help` lists `vde`; `vde_switch` installed); running on macOS unverified | "Configure VDE backend to connect to PORT n of a vde switch running on host"; example `vde_switch -F -sock /tmp/myswitch`. One extra process per segment, owned by the provider's lifecycle. |
| `hubport,hubid=N[,netdev=nd]` | in-process hub | N netdevs inside one QEMU | none | docs | "The hubport netdev lets you connect a NIC to a QEMU emulated hub instead of a single netdev. Alternatively, you can also connect the hubport to another netdev with ID nd". Lets the firewall's one LAN NIC fan out to several point-to-point sockets (one per client) with no external switch. Frame forwarding between hub ports across mixed backends is unverified. |
| `vmnet-host/shared/bridged` | macOS vmnet | N | entitlement or root | n/a | Excluded. |
| `tap`, `bridge` | kernel tap | N | root / no tap on macOS | n/a | Excluded. |

Mixed architectures: every backend above exchanges raw Ethernet frames, so a `qemu-system-aarch64 -machine virt -accel hvf -cpu host` client and the TCG `qemu-system-x86_64` firewall can share a socket; [`qapi/net.json`](https://github.com/qemu/qemu/blob/v11.1.1/qapi/net.json) notes for `stream`/`dgram`: "Only `SocketAddress` types 'unix', 'inet' and 'fd' are supported."

Recommended topology for the v1 scenarios (a management NIC, a LAN with one or two clients, a WAN simulator):

```text
host 127.0.0.1:10443 --hostfwd--> [user, restrict=on] vtnet0 = management     firewall (qemu-system-x86_64, TCG)
                                                       vtnet1 = LAN  --dgram unix--> client-a (qemu-system-aarch64, HVF)
                                                                    (hubport fan-out or vde_switch when a second client joins)
                                                       vtnet2 = WAN  --dgram unix--> wan-sim (HVF: DNS + web server)
```

A dedicated management NIC keeps the API path (slirp `hostfwd`) outside the LAN/WAN segments under test, which is the handoff's "preserve management/console access outside the path being tested". Whether OPNsense's default assignment (first NIC LAN, second WAN) makes a dedicated management NIC awkward is a scenario-image question, not a QEMU one.

Memory budget under 24 GB (`hw.memsize` 25769803776):

| Component | Guest RAM | Host resident (planning) | Basis |
|---|---|---|---|
| Firewall slot (TCG, `-m 3072`) | 3 GB | about 2 GB idle measured, plan 4 GB busy | probe measurement; TCG translation cache up to 1 GiB by default |
| arm64 Alpine client (HVF, `-m 256`..`512`) | 0.25 to 0.5 GB | about 0.5 GB | estimate, not measured |
| `vde_switch` | none | negligible | estimate |
| One slot + 3 clients | | about 5.5 GB | |
| Two slots + 6 clients | | about 11 GB | |
| macOS + PostgreSQL/Docker + Inspect | | 6 to 10 GB | |

So `default_concurrency()` of 1 is comfortable and 2 fits; 3 firewall slots would be 12 to 15 GB of VM plus overhead and is not advisable alongside Docker Desktop. CPU, not memory, is the more likely limiter for two TCG firewalls (each boot saturates two performance cores).

## 4. What only a prototype can settle

1. **`loadvm` versus the network.** After a restore the guest's TCP/ARP state jumps back while slirp and any peer VMs kept running. Expected: in-flight host connections to the API are reset (harmless with a new TLS connection per request), and clients may hold stale ARP/TCP state. Options to test: restore clients too (they are HVF, so a reboot is also cheap), or bring client links down/up around the restore. Also whether `NETDEV_STREAM_CONNECTED`/`reconnect-ms` matters when the firewall is restored while a `stream` peer is attached.
2. **Serial-console `exec` for the firewall.** Latency, reliability across many samples, login-state after `loadvm` (the console may be mid-session in the snapshot), and the csh/`/bin/sh` quirks the probe found. Alternative: enable SSH with a key in the scenario image and use `hostfwd` 10022.
3. **`dgram` Unix and `stream` Unix between TCG x86-64 and HVF aarch64 QEMUs on macOS 26**: throughput, whether `dgram` sends fail until the peer has bound its path (start order), and whether socket files survive `loadvm`.
4. **`hubport` fan-out** inside one QEMU across mixed backends, versus a per-sample `vde_switch`: which actually forwards frames, and the process/cleanup cost.
5. **Two TCG firewalls at once**: API latency and boot time under CPU contention on the M4 Pro; whether `max_sandboxes=2` is worth it.
6. **Snapshot hygiene over many samples**: overlay growth after hundreds of `loadvm`s, `savevm` of a fresh baseline per scenario in `task_init` (about a minute per scenario per slot) versus copying a prebuilt overlay.
7. **Interrupt paths end to end**: Ctrl+C during `sample_init` boot, during `loadvm`, and during `task_cleanup`; confirm no orphaned QEMU/`vde_switch` processes remain and that `inspect sandbox cleanup qemu` recovers the rest. Inspect gives `sample_init` no timeout, so the provider's own boot deadline must be tested.
8. **Memory of arm64 clients** (the 0.5 GB figure is an estimate) and of a firewall slot under load (the 1.9 GB figure is idle).

## 5. Open uncertainties

- **Inspect release cadence.** 0.3.x ships almost daily (0.3.252 to 0.3.266 in the tag list; no GitHub releases, only tags). The provider surface used here (`sample_init`/`sample_cleanup`/`task_init`/`task_cleanup`/`cli_cleanup`/`default_concurrency`/`config_deserialize`) is shared by the built-in Docker provider and the Proxmox and k8s packages, which is the best available stability signal; pin `inspect-ai` and re-verify signatures on upgrade. `SandboxEnvironments` (a dataclass with a `cleanup` callable) exists in `environment.py` but is not used by the sample driver; ignore it.
- **`exec_remote` and sandbox-tools injection.** Any tool or Inspect feature that calls `exec_remote` or `sandbox_with_injected_tools` (`bash_session`, `text_editor`, web browsing tools, the checkpoint restic strategy) will try to inject binaries into whichever sandbox it targets. The firewall must never be that target; which built-in tools inject was not enumerated here.
- **Whether a host-side "default" environment is acceptable to Inspect's tooling.** `LocalSandboxEnvironment` is documented as only for use inside another sandbox; a host-side default mirrors it. If future scenarios give the agent `bash()`, that must run in a client VM, not on the host.
- **Slirp and `loadvm` interaction** (see prototype item 1): slirp's connection table lives in the QEMU process and is not part of the VM snapshot; the docs do not describe what happens to established forwards across a restore.
- **`socket,mcast` on macOS** was not tested by anyone we can cite; it is excluded on isolation grounds regardless.
- **UDP multicast, VDE and `hubport` frame forwarding with `virtio-net` under HVF on macOS 26** are documented features but there is no primary-source evidence about macOS-specific behaviour; the prototype decides.
- **OPNsense interface assignment** for a three-NIC (management, LAN, WAN) layout in the golden image is untested and belongs to the scenario-image work, not to this ticket.

## Method and limits

Inspect source and docs were read from a shallow clone at tag `0.3.266`; the Proxmox provider from a clone at `53e2646`; QEMU from raw files at `v11.1.1` (`qemu-options.hx`, `docs/system/images.rst`, `docs/system/devices/net.rst`, `qapi/migration.json`, `qapi/net.json`, `net/socket.c`, `net/dgram.c`, `net/stream.c`, `net/stream_data.c`). Local checks were read-only: `qemu-system-* --version`, `-netdev help`, `brew info vde`, `which vde_switch`, `sysctl hw.memsize`, and the probe's scripts. Nothing was installed, started, or changed. Everything labelled "estimate", "expected", or "unverified" is not backed by a primary source and is listed under sections 4 and 5.
