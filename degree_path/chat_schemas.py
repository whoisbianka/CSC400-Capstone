from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class KeywordAddition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    keyword_id: int = Field(ge=1)
    evidence: list[str] = Field(min_length=1)


class ExploreSearch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    majors: list[str] = Field(default_factory=list, max_length=10)
    major_subjects: list[str] = Field(default_factory=list, max_length=10)
    states: list[str] = Field(default_factory=list, max_length=60)
    colleges: list[str] = Field(default_factory=list, max_length=10)
    degree_levels: list[Literal["associate", "bachelor"]] = Field(default_factory=list)
    school_size: Literal["small", "medium", "large"] | None = None
    net_price_max: int | None = Field(default=None, ge=0, le=2147483647)
    tuition_in_max: int | None = Field(default=None, ge=0, le=2147483647)
    tuition_out_max: int | None = Field(default=None, ge=0, le=2147483647)


class AdvisorTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    reply: str = Field(min_length=1,max_length=4000)
    keyword_additions: list[KeywordAddition]
    keyword_removals: list[int]
    major_mentions: list[str]
    explore_search: ExploreSearch | None = None

class GeminiKeywordAddition(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )

    keyword: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class GeminiAdvisorTurn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )

    reply: str = Field(min_length=1, max_length=4000)
    keyword_additions: list[GeminiKeywordAddition]
    keyword_removals: list[str]
    major_mentions: list[str]
    search_requested: bool = False
    explore_search: ExploreSearch | None = None
