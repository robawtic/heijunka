# application/shared/behaviors/behavior_pipeline.py
from typing import List, Callable, Awaitable, Any

BehaviorFunction = Callable[[Any, Callable[[Any], Awaitable[Any]]], Awaitable[Any]]

class BehaviorPipeline:
    def __init__(self):
        self._behaviors: List[BehaviorFunction] = []

    def add_behavior(self, behavior: BehaviorFunction) -> None:
        self._behaviors.append(behavior)

    async def execute(self, request: Any, handler: Any) -> Any:
        if not self._behaviors:
            return await handler.handle(request)

        # Build behavior pipeline
        async def execute_handler(req):
            return await handler.handle(req)

        # Apply behaviors in reverse order
        pipeline = execute_handler
        for behavior in reversed(self._behaviors):
            current_pipeline = pipeline

            def create_pipeline_step(behavior_func, next_pipeline):
                async def pipeline_step(req):
                    return await behavior_func(req, next_pipeline)
                return pipeline_step

            pipeline = create_pipeline_step(behavior, current_pipeline)

        return await pipeline(request)