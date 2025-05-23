import asyncio
from functools import wraps
from typing import Callable, Any, TypeVar, Coroutine

T = TypeVar('T')

def run_in_threadpool(func: Callable[..., T]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to run a synchronous function in a thread pool.
    
    This is useful for running blocking I/O operations (like SQLAlchemy database queries)
    without blocking the event loop.
    
    Args:
        func: The synchronous function to run in a thread pool
        
    Returns:
        An async function that runs the original function in a thread pool
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: func(*args, **kwargs)
        )
    return wrapper

# Example usage:
# 
# @run_in_threadpool
# def get_user_from_db(user_id: int):
#     # This is a blocking operation
#     return db.query(User).filter(User.id == user_id).first()
# 
# async def get_user(user_id: int):
#     # This won't block the event loop
#     user = await get_user_from_db(user_id)
#     return user