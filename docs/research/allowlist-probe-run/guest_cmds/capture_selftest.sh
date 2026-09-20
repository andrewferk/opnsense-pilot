rm -f /tmp/selftest.pcap;
(nohup tcpdump -ni vtnet1 -w /tmp/selftest.pcap >/dev/null 2>&1 &);
/bin/sleep 2;
ping -c 2 -t 3 10.0.2.2 >/dev/null 2>&1;
echo PING_RC $?;
cat /etc/resolv.conf;
host -W 3 pkg.opnsense.org 2>&1 | head -3;
configctl firmware remote 2>&1 | head -c 300;
echo;
/bin/sleep 2;
pkill -INT tcpdump;
/bin/sleep 2;
echo SELFTEST_PACKETS $(tcpdump -nr /tmp/selftest.pcap 2>/dev/null | wc -l);
tcpdump -nr /tmp/selftest.pcap 2>/dev/null | head -12
