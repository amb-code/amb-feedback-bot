import random
from unittest.mock import MagicMock


class AsyncContextManagerWrapper:
    def __init__(self, for_obj):
        self._obj = for_obj

    async def __aenter__(self):
        return self._obj

    async def __aexit__(self, exc_type, exc, traceback):
        pass


class AsyncSessionMock:
    def __init__(self, session_mock):
        self._session = session_mock

    def add(self, *args, **kwargs):

        for obj in args:
            if obj.id == None:
                obj.id = random.randint(1000000, 9999999)

        self._session.add(*args, **kwargs)
        self._session.commit()

    async def get(self, *args, **kwargs):
        return self._session.get(*args, **kwargs)

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def commit(self, *args, **kwargs):
        return self._session.commit(*args, **kwargs)

    begin = MagicMock()
