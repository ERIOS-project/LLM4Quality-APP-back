from pymongo import MongoClient
from bson import ObjectId
from models.models import Verbatim, Result, Status
from config.config import Config
from datetime import datetime, timezone
from typing import List, Optional


class VerbatimController:
    def __init__(self):
        client = MongoClient(Config.MONGO_URI)
        self.collection = client.llm4quality.verbatims

    async def create_verbatims(self, lines: List[str], year: int) -> List[Verbatim]:
        """
        Create verbatims in MongoDB.

        Args:
            lines (List[str]): Lines of content for the verbatims.
            year (int): Year associated with the verbatims.

        Returns:
            List[Verbatim]: The created verbatims.
        """
        verbatim_dicts = [
            {
                "content": line.strip(),
                "status": Status.RUN.value,  # Convert enum to string
                "result": None,
                "year": year,
                "created_at": datetime.now(timezone.utc),
            }
            for line in lines
        ]

        # Insert documents into MongoDB
        result = self.collection.insert_many(verbatim_dicts)

        # Fetch inserted documents to include `_id` and `created_at`
        inserted_verbatims = [
            Verbatim.from_dict(self.collection.find_one({"_id": oid}))
            for oid in result.inserted_ids
        ]
        return inserted_verbatims

    async def get_verbatims(
        self, query: dict, pagination: int = 1, per_page: int = 10
    ) -> List[Verbatim]:
        """
        Retrieve verbatims based on a query with pagination.

        Args:
            query (dict): MongoDB query filter.
            pagination (int): Page number (default is 1).
            per_page (int): Results per page (default is 10).

        Returns:
            List[Verbatim]: The retrieved verbatims.
        """
        skip = (pagination - 1) * per_page
        results = self.collection.find(query).skip(skip).limit(per_page)
        return [Verbatim.from_dict(v) for v in results]

    async def delete_verbatims(self, verbatim_ids: List[str]) -> int:
        """
        Delete multiple verbatims by their IDs.

        Args:
            verbatim_ids (List[str]): List of verbatim IDs to delete.

        Returns:
            int: Number of documents deleted.
        """
        object_ids = [ObjectId(vid) for vid in verbatim_ids]
        result = self.collection.delete_many({"_id": {"$in": object_ids}})
        return result.deleted_count

    async def update_verbatim_status(
        self, verbatim_id: str, status: Status, result: Optional[Result | dict]
    ) -> dict:
        """
        Update the status and result of a verbatim in MongoDB.

        Args:
            verbatim_id (str): ID of the verbatim to update.
            status (Status): New status for the verbatim.
            result (Optional[Result | dict]): Updated result for the verbatim.

        Returns:
            bool: True if the update succeeded, False otherwise.
        """
        update_data = {"status": status.value}  # Convert enum to string
        if result:
            update_data["result"] = (
                result.dict() if isinstance(result, Result) else result
            )

        # Update document in MongoDB
        update_result = self.collection.update_one(
            {"_id": ObjectId(verbatim_id)},
            {"$set": update_data},
        )

        return update_result

    async def find_verbatim_by_id(self, verbatim_id: str) -> Optional[Verbatim]:
        """
        Retrieve a single verbatim by its ID.

        Args:
            verbatim_id (str): ID of the verbatim to retrieve.

        Returns:
            Optional[Verbatim]: The retrieved verbatim object or None.
        """
        document = self.collection.find_one({"_id": ObjectId(verbatim_id)})
        return Verbatim.from_dict(document) if document else None
    
    async def get_collection_count(self) -> dict:
        """
        Get the total number of documents in the verbatims collection.

        Returns:
            dict: -total: Total number of documents.
                    -total_run : Total number of documents with status RUN.
                    -total_success : Total number of documents with status SUCCESS.
                    -total_error : Total number of documents with status ERROR.
        """
        total = self.collection.count_documents({})
        total_run = self.collection.count_documents({"status": Status.RUN.value})
        total_success = self.collection.count_documents({"status": Status.SUCCESS.value})
        total_error = self.collection.count_documents({"status": Status.ERROR.value})
        return {
            "total": total,
            "total_run": total_run,
            "total_success": total_success,
            "total_error": total_error,
        }
