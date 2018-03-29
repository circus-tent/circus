import win32serviceutil
import win32api
import win32con
import servicemanager
import os
import logging
import traceback

from circus.arbiter import Arbiter
from circus.util import check_future_exception_and_log, LOG_LEVELS


def getServiceKeyTuple(sn, prm):
    key = "System\\CurrentControlSet\\Services\\%s\\%s" % (sn, prm)
    return win32con.HKEY_LOCAL_MACHINE, key


def setServiceParameter(serviceName, parameter, value):
    keyTuple = getServiceKeyTuple(serviceName, parameter)
    if value is not None:
        key = win32api.RegCreateKey(*keyTuple)
        try:
            win32api.RegSetValue(key, None, win32con.REG_SZ, value)
        finally:
            win32api.RegCloseKey(key)
    else:
        win32api.RegDeleteKey(*keyTuple)


def getServiceParameter(serviceName, parameter):
    keyTuple = getServiceKeyTuple(serviceName, parameter)
    key = win32api.RegOpenKey(*keyTuple)
    try:
        return win32api.RegQueryValue(key, None)
    finally:
        win32api.RegCloseKey(key)


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
        super().__init__(args)

        config = getServiceParameter(self._svc_name_, self._parameter_config)
        loglevel = logging.INFO
        try:
            lls = getServiceParameter(self._svc_name_, self._parameter_loglevel)
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
        self.arbiter.stop()

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
        for opt, val in opts:
            if opt == '-c':
                setServiceParameter(cls._svc_name_,
                                    cls._parameter_config,
                                    val)
            if opt == '-l':
                setServiceParameter(cls._svc_name_,
                                    cls._parameter_loglevel,
                                    val)


def main():
    kwargs = {}
    kwargs['customInstallOptions'] = 'c:l:'
    kwargs['customOptionHandler'] = CircusSrv.OptionsHandler
    ret = win32serviceutil.HandleCommandLine(CircusSrv, **kwargs)
    sys.exit(ret)


if __name__ == '__main__':
    main()
