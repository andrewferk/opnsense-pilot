#!/bin/sh
# Thin, throwaway OPNsense probe VM (wayfinder ticket #12). Not the reproducible lab.
# DRAFT: written before QEMU was installed; untested until the first boot.
set -eu

PROBE="$HOME/.local/share/opnsense-pilot-probe"
BASE="$PROBE/images/OPNsense-26.7-nano-amd64.qcow2"   # converted from the verified raw image, never booted
DISK="$PROBE/run/probe.qcow2"                         # overlay; delete it to cold-reset
mkdir -p "$PROBE/run"

[ -f "$DISK" ] || qemu-img create -f qcow2 -b "$BASE" -F qcow2 "$DISK" 16G

# vtnet0 = LAN (management, host-reachable), vtnet1 = WAN (slirp DHCP on 10.0.2.0/24).
# The WAN is isolated too unless PROBE_ONLINE=1, which firmware updates need.
if [ "${PROBE_ONLINE:-0}" = "1" ]; then WAN_RESTRICT=off; else WAN_RESTRICT=on; fi

# Pure emulation (TCG): HVF cannot accelerate an amd64 guest on Apple Silicon.
# One NIC only, so OPNsense assigns it as LAN (192.168.1.1/24). Slirp is renumbered
# onto that subnet and restricted: the guest cannot reach the network, only the
# host can reach the guest, through loopback-only forwards.
exec qemu-system-x86_64 \
  -name opnsense-probe \
  -machine q35 -accel tcg,thread=multi -cpu qemu64 -smp 2 -m 3072 \
  -drive if=virtio,file="$DISK",format=qcow2 \
  -netdev user,id=lan,restrict=on,net=192.168.1.0/24,host=192.168.1.2,dhcpstart=192.168.1.100,hostfwd=tcp:127.0.0.1:10443-192.168.1.1:443,hostfwd=tcp:127.0.0.1:10022-192.168.1.1:22 \
  -device virtio-net-pci,netdev=lan,mac=52:54:00:12:34:56 \
  -netdev user,id=wan,restrict="$WAN_RESTRICT" \
  -device virtio-net-pci,netdev=wan,mac=52:54:00:12:34:57 \
  -display none \
  -chardev socket,id=ser0,path="$PROBE/run/serial.sock",server=on,wait=off,logfile="$PROBE/run/serial.log",logappend=on \
  -serial chardev:ser0 \
  -qmp unix:"$PROBE/run/qmp.sock",server=on,wait=off \
  -pidfile "$PROBE/run/qemu.pid" \
  -daemonize
