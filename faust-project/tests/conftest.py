import sys
import types
import asyncio
import importlib
import importlib.util
import importlib.machinery
import importlib.abc


_orig_Event = asyncio.Event
_orig_Lock = asyncio.Lock
_orig_Semaphore = asyncio.Semaphore
_orig_Condition = asyncio.Condition
_orig_Queue = asyncio.Queue
_orig_PriorityQueue = getattr(asyncio, 'PriorityQueue', None)
_orig_LifoQueue = getattr(asyncio, 'LifoQueue', None)
_orig_sleep = asyncio.sleep
_orig_wait = asyncio.wait
_orig_gather = asyncio.gather
_orig_wait_for = asyncio.wait_for
_orig_shield = asyncio.shield


def _sleep_compat(*args, **kwargs):
    kwargs.pop('loop', None)
    return _orig_sleep(*args, **kwargs)


def _wait_compat(*args, **kwargs):
    kwargs.pop('loop', None)
    return _orig_wait(*args, **kwargs)


def _gather_compat(*args, **kwargs):
    kwargs.pop('loop', None)
    return _orig_gather(*args, **kwargs)


def _wait_for_compat(*args, **kwargs):
    kwargs.pop('loop', None)
    return _orig_wait_for(*args, **kwargs)


def _shield_compat(*args, **kwargs):
    kwargs.pop('loop', None)
    return _orig_shield(*args, **kwargs)


asyncio.sleep = _sleep_compat
asyncio.wait = _wait_compat
asyncio.gather = _gather_compat
asyncio.wait_for = _wait_for_compat
asyncio.shield = _shield_compat


class _EventCompat(_orig_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('loop', None)
        super().__init__(*args, **kwargs)


class _LockCompat(_orig_Lock):
    def __init__(self, *args, **kwargs):
        kwargs.pop('loop', None)
        super().__init__(*args, **kwargs)


class _SemaphoreCompat(_orig_Semaphore):
    def __init__(self, *args, **kwargs):
        kwargs.pop('loop', None)
        super().__init__(*args, **kwargs)


class _ConditionCompat(_orig_Condition):
    def __init__(self, *args, **kwargs):
        kwargs.pop('loop', None)
        lock = kwargs.get('lock', None)
        if lock is not None:
            kwargs['lock'] = lock
        super().__init__(*args, **kwargs)


class _QueueCompat(_orig_Queue):
    def __init__(self, *args, **kwargs):
        kwargs.pop('loop', None)
        super().__init__(*args, **kwargs)


asyncio.Event = _EventCompat
asyncio.Lock = _LockCompat
asyncio.Semaphore = _SemaphoreCompat
asyncio.Condition = _ConditionCompat
asyncio.Queue = _QueueCompat

if _orig_PriorityQueue is not None:
    class _PriorityQueueCompat(_orig_PriorityQueue):
        def __init__(self, *args, **kwargs):
            kwargs.pop('loop', None)
            super().__init__(*args, **kwargs)
    asyncio.PriorityQueue = _PriorityQueueCompat

if _orig_LifoQueue is not None:
    class _LifoQueueCompat(_orig_LifoQueue):
        def __init__(self, *args, **kwargs):
            kwargs.pop('loop', None)
            super().__init__(*args, **kwargs)
    asyncio.LifoQueue = _LifoQueueCompat

import sys as _sys  # noqa: E402
if hasattr(_sys, 'set_coroutine_origin_tracking_depth'):
    try:
        _sys.set_coroutine_origin_tracking_depth(0)
    except Exception:
        pass


if 'imp' not in sys.modules:
    _imp = types.ModuleType('imp')

    _imp.PY_SOURCE = 1
    _imp.PY_COMPILED = 2
    _imp.C_EXTENSION = 3
    _imp.PKG_DIRECTORY = 5
    _imp.C_BUILTIN = 6
    _imp.PY_FROZEN = 7

    _imp.lock_held = lambda: False
    _imp.acquire_lock = lambda: None
    _imp.release_lock = lambda: None

    def _find_module(name, path=None):
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None:
            raise ImportError(f"No module named {name!r}")
        origin = spec.origin or ''
        suffixes = importlib.machinery.all_suffixes()
        suffix = ''
        ftype = 0
        for s in suffixes:
            if origin.endswith(s):
                suffix = s
                if s in importlib.machinery.SOURCE_SUFFIXES:
                    ftype = _imp.PY_SOURCE
                elif s in importlib.machinery.BYTECODE_SUFFIXES:
                    ftype = _imp.PY_COMPILED
                elif s in importlib.machinery.EXTENSION_SUFFIXES:
                    ftype = _imp.C_EXTENSION
                break
        if spec.submodule_search_locations:
            ftype = _imp.PKG_DIRECTORY
            if spec.origin == 'namespace':
                return None, spec.submodule_search_locations[0], ('', '', _imp.PKG_DIRECTORY)
        return None, origin, (suffix, 'r', ftype) if ftype else None

    _imp.find_module = _find_module

    def _load_module(name, file, filename, details):
        path = None
        if details and details[2] == _imp.PKG_DIRECTORY:
            head = filename.rsplit('/', 1)[0]
            head = head.rsplit('\\', 1)[0]
            path = [head]
        spec = importlib.util.spec_from_file_location(
            name, filename, submodule_search_locations=path
        )
        if spec is None:
            raise ImportError(f"Cannot load module {name!r}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _imp.load_module = _load_module

    def _load_source(name, pathname, file=None):
        spec = importlib.util.spec_from_file_location(name, pathname)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _imp.load_source = _load_source

    _imp.get_magic = lambda: importlib.util.MAGIC_NUMBER
    _imp.get_suffixes = lambda: [
        (s, 'r', _imp.PY_SOURCE) for s in importlib.machinery.SOURCE_SUFFIXES
    ] + [
        (s, 'rb', _imp.PY_COMPILED) for s in importlib.machinery.BYTECODE_SUFFIXES
    ] + [
        (s, 'rb', _imp.C_EXTENSION) for s in importlib.machinery.EXTENSION_SUFFIXES
    ]

    def _get_tags():
        return sys.implementation.cache_tag

    _imp.get_tag = _get_tags

    sys.modules['imp'] = _imp


class _SixMovesLoader(importlib.abc.Loader):
    def create_module(self, spec):
        import six
        return six.moves

    def exec_module(self, module):
        pass


class _SixLoader(importlib.abc.Loader):
    def create_module(self, spec):
        import six
        return six

    def exec_module(self, module):
        pass


class _KafkaVendorSixFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == 'kafka.vendor.six':
            return importlib.machinery.ModuleSpec(fullname, _SixLoader())
        if fullname == 'kafka.vendor.six.moves':
            return importlib.machinery.ModuleSpec(fullname, _SixMovesLoader())
        return None


if not any(
    isinstance(f, _KafkaVendorSixFinder) for f in sys.meta_path
):
    sys.meta_path.insert(0, _KafkaVendorSixFinder())


def _patch_httpx_client_unset():
    try:
        import httpx._client as _httpx_client
        import typing as _typing

        if not hasattr(_httpx_client, 'UNSET'):
            _UNSET_SENTINEL = object()
            _httpx_client.UNSET = _UNSET_SENTINEL

            _UnsetType = type(_UNSET_SENTINEL)
            if not hasattr(_httpx_client, 'UnsetType'):
                _httpx_client.UnsetType = _UnsetType

            if not hasattr(_httpx_client, 'TimeoutTypes'):
                _httpx_client.TimeoutTypes = _typing.Union[
                    _typing.NoneType, float, _UnsetType
                ]
    except Exception:
        pass


_patch_httpx_client_unset()

import pytest as _pytest


@_pytest.fixture()
def event_loop():
    import asyncio as _asyncio
    try:
        loop = _asyncio.get_running_loop()
    except RuntimeError:
        loop = _asyncio.new_event_loop()
    try:
        yield loop
    finally:
        try:
            pending = _asyncio.all_tasks(loop)
            if pending:
                loop.run_until_complete(
                    _asyncio.gather(*pending, return_exceptions=True)
                )
        except Exception:
            pass
        loop.close()
