echo SYSTEM_LINES $(wc -l < /var/log/system/latest.log);
echo CONFIG_SHA $(sha256 -q /conf/config.xml);
echo BACKUPS $(ls /conf/backup | wc -l);
echo AUDIT_MUTATIONS;
grep -E "pilot-readonly|clear|restart|reconfigure|filter.reload|interface.apply" /var/log/audit/latest.log | sed -E "s/^.*\] //" | sed -E "s/api key .*/api key <redacted>/" | sort | uniq -c | sort -rn | head -14;
echo CRON $(ps -axo lstart,comm | grep cron | grep -v grep | head -1);
diff /conf/backup/$(ls -t /conf/backup | sed -n 2p) /conf/config.xml | head -12
