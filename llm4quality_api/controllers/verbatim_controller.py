from pymongo import MongoClient
from bson import ObjectId
from models.models import Verbatim, Result, Status
from config.config import Config
from typing import List, Optional


class VerbatimController:
    def __init__(self):
        client = MongoClient(Config.MONGO_URI)
        self.collection = client.llm4quality.verbatims

    async def create_verbatims(self, lines: List[str], year: int) -> List[Verbatim]:
        """
        Crée des verbatims dans MongoDB. MongoDB gère `_id` et `created_at`.

        Args:
            lines (List[str]): Lignes de contenu des verbatims.
            year (int): Année associée aux verbatims.

        Returns:
            List[Verbatim]: Les verbatims créés.
        """
        verbatim_dicts = [
            {
                "content": line.strip(),
                "status": Status.RUN,
                "result": None,
                "year": year,
            }
            for line in lines
        ]

        # Insère plusieurs verbatims à la fois
        result = self.collection.insert_many(verbatim_dicts)

        # Récupère les documents insérés pour inclure `_id` et `created_at`
        inserted_verbatims = [
            self.collection.find_one({"_id": oid}) for oid in result.inserted_ids
        ]
        return [Verbatim.from_dict(v) for v in inserted_verbatims]

    async def get_verbatims(
        self, query: dict, pagination: int = 1, per_page: int = 10
    ) -> List[Verbatim]:
        """
        Récupère les verbatims en fonction d'une requête avec pagination.

        Args:
            query (dict): Filtre de requête pour MongoDB.
            pagination (int): Numéro de page (par défaut 1).
            per_page (int): Nombre de résultats par page (par défaut 10).

        Returns:
            List[Verbatim]: Les verbatims récupérés.
        """
        skip = (pagination - 1) * per_page
        results = self.collection.find(query).skip(skip).limit(per_page)
        return [Verbatim.from_dict(v) for v in results]

    async def delete_verbatims(self, verbatim_ids: List[str]) -> int:
        """
        Supprime plusieurs verbatims par leurs IDs.

        Args:
            verbatim_ids (List[str]): Liste des IDs des verbatims à supprimer.

        Returns:
            int: Nombre de documents supprimés.
        """
        object_ids = [ObjectId(vid) for vid in verbatim_ids]
        result = self.collection.delete_many({"_id": {"$in": object_ids}})
        return result.deleted_count

    async def update_verbatim_status(
        self, verbatim_id: str, status: Status, result: Optional[Result]
    ) -> bool:
        """
        Met à jour le statut et le résultat d'un verbatim dans MongoDB.

        Args:
            verbatim_id (str): ID du verbatim à mettre à jour.
            status (Status): Nouveau statut pour le verbatim (par exemple, "SUCCESS").
            result (Optional[Result]): Résultat mis à jour pour le verbatim, calculé.

        Returns:
            bool: True si la mise à jour a réussi, False sinon.
        """
        update_data = {"status": status}
        if result:
            update_data["result"] = result.dict()

        # Met à jour le document dans MongoDB
        update_result = self.collection.update_one(
            {"_id": ObjectId(verbatim_id)},
            {"$set": update_data},
        )

        return update_result.modified_count > 0

    async def find_verbatim_by_id(self, verbatim_id: str) -> Optional[Verbatim]:
        """
        Récupère un verbatim unique par son ID.

        Args:
            verbatim_id (str): ID du verbatim à récupérer.

        Returns:
            Optional[Verbatim]: L'objet Verbatim récupéré ou None s'il n'existe pas.
        """
        document = self.collection.find_one({"_id": ObjectId(verbatim_id)})
        return Verbatim.from_dict(document) if document else None
