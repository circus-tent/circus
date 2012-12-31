
from circus.plugins.statsd import BaseObserver
try:
    from tornado.httpclient import AsyncHTTPClient
except ImportError:
    raise ImportError("This plugin requires tornado-framework to run.")


class HttpObserver(BaseObserver):

    name = 'http_observer'
    default_app_name = "http_observer"

    def __init__(self, *args, **config):
        super(HttpObserver, self).__init__(*args, **config)
        self.http_client = AsyncHTTPClient(io_loop=self.loop)
        self.check_url = config.get("check_url", "http://localhost/")
        self.timeout = float(config.get("timeout", 10))

        self.restart_on_error = config.get("restart_on_error", None)

    def look_after(self):

        def handle_response(response, *args, **kwargs):
            if response.error:
                self.statsd.increment("http_stats.error")
                self.statsd.increment("http_stats.error.%s" % response.code)
                if self.restart_on_error:
                    self.cast("restart", name=self.restart_on_error)
                    self.statsd.increment("http_stats.restart_on_error")
                return

            self.statsd.timed("http_stats.request_time",
                              int(response.request_time * 1000))

        self.http_client.fetch(self.check_url, handle_response,
                               request_timeout=self.timeout)
