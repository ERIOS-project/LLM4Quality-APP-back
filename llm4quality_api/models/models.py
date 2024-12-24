from typing import Optional, Dict
from pydantic import BaseModel, Field, field_serializer
from bson import ObjectId
from datetime import datetime
from enum import Enum


# Enum for status
class Status(str, Enum):
    RUN = "RUN"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class Result(BaseModel):
    circuit_de_prise_en_charge: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    professionnalisme_de_l_equipe: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    qualite_hoteliere: Dict[str, Dict[str, int]] = Field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create a Result instance from a dictionary.
        """
        return cls(**data)

    def to_dict(self) -> dict:
        """
        Convert the Result instance to a dictionary.
        """
        return self.model_dump()


# Custom type for MongoDB ObjectId
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class Verbatim(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    content: str
    status: Status 
    result: Optional[Result]
    year: int
    created_at: Optional[datetime]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        populate_by_name = True

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize `created_at` to an ISO 8601 string."""
        return value.isoformat() if value else None

    @classmethod
    def from_dict(cls, data: dict):
        """Create a Verbatim instance from a dictionary."""
        return cls(
            id=str(data.get("_id")) if data.get("_id") else None,
            content=data["content"],
            status=data["status"],
            result=data.get("result"),
            year=data["year"],
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        """Convert the Verbatim instance to a dictionary."""
        doc = self.model_dump(by_alias=True, exclude_unset=True)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
