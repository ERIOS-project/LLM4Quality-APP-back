from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from controllers.verbatim_controller import VerbatimController

# Définir un routeur FastAPI
router = APIRouter()


# Modèle pour le Verbatim (entrée/sortie)
class Verbatim(BaseModel):
    id: Optional[str] = None
    status: str
    content: str
    year: int
    result: Optional[dict] = None


# Instanciation du contrôleur
controller = VerbatimController()


# Endpoint pour récupérer les verbatims
@router.get("/get", response_model=List[Verbatim])
async def get_verbatims(
    pagination: int = Query(default=10, description="Nombre d'éléments par page"),
    page: int = Query(default=1, description="Numéro de la page"),
    year: Optional[int] = Query(None, description="Filtrer par année"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    created_at: Optional[str] = Query(None, description="Filtrer par date de création"),
):
    query = {}
    if year:
        query["year"] = year
    if status:
        query["status"] = status
    if created_at:
        query["created_at"] = created_at

    try:
        return await controller.get_verbatims(
            query, pagination=page, per_page=pagination
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint pour supprimer un ou plusieurs verbatims
@router.delete("/delete")
async def delete_verbatims(ids: List[str]):
    try:
        deleted_count = await controller.delete_verbatims(ids)
        return {"message": f"{deleted_count} verbatims supprimés."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
