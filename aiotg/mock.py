from . bot import Bot


class MockBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__("test_token", args, kwargs)
        self.calls = {}

    def api_call(self, method, **params):
        self.calls[method] = params
