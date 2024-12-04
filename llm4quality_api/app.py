from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from routes.routes import router
from threading import Thread
import asyncio
import json
from config.config import Config
from controllers.verbatim_controller import VerbatimController
from models.models import Status
from fastapi.logger import logger
from utils.utils import publish_message, consume_messages
from io import StringIO

# Initialize FastAPI application
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Controller instance for MongoDB operations
controller = VerbatimController()

# Set of active WebSocket connections
connected_clients = set()

# TODO: REMOVE THIS
@app.get("/")
async def read_root():
    """Test route for the API"""
    return {"message": "Hello, World!"}


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
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "CSV" and "file" in data:
                await handle_csv_action(websocket, data["file"])
            elif action == "RERUN" and "verbatims" in data:
                await handle_rerun_action(websocket, data["verbatims"])
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected: {websocket.client}")


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
            publish_message("worker_requests", verbatim.dict())

        await websocket.send_json({"status": "CSV processed", "count": len(verbatims)})
    except Exception as e:
        logger.error(f"Error processing CSV action: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})


async def handle_rerun_action(websocket: WebSocket, verbatims: list[dict]):
    """
    Handle RERUN action: publish each verbatim as a job to RabbitMQ.

    Args:
        websocket (WebSocket): WebSocket instance.
        verbatims (list): List of verbatim dictionaries.
    """
    try:
        for verbatim_data in verbatims:
            publish_message("worker_requests", verbatim_data)

        await websocket.send_json(
            {"status": "RERUN initiated", "count": len(verbatims)}
        )
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
    try:
        # Decode the RabbitMQ message
        message = json.loads(body)
        verbatim_id = message["_id"]

        # Update MongoDB with the new status and result
        update_success = controller.update_verbatim_status(
            verbatim_id=verbatim_id,
            status=Status.SUCCESS,
            result=message["result"],
        )

        if update_success:
            # Notify all connected WebSocket clients
            for websocket in connected_clients:
                try:
                    asyncio.run(websocket.send_json(message))
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")
                    connected_clients.remove(websocket)
        else:
            logger.error(f"Failed to update verbatim with ID: {verbatim_id}")
    except Exception as e:
        logger.error(f"Error processing worker response: {e}")


async def lifespan(app: FastAPI):
    Thread(
        target=consume_messages,
        args=("worker_responses", handle_worker_response),
        daemon=True,
    ).start()
    yield


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(Config.PORT))
