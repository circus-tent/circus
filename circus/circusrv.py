import win32serviceutil
import win32security
import servicemanager
import os
import logging
import traceback

from circus.arbiter import Arbiter
from circus.util import check_future_exception_and_log, LOG_LEVELS


def grant_service_login_right(account_name):
    policy_handle = win32security.GetPolicyHandle('', win32security.POLICY_ALL_ACCESS)
    try:
        sid = win32security.LookupAccountName('', account_name)[0]
        win32security.LsaAddAccountRights(policy_handle, sid, ['SeServiceLogonRight'])
    finally:
        win32security.LsaClose(policy_handle)


class ServiceManagerHandler(logging.Handler):
    _map_ = {
        logging.CRITICAL: servicemanager.EVENTLOG_ERROR_TYPE,
        logging.ERROR: servicemanager.EVENTLOG_ERROR_TYPE,
        logging.WARNING: servicemanager.EVENTLOG_WARNING_TYPE,
        logging.INFO: servicemanager.EVENTLOG_INFORMATION_TYPE,
        logging.DEBUG: servicemanager.EVENTLOG_INFORMATION_TYPE
    }

    def emit(self, record):
        level = self._map_.get(record.levelno)
        details = ""
        if record.exc_info is not None:
            formated_exc = traceback.format_exception(*record.exc_info)
            details = os.linesep.join(formated_exc)
        servicemanager.LogMsg(level, 0xF000, (record.getMessage(), details))


class CircusSrv(win32serviceutil.ServiceFramework):
    _svc_name_ = 'circus'
    _svc_display_name_ = 'Circus'
    _svc_description_ = 'Run some watchers.'

    _parameter_config = 'Config'
    _parameter_loglevel = 'LogLevel'

    def __init__(self, args):
        self._svc_name_ = args[0]
        super(CircusSrv, self).__init__(args)

        config = win32serviceutil.GetServiceCustomOption(self._svc_name_, self._parameter_config)
        loglevel = logging.INFO
        try:
            lls = win32serviceutil.GetServiceCustomOption(self._svc_name_, self._parameter_loglevel)
            if lls is not None:
                loglevel = LOG_LEVELS.get(lls.lower(), logging.INFO)
        except:
            pass

        root_logger = logging.getLogger()
        root_logger.setLevel(loglevel)
        root_logger.handlers = [ServiceManagerHandler()]

        # From here it can also come from the arbiter configuration
        # load the arbiter from config
        self.arbiter = Arbiter.load_from_config(config)

    def SvcStop(self):
        self.arbiter.loop.run_sync(self.arbiter._emergency_stop)

    def SvcDoRun(self):
        arbiter = self.arbiter
        try:
            future = arbiter.start()
            check_future_exception_and_log(future)
        except Exception as e:
            # emergency stop
            arbiter.loop.run_sync(arbiter._emergency_stop)
            raise (e)
        except KeyboardInterrupt:
            pass

    @classmethod
    def OptionsHandler(cls, opts):
        username = None
        for opt, val in opts:
            if opt == '--username':
                username = val
            if opt == '-c':
                win32serviceutil.SetServiceCustomOption(cls._svc_name_,
                                    cls._parameter_config,
                                    val)
            if opt == '-l':
                win32serviceutil.SetServiceCustomOption(cls._svc_name_,
                                    cls._parameter_loglevel,
                                    val)
        if username is not None:
            # Take only user from domain\user
            username = username.split('\\')[-1]
            grant_service_login_right(username)

        # Register now the source (rights of service's user may be different)
        servicemanager.SetEventSourceName(cls._svc_name_, True)


def main():
    kwargs = {}
    kwargs['customInstallOptions'] = 'c:l:'
    kwargs['customOptionHandler'] = CircusSrv.OptionsHandler
    ret = win32serviceutil.HandleCommandLine(CircusSrv, **kwargs)
    sys.exit(ret)


if __name__ == '__main__':
    main()
