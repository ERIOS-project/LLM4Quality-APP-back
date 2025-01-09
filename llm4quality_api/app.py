from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from routes.routes import router
from threading import Thread
import asyncio
import json
from config.config import Config
from pydantic_settings import BaseSettings
from controllers.verbatim_controller import VerbatimController
from models.models import Status,Result,Verbatim
from fastapi.logger import logger
from utils.utils import publish_message, consume_messages
from io import StringIO
from auth import get_current_user

from dotenv import load_dotenv

# Initialize FastAPI application

class Settings(BaseSettings):
    APP_CLIENT_ID: str = ""
    TENANT_ID: str = ""
    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    AUTHORITY: str = ""
    API_SCOPE : str = ""
    SCOPE_DESCRIPTION: str = "user_impersonation"

    # @computed_field
    @property
    def SCOPE_NAME(self) -> str:
        return f'api://{self.APP_CLIENT_ID}/{self.SCOPE_DESCRIPTION}'

    # @computed_field
    @property
    def SCOPES(self) -> dict:
        return {
            self.SCOPE_NAME: self.SCOPE_DESCRIPTION,
        }

    # @computed_field
    @property
    def OPENAPI_AUTHORIZATION_URL(self) -> str:
        return f"https://login.microsoftonline.com/{self.TENANT_ID}/oauth2/v2.0/authorize"

    # @computed_field
    @property
    def OPENAPI_TOKEN_URL(self) -> str:
        return f"https://login.microsoftonline.com/{self.TENANT_ID}/oauth2/v2.0/token"

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True

settings = Settings()


async def lifespan(app: FastAPI):
    # Perform startup tasks
    await azure_scheme.openid_config.load_config()

    # Start the message consumer thread
    consumer_thread = Thread(
        target=consume_messages,
        args=("worker_responses", handle_worker_response),
        daemon=True,
    )
    consumer_thread.start()

    yield

    # Perform shutdown tasks if necessary
    # For example, join the consumer thread if it's not daemonized
    # consumer_thread.join()

app = FastAPI(
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url='/oauth2-redirect',
    swagger_ui_init_oauth={
        'usePkceWithAuthorizationCodeGrant': True,
        'clientId': settings.APP_CLIENT_ID,
        'scopes': settings.SCOPE_NAME,
    },
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=settings.APP_CLIENT_ID,
    tenant_id=settings.TENANT_ID,
    scopes=settings.SCOPES,
)

# Include API routes
app.include_router(router)

# Controller instance for MongoDB operations
controller = VerbatimController()

# Set of active WebSocket connections
connected_clients = set()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for managing live client connections.

    Args:
        websocket (WebSocket): WebSocket instance.
    """
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON format"})

            if not isinstance(parsed_data, dict):
                await websocket.send_json({"error": "Message must be a JSON object"})

            if "action" not in parsed_data or not isinstance(parsed_data["action"], str):
                await websocket.send_json({"error": "Missing or invalid 'action' field"})

            if "file" in parsed_data and not isinstance(parsed_data["file"], (str, bytes)):
                await websocket.send_json(
                    {"error": "Invalid 'file' field, must be a string or bytes"}
                )

            if "verbatims" in parsed_data:
                if not isinstance(parsed_data["verbatims"], list) or not all(
                    isinstance(v, dict) for v in parsed_data["verbatims"]
                ):
                    await websocket.send_json(
                        {"error": "Invalid 'verbatims' field, must be a list of objects"}
                    )

            action = parsed_data["action"]

            if action == "CSV" and "file" in parsed_data:
                logger.info(f"Gonna process CSV file")
                await handle_csv_action(websocket, parsed_data["file"])
            elif action == "RERUN" and "verbatims" in parsed_data:
                await handle_rerun_action(websocket, parsed_data["verbatims"])
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected: {websocket.client}")


# TODO : REFACTOR TO CONTROLLER
async def handle_csv_action(websocket: WebSocket, csv_file: str):
    """
    Handle CSV action: process CSV content and publish jobs to RabbitMQ.

    Args:
        websocket (WebSocket): WebSocket instance.
        csv_file (str): CSV file content as a string.
    """
    try:
        # Split CSV lines and create verbatims
        lines = StringIO(csv_file).readlines()
        year = 2024  # Example, adjust based on your requirements
        verbatims = await controller.create_verbatims(lines, year)

        # Publish each verbatim as a job to RabbitMQ
        for verbatim in verbatims:
            publish_message("worker_requests", verbatim.model_dump_json())

        await websocket.send_json({"status": "CSV processed", "count": len(verbatims)})
        for verbatim in verbatims:
            await websocket.send_json(verbatim.model_dump_json())
    except Exception as e:
        logger.error(f"Error processing CSV action: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})


# TODO : REFACTOR TO CONTROLLER
async def handle_rerun_action(websocket: WebSocket, verbatims: list[dict]):
    """
    Handle RERUN action: publish each verbatim as a job to RabbitMQ.

    Args:
        websocket (WebSocket): WebSocket instance.
        verbatims (list): List of verbatim dictionaries.
    """
    try:
        existing_verbatims = []
        non_existing_verbatims = []

        for verbatim_data in verbatims:
            try:
                # Initialize the verbatim model
                verbatim = Verbatim(**verbatim_data)

                # Check if the verbatim exists in the database
                if await controller.find_verbatim_by_id(verbatim.id):
                    existing_verbatims.append(verbatim)
                else:
                    non_existing_verbatims.append(verbatim.model_dump())
            except Exception as e:
                logger.error(
                    f"Error processing verbatim data: {verbatim_data}. Error: {e}"
                )
                non_existing_verbatims.append(verbatim_data)

        # Publish only existing verbatims
        for verbatim in existing_verbatims:
            # Update the status to 'RUN' before publishing
            res = await controller.update_verbatim_status(
                verbatim_id=verbatim.id, status=Status.RUN, result=None
            )
            if res.modified_count > 0:
                logger.info(
                    f"Updated verbatim {verbatim.id} with status {verbatim.status}"
                )
            else:
                if res.matched_count > 0:
                    logger.error(f"Nothing to update verbatim {verbatim.id}")
                else:
                    logger.error(f"Error verbatim {verbatim.id} not found")
            publish_message("worker_requests", verbatim.model_dump_json())

        # Send the response back to WebSocket
        response = {
            "status": "RERUN initiated",
            "published_count": len(existing_verbatims),
            "non_existing_count": len(non_existing_verbatims),
            "non_existing_verbatims": non_existing_verbatims,
        }
        await websocket.send_json(response)

        # Send each verbatim to WebSocket
        for verbatim in existing_verbatims:
            verbatim.status = Status.RUN
            await websocket.send_json(verbatim.model_dump_json())
    except Exception as e:
        logger.error(f"Error processing RERUN action: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})


def handle_worker_response(channel, method, properties, body):
    """
    Process RabbitMQ worker response and update MongoDB.

    Args:
        channel: RabbitMQ channel.
        method: RabbitMQ method frame.
        properties: RabbitMQ properties.
        body (bytes): The message body.
    """
    async def process_response():
        try:
            logger.info(f"Received worker body : {body}")
            # Decode the RabbitMQ message
            message = json.loads(body)
            logger.info(f"Received worker message (parsed in json) : {message}")
            verbatim_id = message["id"]
            logger.info(f"Received worker response for verbatim : : {message}")
            # Convert 'result' en objet Pydantic Result s'il existe
            result_data = message.get("result")
            result = Result(**result_data) if result_data else None

            # Get the Status from the verbatim
            verbatim_status = Status(message["status"])

            # Mettre à jour MongoDB avec le nouveau statut et le résultat
            update_success = await controller.update_verbatim_status(
                verbatim_id=verbatim_id,
                status=verbatim_status,
                result=result,  # Passer l'objet Pydantic
            )
            if update_success.modified_count > 0:
                logger.info(f"Updated verbatim {verbatim_id} with status {verbatim_status}")
            else:
                if update_success.matched_count > 0:
                    logger.error(f"Nothing to update verbatim {verbatim_id}")
                else:
                    logger.error(f"Error verbatim {verbatim_id} not found")
            # Notifier tous les clients WebSocket connectés
            for websocket in connected_clients:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")
                    connected_clients.remove(websocket)
        except Exception as e:
            logger.error(f"Error processing worker response: {e}")

    # Run the coroutine in an event loop
    try:
        asyncio.run(process_response())
    except RuntimeError as e:
        # If an event loop is already running, use ensure_future
        loop = asyncio.get_event_loop()
        loop.create_task(process_response())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(Config.PORT))
