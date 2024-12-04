from bson import ObjectId
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict
import datetime


class Status(str, Enum):
    SUCCESS = "SUCCESS"
    RUN = "RUN"
    ERROR = "ERROR"


class Result(BaseModel):
    circuit: Dict[str, str] = {
        "positive": "",
        "negative": "",
        "neutral": "",
        "not mentioned": "",
    }
    qualite: Dict[str, str] = {
        "positive": "",
        "negative": "",
        "neutral": "",
        "not mentioned": "",
    }
    professionnalisme: Dict[str, str] = {
        "positive": "",
        "negative": "",
        "neutral": "",
        "not mentioned": "",
    }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            circuit=data.get("circuit", cls.__fields__["circuit"].default),
            qualite=data.get("qualite", cls.__fields__["qualite"].default),
            professionnalisme=data.get(
                "professionnalisme", cls.__fields__["professionnalisme"].default
            ),
        )

    def to_dict(self):
        return self.dict()


class Verbatim(BaseModel):
    id: Optional[str] = Field(alias="_id")  # Pour mapper `_id` de MongoDB
    content: str
    status: Status = Status.RUN
    result: Optional[Result] = None
    year: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True
    )  # Permet les types comme datetime et ObjectId

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=str(data.get("_id")) if data.get("_id") else None,
            content=data["content"],
            status=data["status"],
            result=Result.from_dict(data["result"]) if data.get("result") else None,
            year=data["year"],
            created_at=data.get("created_at"),
        )

    def to_dict(self):
        doc = self.dict(by_alias=True, exclude_unset=True)
        # Convertir `id` en `_id` pour MongoDB
        if "id" in doc:
            doc["_id"] = ObjectId(doc.pop("id"))
        return doc
