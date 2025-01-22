import asyncio
import json
from llm4quality_api.models.models import Result, Status
from llm4quality_api.controllers.verbatim_controller import VerbatimController
from llm4quality_api.utils.logger import Logger
from llm4quality_api.routes.routes import connected_clients

# Logger instance
logger = Logger.get_instance().get_logger()

# Controller instance
controller = VerbatimController()

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
                logger.info(
                    f"Updated verbatim {verbatim_id} with status {verbatim_status}"
                )
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
