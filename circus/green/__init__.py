from circus import ArbiterHandler as _ArbiterHandler


class ArbiterHandler(_ArbiterHandler):
    def __call__(self, watchers, **kwargs):
        return super(ArbiterHandler, self).__call__(watchers, **kwargs)

    def _get_arbiter_klass(self, background):
        if background:
            raise NotImplementedError
        else:
            from circus.green.arbiter import Arbiter   # NOQA
        return Arbiter


get_arbiter = ArbiterHandler()
