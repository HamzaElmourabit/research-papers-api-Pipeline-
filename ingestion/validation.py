from pydantic import BaseModel, HttpUrl
from typing import List, Dict
from datetime import datetime
from pydantic import ValidationError,field_validator

import logging
logger = logging.getLogger(__name__)

class PaperModel(BaseModel):
    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    categories: List[str]
    primary_category: str
    published_date: datetime
    updated_date: datetime
    pdf_url: HttpUrl
    raw_json: str
    ingested_at: datetime

    @field_validator("arxiv_id", "title", "abstract", "primary_category")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must not be empty or whitespace")
        return v.strip()

    @field_validator("authors", "categories")
    @classmethod
    def must_be_non_empty_list(cls, v: list) -> list:
        if not v:
            raise ValueError("list must contain at least one element")
        return v

    def to_insert_dict(self) -> dict:
        """
        Returns a plain dict safe for Cassandra insertion.
        Converts HttpUrl to str so the driver doesn't receive a Pydantic object.
        """
        data = self.model_dump()
        data["pdf_url"] = str(self.pdf_url)
        return data


def validate_paper( papers: List[Dict]) -> List[dict]:
    valid_papers = []
    for paper in papers:
        try:
            valid_paper = PaperModel(**paper)
            valid_papers.append(valid_paper.to_insert_dict())
        except ValidationError :
            pass
    return valid_papers