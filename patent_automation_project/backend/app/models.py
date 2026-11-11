from pydantic import BaseModel, Field
from typing import Any

class FeatureExtraction(BaseModel):
    invention_title: str = ""
    technical_domain: str = ""
    problem: str = ""
    proposed_solution: str = ""
    key_features: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    synonyms: dict[str, list[str]] = Field(default_factory=dict)

class AnalysisResult(BaseModel):
    features: FeatureExtraction
    search_queries: list[str] = Field(default_factory=list)

class JobStatus(BaseModel):
    job_id: str
    status: str
    original_filename: str
    artifacts: dict[str, Any] = Field(default_factory=dict)
