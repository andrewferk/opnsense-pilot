---
status: accepted
---

# The developer's local machine is the primary lab; Proxmox is optional

The handoff names Proxmox as the repeatable shared lab path and QEMU as the local alternative. We reverse that: every lab, test, and evaluation path must run on the developer's own machine (currently an Apple Silicon Mac, so OPNsense amd64 runs under QEMU software emulation), because no Proxmox host can be guaranteed to stay available. Proxmox support may be added later as an optional accelerator, but nothing in the v1 plan may depend on it.

## Consequences

- Emulated amd64 is slow; lab scenarios, topologies, and CI expectations must be sized for it. If emulation proves unusable, that is a decision to bring back to the owner, not a reason to fall back to Proxmox silently.
- The `inspect_proxmox_sandbox` project is not evaluated for v1; how Inspect drives a local QEMU lab is an open question for the v1 plan.
