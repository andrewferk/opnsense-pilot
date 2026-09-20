#!/bin/sh
# Attach to the probe VM's serial console. Ctrl-C detaches; the VM keeps running.
exec nc -U "$HOME/.local/share/opnsense-pilot-probe/run/serial.sock"
