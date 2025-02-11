from fastapi import APIRouter,WebSocket,WebSocketDisconnect,WebSocketException, HTTPException, Query, Depends
from typing import List, Optional
from bson import ObjectId
import json
from pydantic import BaseModel
from llm4quality_api.controllers.verbatim_controller import VerbatimController
from llm4quality_api.models.models import Verbatim, Status
from llm4quality_api.utils.logger import Logger
from llm4quality_api.auth import get_current_user
from llm4quality_api.services.verbatims import handle_csv_action, handle_rerun_action

# Définir un routeur FastAPI
router = APIRouter()

# Logger instance
logger = Logger.get_instance().get_logger()

# Set of active WebSocket connections
connected_clients = set()

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

# Endpoint pour obtenir les informations de count de la collection
@router.get("/count")
async def get_count(user: dict = Depends(get_current_user)):
    try:
        return await controller.get_collection_count()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for managing live client connections.

    Args:
        websocket (WebSocket): WebSocket instance.
    """
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"WebSocket client connected: {websocket.client}")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})

            if not isinstance(parsed_data, dict):
                await websocket.send_json({"error": "Message must be a JSON object"})

            if "action" not in parsed_data or not isinstance(
                parsed_data["action"], str
            ):
                await websocket.send_json(
                    {"error": "Missing or invalid 'action' field"}
                )

            if "file" in parsed_data and not isinstance(
                parsed_data["file"], (str, bytes)
            ):
                await websocket.send_json(
                    {"error": "Invalid 'file' field, must be a string or bytes"}
                )

            if "verbatims" in parsed_data:
                if not isinstance(parsed_data["verbatims"], list) or not all(
                    isinstance(v, dict) for v in parsed_data["verbatims"]
                ):
                    await websocket.send_json(
                        {
                            "error": "Invalid 'verbatims' field, must be a list of objects"
                        }
                    )

            if "year" in parsed_data and not isinstance(parsed_data["year"], int):
                await websocket.send_json(
                    {"error": "Invalid 'year' field, must be an integer"}
                )

            action = parsed_data["action"]

            if action == "CSV" and "file" in parsed_data:
                logger.info(f"Gonna process CSV file")
                await handle_csv_action(
                    websocket, parsed_data["file"], parsed_data["year"]
                )
            elif action == "RERUN" and "verbatims" in parsed_data:
                await handle_rerun_action(websocket, parsed_data["verbatims"])
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected: {websocket.client}")
