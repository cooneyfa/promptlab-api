"""Request/response models for the PromptLab API."""

from pydantic import BaseModel, Field


class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    template: str = Field(..., min_length=1, max_length=8000)
    description: str = Field(default="", max_length=500)


class PromptUpdate(BaseModel):
    template: str = Field(..., min_length=1, max_length=8000)
    description: str = Field(default="", max_length=500)


class PromptOut(BaseModel):
    id: int
    name: str
    version: int
    template: str
    description: str
    created_at: str


class PromptVersionOut(BaseModel):
    version: int
    template: str
    description: str
    created_at: str


class RenderRequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)


class RenderOut(BaseModel):
    id: int
    name: str
    version: int
    rendered: str


class EvaluateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)


class EvaluateOut(BaseModel):
    scores: dict[str, float]
    overall: float
    notes: list[str]
