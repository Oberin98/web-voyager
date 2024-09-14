import asyncio


def patch_asyncio():
    """Patch asyncio to prevent it from throwing warning when the event loop is deleted"""

    _BEL = asyncio.base_events.BaseEventLoop

    _original_del = _BEL.__del__

    def _patched_del(self):
        try:
            # invoke the original method...
            _original_del(self)
        except:
            # ... but ignore any exceptions it might raise
            # NOTE: horrible anti-pattern
            pass

    # replace the original __del__ method
    _BEL.__del__ = _patched_del
