from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from bson import ObjectId
from pydantic import BaseModel
from controllers.verbatim_controller import VerbatimController
from models.models import Verbatim, Status
from auth import get_current_user

# Définir un routeur FastAPI
router = APIRouter()


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
    user: dict = Depends(get_current_user),
):
    
    try:
        query = {}
        if year:
            # Check if the year is valid
            if year < 0:
                raise HTTPException(
                    status_code=400, detail=f"Invalid year: {year}"
                )
            query["year"] = year
        if status:
            # Check if the status is valid
            if status not in [s.value for s in Status]:
                raise HTTPException(
                    status_code=400, detail=f"Invalid status: {status}"
                )
            query["status"] = status
        if created_at:
            # Check if the date is valid
            query["created_at"] = created_at
        return await controller.get_verbatims(
            query, pagination=page, per_page=pagination
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Pydantic model for the request body
class DeleteVerbatimsRequest(BaseModel):
    ids: List[str]


# Endpoint pour supprimer un ou plusieurs verbatims
@router.delete("/delete")
async def delete_verbatims(
    request: DeleteVerbatimsRequest,
    user: dict = Depends(get_current_user),
):
    try:
        # Validate each ID
        invalid_ids = [id for id in request.ids if not ObjectId.is_valid(id)]
        if invalid_ids:
            raise HTTPException(
                status_code=400, detail=f"Invalid ObjectId(s): {', '.join(invalid_ids)}"
            )

        # Perform the deletion
        deleted_count = await controller.delete_verbatims(request.ids)
        return {"message": f"{deleted_count} verbatims supprimés."}
    except HTTPException as e:
        raise e  # Re-raise validation errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
