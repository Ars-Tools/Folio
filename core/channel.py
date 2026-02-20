#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import concurrent.futures
import logging
from typing import Callable, Awaitable, Any

class DispatchQueue:
    def __init__(self, max_workers: int = 1):
        self._queue = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, handler: Callable[..., Any], *args, **kwargs) -> concurrent.futures.Future:
        return self._queue.submit(handler, *args, **kwargs)

    def shutdown(self, wait=True):
        self._queue.shutdown(wait=wait)

class Channel:
    def __init__(self, handler: Callable[..., Awaitable[Any]], max_parallel: int = 1):
        semaphore = asyncio.Semaphore(max_parallel)
        async def task(*args, **kwargs):
            async with semaphore:
                return await handler(*args, **kwargs)
        self._task = task

    def dispatch(self, *args, **kwargs):
        asyncio.create_task(self._task(*args, **kwargs))

if __name__ == "__main__":
    """Example usage of Channel with a simple async handler."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    async def test():
        async def my_handler(task_id):
            logging.info(f"Starting task {task_id}")
            await asyncio.sleep(2)
            logging.info(f"Finished task {task_id}")

        channel = Channel(my_handler, max_parallel=3)

        for i in range(8):
            logging.info(f"Dispatching task {i}")
            channel.dispatch(i)
        
        # Wait for tasks to complete (simple wait for demonstration)
        await asyncio.sleep(8)

    asyncio.run(test())
    