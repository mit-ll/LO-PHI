#
# Regular cron jobs for the lophi-disk-introspection-server package
#
0 4	* * *	root	[ -x /usr/bin/lophi-disk-introspection-server_maintenance ] && /usr/bin/lophi-disk-introspection-server_maintenance
