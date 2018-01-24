from . bot import Bot


async def empty_func():
    pass


class MockBot(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__("test_token", args, kwargs)
        self.calls = {}

    def api_call(self, method, **params):
        self.calls[method] = params
        return empty_func()

