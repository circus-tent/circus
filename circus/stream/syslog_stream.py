from urllib.parse import urlparse
import logging
import socket
import syslog

from circus.util import to_str


class SyslogStream(object):

    # priorities (these are ordered)
    LOG_EMERG = 0       # system is unusable
    LOG_ALERT = 1       # action must be taken immediately
    LOG_CRIT = 2       # critical conditions
    LOG_ERR = 3       # error conditions
    LOG_WARNING = 4       # warning conditions
    LOG_NOTICE = 5       # normal but significant condition
    LOG_INFO = 6       # informational
    LOG_DEBUG = 7       # debug-level messages

    # facility codes
    LOG_KERN = 0       # kernel messages
    LOG_USER = 1       # random user-level messages
    LOG_MAIL = 2       # mail system
    LOG_DAEMON = 3       # system daemons
    LOG_AUTH = 4       # security/authorization messages
    LOG_SYSLOG = 5       # messages generated internally by syslogd
    LOG_LPR = 6       # line printer subsystem
    LOG_NEWS = 7       # network news subsystem
    LOG_UUCP = 8       # UUCP subsystem
    LOG_CRON = 9       # clock daemon
    LOG_AUTHPRIV = 10      # security/authorization messages (private)
    LOG_FTP = 11      # FTP daemon

    # other codes through 15 reserved for system use
    LOG_LOCAL0 = 16      # reserved for local use
    LOG_LOCAL1 = 17      # reserved for local use
    LOG_LOCAL2 = 18      # reserved for local use
    LOG_LOCAL3 = 19      # reserved for local use
    LOG_LOCAL4 = 20      # reserved for local use
    LOG_LOCAL5 = 21      # reserved for local use
    LOG_LOCAL6 = 22      # reserved for local use
    LOG_LOCAL7 = 23      # reserved for local use

    facility_names = {
        "auth":     LOG_AUTH,
        "authpriv": LOG_AUTHPRIV,
        "cron":     LOG_CRON,
        "daemon":   LOG_DAEMON,
        "ftp":      LOG_FTP,
        "kern":     LOG_KERN,
        "lpr":      LOG_LPR,
        "mail":     LOG_MAIL,
        "news":     LOG_NEWS,
        "security": LOG_AUTH,       # DEPRECATED
        "syslog":   LOG_SYSLOG,
        "user":     LOG_USER,
        "uucp":     LOG_UUCP,
        "local0":   LOG_LOCAL0,
        "local1":   LOG_LOCAL1,
        "local2":   LOG_LOCAL2,
        "local3":   LOG_LOCAL3,
        "local4":   LOG_LOCAL4,
        "local5":   LOG_LOCAL5,
        "local6":   LOG_LOCAL6,
        "local7":   LOG_LOCAL7,
        }

    def __init__(self, syslog_url, ident=None):
        self.socktype = None
        info = urlparse(syslog_url)
        facility = 'user'
        if info.query in logging.handlers.SysLogHandler.facility_names:
            facility = info.query
        if info.netloc:
            address = (info.hostname, info.port or 514)
        else:
            address = info.path

        if ident:
            self.ident = ident
        else:
            self.ident = ''
        self.address = address
        self.facility = facility
        self.init_syslog(address)

    def init_syslog(self, address):
        if isinstance(address, str):
            self.unixsocket = True
            syslog.openlog(self.ident)
        else:
            self.unixsocket = False
            socktype = socket.SOCK_DGRAM
            host, port = address
            ress = socket.getaddrinfo(host, port, 0, socktype)
            if not ress:
                raise OSError("getaddrinfo returns an empty list")
            for res in ress:
                af, socktype, proto, _, sa = res
                err = sock = None
                try:
                    sock = socket.socket(af, socktype, proto)
                    if socktype == socket.SOCK_STREAM:
                        sock.connect(sa)
                    break
                except OSError as exc:
                    err = exc
                    if sock is not None:
                        sock.close()
            if err is not None:
                raise err
            self.socket = sock
            self.socktype = socktype

    def write_data(self, data):
        # data to write to syslog
        syslog_data = to_str(data['data'])
        if self.unixsocket:
            # facility dealt with when opening syslog
            # priority forced to LOG_INFO
            syslog.syslog(syslog_data)
        else:
            if self.ident:
                syslog_data = self.ident + ":" + syslog_data
            facility = self.facility_names[self.facility]
            priority = self.LOG_INFO
            priority = (facility << 3) | priority
            syslog_data = "<" + str(priority) + ">" + syslog_data
            self.socket.sendto(syslog_data.encode('utf-8'), self.address)

    def __call__(self, data):
        self.write_data(data)

    def close(self):
        """
        Closes the socket.
        """
        if self.unixsocket:
            syslog.closelog()
        else:
            self.socket.close()
