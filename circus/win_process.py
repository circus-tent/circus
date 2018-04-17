import time
import signal

import psutil
import wmi

from circus import logger
from circus import process
from circus.util import debuglog


class WinProcessError(OSError):
    '''
    All windows process/service specific errors must derive from this one.
    '''

SUCCESS = 0
START_SERVICE_ECODES = {
    SUCCESS: "The request was accepted.",
    1: "The request is not supported.",
    2: "The user did not have the necessary access.",
    3: "The service cannot be stopped because other services that are running are dependent on it.",
    4: "The requested control code is not valid, or it is unacceptable to the service.",
    5: "The requested control code cannot be sent to the service because the "
       "the service is not supporting this request, or user doesn't have necessary access",
    6: "The service has not been started.",
    7: "The service did not respond to the start request in a timely fashion.",
    8: "Unknown failure when starting the service.",
    9: "The directory path to the service executable file was not found.",
    10: "The service is already running.",
    11: "The database to add a new service is locked.",
    12: "A dependency this service relies on has been removed from the system.",
    13: "The service failed to find the service needed from a dependent service.",
    14: "The service has been disabled from the system.",
    15: "The service does not have the correct authentication to run on the system.",
    16: "This service is being removed from the system.",
    17: "The service has no execution thread.",
    18: "The service has circular dependencies when it starts.",
    19: "A service is running under the same name.",
    20: "The service name has invalid characters.",
    21: "Invalid parameters have been passed to the service.",
    22: "The account under which this service runs is either invalid or lacks the permissions to run the service.",
    23: "The service exists in the database of services available from the system.",
    24: "The service is currently paused in the system.",
}


STOPPED = "Stopped"
START_PENDING = "Start Pending"
STOP_PENDING = "Stop Pending"
RUNNING = "Running"
CONT_PENDING = "Continue Pending"
PAUSE_PENDING = "Pause Pending"
PAUSED = "Paused"
UNKNOWN = "Unknown"

DISABLED = "Disabled"
MANUAL = "Manual"


class WinService(process.Process):
    '''
    Wraps windows service.
    '''
    def __init__(self, *args, **kwargs):
        self._server = kwargs.pop("server") if "server" in kwargs else None
        self._wmi = self._make_wmi_connection(self._server)
        self._service = None

        # Must call super last, otherwise spawn may be called before anything
        # below __init__ get initialized
        super().__init__(*args, **kwargs)

    def _make_wmi_connection(self, server):
        '''
        Create the WMI connection to start the windows process.

        @param server - name of the server on which the process needs to be
                        started
        '''
        if server:
            return wmi.WMI(computer=server)
        else:
            return wmi.WMI()

    @property
    def service(self):
        '''
        This property always returns a fresh copy of the service
        '''
        service = self._wmi.Win32_Service(displayname=self.cmd)\
            or self._wmi.Win32_Service(name=self.cmd)

        if not service:
            raise WinProcessError("System can't find service: {}".format(self.cmd))
        return service[0]

    @debuglog
    def poll(self):
        return None if self.is_alive() else self.service.ExitCode

    @debuglog
    def is_alive(self):
        return self._worker.is_running()

    def returncode(self):
        return self.poll()

    @property
    def stdout(self):
        """Return the *stdout* stream"""
        return None

    @property
    def stderr(self):
        """Return the *stdout* stream"""
        return None

    @debuglog
    def stop(self):
        '''
        Use WMI API to shutdown this service.
        '''
        if self.is_alive():
            self._stop_service()

    @debuglog
    def send_signal(self, sig):
        '''
        Overwrite the default behavior to cleanly stop the windows service
        using WMI if "sig" is SIGTERM.
        '''
        if sig == signal.SIGTERM:
            logger.debug("sending signal %s to %s" % (sig, self.pid))
            self._stop_service()
        else:
            super().send_signal(sig)

    def spawn(self):
        '''
        Spawn a new instance of this process
        '''
        self.started = time.time()
        if self.service.StartMode == DISABLED:
            self._exec_service_command("ChangeStartMode", MANUAL)

        self._stop_service()
        self._exec_service_command("StartService")
        self._worker = psutil.Process(self.service.ProcessID)

    def _stop_service(self):
        if self.service.State == STOPPED:
            return

        self.service.StopService()
        if self.service.State == STOP_PENDING:
            time.sleep(0.05)
            if self.service.State != STOPPED:
                raise WinProcessError("Unable to stop Windows Service: {}".format(self.cmd))

    def _exec_service_command(self, command, *args):
        '''
        Helper method to execute WMI service commands

        @param command - WMI method to execute
        @param *args - arguments to the command method
        '''
        res = getattr(self.service, command)(*args)[0]
        if res != SUCCESS:
            raise self._make_error(res)

    def _make_error(self, ecode):
        '''
        Helper method to make an exception and populate it with an appropriate
        error.
        '''
        message = START_SERVICE_ECODES.get(ecode, "Unknown error occurred: {}".format(ecode))
        return WinProcessError(message)
