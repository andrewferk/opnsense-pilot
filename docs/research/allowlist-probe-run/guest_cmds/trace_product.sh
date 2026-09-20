echo DEFAULT_ROUTES $(netstat -rn4 | grep -c "^default");
truss -f -o /tmp/tp.out /usr/local/opnsense/scripts/firmware/product.php > /tmp/product.json 2>/dev/null;
echo TRUSS_LINES $(wc -l < /tmp/tp.out);
echo NET_SYSCALLS $(grep -c -E " (connect|sendto|sendmsg)\(" /tmp/tp.out);
grep -E " (connect|sendto|sendmsg)\(" /tmp/tp.out | cut -c1-150 | head -8;
echo INET_SOCKETS $(grep -E " socket\(" /tmp/tp.out | grep -c -E "PF_INET");
echo EXECS;
grep "execve(" /tmp/tp.out | sed -E "s/.*execve\(.([^,]+).,.*/\1/" | sort | uniq -c | sort -rn | head -16
