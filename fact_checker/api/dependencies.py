from fastapi import Request

from fact_checker.pipeline import FactCheckPipeline


def get_pipeline(request: Request) -> FactCheckPipeline:
    return request.app.state.pipeline  # type: ignore[no-any-return]
