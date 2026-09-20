echo INFO_ACTIONS;
grep -E "firmware|Retrieve|pkg" /var/log/configd/latest.log | sed -E "s/^.*\] //" | sort | uniq -c | head -12;
truss -f -o /tmp/tr.out /usr/local/opnsense/scripts/firmware/query.sh remote > /dev/null 2>&1;
echo TRUSS_LINES $(wc -l < /tmp/tr.out);
echo NET_SYSCALLS $(grep -c -E " (connect|sendto|sendmsg)\(" /tmp/tr.out);
echo INET_SOCKETS $(grep -E " socket\(" /tmp/tr.out | grep -c PF_INET);
grep -E " connect\(" /tmp/tr.out | cut -c1-150 | head -5
