from __future__ import print_function, division, absolute_import

import os

"""
Fix windows Popen for supporting socket as pipe
"""

if os.name == "nt":
    import subprocess
    import socket
    import sys
    import msvcrt
    if sys.version_info < (3, 0):
        import _subprocess
    else:
        import _winapi

    SO_OPENTYPE = 0x7008
    SO_SYNCHRONOUS_ALERT = 0x10
    SO_SYNCHRONOUS_NONALERT = 0x20

    PIPE = subprocess.PIPE
    STDOUT = subprocess.STDOUT
    if sys.version_info >= (3, 0):
        DEVNULL = subprocess.DEVNULL

    class WindowsPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            super(WindowsPopen, self).__init__(*args, **kwargs)

        if sys.version_info < (3, 0):
            def _get_handles(self, stdin, stdout, stderr):
                """Construct and return tuple with IO objects:
                p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
                """
                to_close = set()
                if stdin is None and stdout is None and stderr is None:
                    return (None, None, None, None, None, None), to_close

                p2cread, p2cwrite = None, None
                c2pread, c2pwrite = None, None
                errread, errwrite = None, None

                if stdin is None:
                    p2cread = _subprocess.GetStdHandle(_subprocess.STD_INPUT_HANDLE)
                    if p2cread is None:
                        p2cread, _ = _subprocess.CreatePipe(None, 0)
                elif stdin == PIPE:
                    p2cread, p2cwrite = _subprocess.CreatePipe(None, 0)
                elif isinstance(stdin, int):
                    p2cread = msvcrt.get_osfhandle(stdin)
                else:
                    # Assuming file-like object
                    if not hasattr(stdin, '_sock'):
                        p2cread = msvcrt.get_osfhandle(stdin.fileno())
                    else:
                        p2cread = stdin.fileno()
                p2cread = self._make_inheritable(p2cread)
                # We just duplicated the handle, it has to be closed at the end
                to_close.add(p2cread)
                if stdin == PIPE:
                    to_close.add(p2cwrite)

                if stdout is None:
                    c2pwrite = _subprocess.GetStdHandle(_subprocess.STD_OUTPUT_HANDLE)
                    if c2pwrite is None:
                        _, c2pwrite = _subprocess.CreatePipe(None, 0)
                elif stdout == PIPE:
                    c2pread, c2pwrite = _subprocess.CreatePipe(None, 0)
                elif isinstance(stdout, int):
                    c2pwrite = msvcrt.get_osfhandle(stdout)
                else:
                    # Assuming file-like object
                    if not hasattr(stdout, '_sock'):
                        c2pwrite = msvcrt.get_osfhandle(stdout.fileno())
                    else:
                        c2pwrite = stdout.fileno()
                c2pwrite = self._make_inheritable(c2pwrite)
                # We just duplicated the handle, it has to be closed at the end
                to_close.add(c2pwrite)
                if stdout == PIPE:
                    to_close.add(c2pread)

                if stderr is None:
                    errwrite = _subprocess.GetStdHandle(_subprocess.STD_ERROR_HANDLE)
                    if errwrite is None:
                        _, errwrite = _subprocess.CreatePipe(None, 0)
                elif stderr == PIPE:
                    errread, errwrite = _subprocess.CreatePipe(None, 0)
                elif stderr == STDOUT:
                    errwrite = c2pwrite
                elif isinstance(stderr, int):
                    errwrite = msvcrt.get_osfhandle(stderr)
                else:
                    # Assuming file-like object
                    if not hasattr(stderr, '_sock'):
                        errwrite = msvcrt.get_osfhandle(stderr.fileno())
                    else:
                        errwrite = stderr.fileno()
                errwrite = self._make_inheritable(errwrite)
                # We just duplicated the handle, it has to be closed at the end
                to_close.add(errwrite)
                if stderr == PIPE:
                    to_close.add(errread)

                return (p2cread, p2cwrite,
                        c2pread, c2pwrite,
                        errread, errwrite), to_close
        else:
            def _get_handles(self, stdin, stdout, stderr):
                """Construct and return tuple with IO objects:
                p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
                """
                if stdin is None and stdout is None and stderr is None:
                    return (-1, -1, -1, -1, -1, -1)

                p2cread, p2cwrite = -1, -1
                c2pread, c2pwrite = -1, -1
                errread, errwrite = -1, -1

                if stdin is None:
                    p2cread = _winapi.GetStdHandle(_winapi.STD_INPUT_HANDLE)
                    if p2cread is None:
                        p2cread, _ = _winapi.CreatePipe(None, 0)
                        p2cread = subprocess.Handle(p2cread)
                        _winapi.CloseHandle(_)
                elif stdin == PIPE:
                    p2cread, p2cwrite = _winapi.CreatePipe(None, 0)
                    p2cread, p2cwrite = subprocess.Handle(p2cread), subprocess.Handle(p2cwrite)
                elif stdin == DEVNULL:
                    p2cread = msvcrt.get_osfhandle(self._get_devnull())
                elif isinstance(stdin, int):
                    p2cread = msvcrt.get_osfhandle(stdin)
                else:
                    # Assuming file-like object
                    if not hasattr(stdin, '_sock'):
                        p2cread = msvcrt.get_osfhandle(stdin.fileno())
                    else:
                        p2cread = stdin.fileno()
                p2cread = self._make_inheritable(p2cread)

                if stdout is None:
                    c2pwrite = _winapi.GetStdHandle(_winapi.STD_OUTPUT_HANDLE)
                    if c2pwrite is None:
                        _, c2pwrite = _winapi.CreatePipe(None, 0)
                        c2pwrite = subprocess.Handle(c2pwrite)
                        _winapi.CloseHandle(_)
                elif stdout == PIPE:
                    c2pread, c2pwrite = _winapi.CreatePipe(None, 0)
                    c2pread, c2pwrite = subprocess.Handle(c2pread), subprocess.Handle(c2pwrite)
                elif stdout == DEVNULL:
                    c2pwrite = msvcrt.get_osfhandle(self._get_devnull())
                elif isinstance(stdout, int):
                    c2pwrite = msvcrt.get_osfhandle(stdout)
                else:
                    # Assuming file-like object
                    if not hasattr(stdout, '_sock'):
                        c2pwrite = msvcrt.get_osfhandle(stdout.fileno())
                    else:
                        c2pwrite = stdout.fileno()
                c2pwrite = self._make_inheritable(c2pwrite)

                if stderr is None:
                    errwrite = _winapi.GetStdHandle(_winapi.STD_ERROR_HANDLE)
                    if errwrite is None:
                        _, errwrite = _winapi.CreatePipe(None, 0)
                        errwrite = subprocess.Handle(errwrite)
                        _winapi.CloseHandle(_)
                elif stderr == PIPE:
                    errread, errwrite = _winapi.CreatePipe(None, 0)
                    errread, errwrite = subprocess.Handle(errread), subprocess.Handle(errwrite)
                elif stderr == STDOUT:
                    errwrite = c2pwrite
                elif stderr == DEVNULL:
                    errwrite = msvcrt.get_osfhandle(self._get_devnull())
                elif isinstance(stderr, int):
                    errwrite = msvcrt.get_osfhandle(stderr)
                else:
                    # Assuming file-like object
                    if not hasattr(stderr, '_sock'):
                        errwrite = msvcrt.get_osfhandle(stderr.fileno())
                    else:
                        errwrite = stderr.fileno()
                errwrite = self._make_inheritable(errwrite)

                return (p2cread, p2cwrite,
                        c2pread, c2pwrite,
                        errread, errwrite)

    subprocess.Popen_old = subprocess.Popen
    subprocess.Popen = WindowsPopen

    def disable_overlapped():
        # Enable socket to be non overlapped
        try:
            dummy = socket.socket(0xDEAD, socket.SOCK_STREAM)  # After that python will not force WSA_FLAG_OVERLAPPED
        except:
            pass
        dummy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dummy.setsockopt(socket.SOL_SOCKET, SO_OPENTYPE, SO_SYNCHRONOUS_NONALERT)

    def enable_overlapped():
        dummy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dummy.setsockopt(socket.SOL_SOCKET, SO_OPENTYPE, SO_SYNCHRONOUS_ALERT)

else:
    def disable_overlapped():
        pass

    def enable_overlapped():
        pass