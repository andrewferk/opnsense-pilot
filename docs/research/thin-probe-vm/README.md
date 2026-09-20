# OPNsense Pilot: thin probe VM

Throwaway. Exists only to unblock the compatibility-target decision
([ticket](https://github.com/andrewferk/opnsense-pilot/issues/12)). Not the reproducible lab.

- **Guest:** OPNsense Community 26.7.4_1 (amd64), core hash `4fd8ebfb1`, FreeBSD 15.1-RELEASE-p3,
  installed from `OPNsense-26.7-nano-amd64.img.bz2`
  (SHA-256 `28d5e2f37e40d87468a924e3006ef10e2ddc6de485b85333d9e3958c84d0cb9d`, signature verified),
  then `opnsense-update -p` and `opnsense-update -bk` on 2026-09-20.
- **Host:** Apple M4 Pro, Homebrew QEMU 11.1.1, pure TCG emulation, q35, 2 vCPU, 3 GB.
- **Network:** `vtnet0` LAN 192.168.1.1 and `vtnet1` WAN 10.0.2.15, both on restricted user-mode
  networking. The host reaches the guest only at `https://127.0.0.1:10443` (GUI/API) and
  `127.0.0.1:10022` (SSH, disabled in the guest). The guest reaches nothing unless started with
  `PROBE_ONLINE=1`.
- **Credentials:** `credentials.env` (mode 0600): root, `pilot-admin` (`page-all`), and
  `pilot-readonly` (`page-system-login-logout`, `page-system-status`, `user-config-readonly`),
  each API user with a key and secret. Never commit it.

| Do | Command |
| --- | --- |
| Start (isolated) | `./start.sh` (API answers in about 50 s, login prompt in about 60 s) |
| Start with internet | `PROBE_ONLINE=1 ./start.sh` |
| Stop | `./stop.sh` (ACPI powerdown, about 12 s) |
| Serial console | `./console.sh` (Ctrl-C detaches) |
| Run one root command | `. ./credentials.env; ./console-run.exp "$PROBE_ROOT_PASSWORD" 'opnsense-version'` |
| Cold reset to the configured state | `./reset.sh && ./start.sh` |
| Cold reset to factory 26.7 | `./reset.sh factory && ./start.sh` |
| Warm snapshot / restore | `./qmp.py savevm NAME` / `./qmp.py loadvm NAME` (under 1 s each) |
| Smoke test and latency | `./measure.sh` |

`run/configured.qcow2` is the checkpoint (updated, WAN assigned, users and keys created).
`run/probe.qcow2` is the live overlay; both sit on `images/OPNsense-26.7-nano-amd64.qcow2`,
which must never be booted directly. Delete this whole directory to remove the probe.
