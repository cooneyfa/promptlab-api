"""PromptLab API - FastAPI application."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .evaluate import evaluate
from .models import (
    EvaluateOut,
    EvaluateRequest,
    PromptCreate,
    PromptOut,
    PromptUpdate,
    PromptVersionOut,
    RenderOut,
    RenderRequest,
)
from .store import DuplicateNameError, MissingVariableError, NotFoundError, PromptStore


def create_app(db_path: str | None = None) -> FastAPI:
    store = PromptStore(db_path or os.environ.get("PROMPTLAB_DB", "promptlab.db"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = store
        yield

    app = FastAPI(title="PromptLab API", version="0.1.0", lifespan=lifespan)
    # Lifespan runs on startup; set state eagerly too so TestClient works
    # without an explicit context manager.
    app.state.store = store

    def get_store(request: Request) -> PromptStore:
        return request.app.state.store

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.post("/prompts", response_model=PromptOut, status_code=201)
    def create_prompt(payload: PromptCreate, request: Request):
        try:
            return get_store(request).create(
                payload.name, payload.template, payload.description
            )
        except DuplicateNameError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/prompts", response_model=list[PromptOut])
    def list_prompts(request: Request):
        return get_store(request).list()

    @app.get("/prompts/{prompt_id}", response_model=PromptOut)
    def get_prompt(prompt_id: int, request: Request):
        try:
            return get_store(request).get(prompt_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/prompts/{prompt_id}/versions", response_model=list[PromptVersionOut])
    def get_versions(prompt_id: int, request: Request):
        try:
            return get_store(request).versions(prompt_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.put("/prompts/{prompt_id}", response_model=PromptOut)
    def update_prompt(prompt_id: int, payload: PromptUpdate, request: Request):
        try:
            return get_store(request).update(
                prompt_id, payload.template, payload.description
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/prompts/{prompt_id}", status_code=204)
    def delete_prompt(prompt_id: int, request: Request):
        try:
            get_store(request).delete(prompt_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return JSONResponse(status_code=204, content=None)

    @app.post("/prompts/{prompt_id}/render", response_model=RenderOut)
    def render_prompt(prompt_id: int, payload: RenderRequest, request: Request):
        try:
            return get_store(request).render(prompt_id, payload.variables)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except MissingVariableError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/evaluate", response_model=EvaluateOut)
    def evaluate_text(payload: EvaluateRequest):
        return evaluate(payload.text)

    return app


app = create_app()
