
from pydantic import BaseModel, ConfigDict, Field


class KeywordAddition(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )
    keyword_id: int = Field(ge=1)
    evidence: str = Field(min_length=1)


class CollegeSearchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )

    major: str | None
    state: str | None
    school_size: str | None


class AdvisorTurn(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )

    reply: str = Field(min_length=1, max_length=4000)
    keyword_additions: list[KeywordAddition]
    keyword_removals: list[int]
    major_mentions: list[str]
    college_search: CollegeSearchRequest | None = None


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
    college_search: CollegeSearchRequest | None = None
