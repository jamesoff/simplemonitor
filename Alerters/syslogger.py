try:
    import syslog
except:
    pass

from alerter import Alerter


class SyslogAlerter(Alerter):

    def send_alert(self, name, monitor):
        type = self.should_alert(monitor)
        if type == "failure":
            syslog.syslog(
                syslog.LOG_WARNING | syslog.LOG_USER,
                "Monitor %s failed %d times with message: %s" % (
                    name,
                    monitor.virtual_fail_count(),
                    monitor.get_result()
                )
            )
