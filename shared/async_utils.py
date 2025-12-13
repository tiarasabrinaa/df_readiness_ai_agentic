# shared/async_utils.py
import asyncio
import nest_asyncio
from typing import Coroutine, TypeVar

T = TypeVar('T')

def run_async(coro: Coroutine) -> T:
    """
    Helper to run async coroutines in Flask sync context
    
    Args:
        coro: Async coroutine to execute
        
    Returns:
        Result from the coroutine
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Apply nest_asyncio if loop is already running
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)