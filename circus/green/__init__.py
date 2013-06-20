from circus import get_arbiter_handler as _get_arbiter_handler


class get_arbiter_handler(_get_arbiter_handler):
    def __call__(self, watchers, **kwargs):
        return super(get_arbiter_handler, self).__call__(watchers, **kwargs)

    def _get_arbiter_klass(self, background):
        if background:
            raise NotImplementedError
        else:
            from circus.green.arbiter import Arbiter   # NOQA
        return Arbiter


get_arbiter = get_arbiter_handler()
