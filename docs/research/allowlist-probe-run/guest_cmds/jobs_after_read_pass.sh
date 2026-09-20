ls -l /tmp/wan13.pcap;
echo PCAP_PACKETS $(tcpdump -nr /tmp/wan13.pcap 2>/dev/null | wc -l);
tcpdump -ttnr /tmp/wan13.pcap 2>/dev/null | head -40;
echo CONFIGD_SAMPLE;
tail -n +640 /var/log/configd/latest.log | head -3;
echo CONFIGD_ACTIONS;
tail -n +640 /var/log/configd/latest.log | sed -E "s/^.*\] //" | sort | uniq -c | sort -rn | head -50;
echo AUDIT_SAMPLE;
tail -n +571 /var/log/audit/latest.log | head -3;
echo AUDIT_ACTIONS;
tail -n +571 /var/log/audit/latest.log | sed -E "s/^.*\] //" | sort | uniq -c | sort -rn | head -50
