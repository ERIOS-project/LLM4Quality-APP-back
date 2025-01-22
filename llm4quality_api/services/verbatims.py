import base64
from fastapi import WebSocket
from llm4quality_api.models.models import Verbatim, Status
from llm4quality_api.controllers.verbatim_controller import VerbatimController
from llm4quality_api.utils.broker import publish_message
from llm4quality_api.utils.logger import Logger


# Logger instance
logger = Logger.get_instance().get_logger()

# Controller instance
controller = VerbatimController()


async def handle_csv_action(websocket: WebSocket, csv_file: str, year: int):
    """
    Handle CSV action: process CSV content and publish jobs to RabbitMQ.

    Args:
        websocket (WebSocket): WebSocket instance.
        csv_file (bytes): CSV file content as base64 string.
    """
    try:
        # Decode base64 to bytes
        csv_file_bytes = base64.b64decode(csv_file)

        # Decode bytes to string and split into lines
        csv_content = csv_file_bytes.decode("utf-8")
        lines = csv_content.splitlines()

        logger.info(f"Processing CSV with {len(lines)} lines")
        # Remove empty lines and header if needed
        lines = [line for line in lines if line.strip()]

        verbatims = await controller.create_verbatims(lines, year)

        logger.info(f"Publishing {len(verbatims)} verbatims to workers queue")
        # Publish each verbatim as a job to RabbitMQ
        for verbatim in verbatims:
            publish_message("worker_requests", verbatim.model_dump_json())

        await websocket.send_json({"status": "CSV processed", "count": len(verbatims)})
        for verbatim in verbatims:
            await websocket.send_json(verbatim.model_dump_json())
    except Exception as e:
        logger.error(f"Error processing CSV action for client {websocket.client} Error trace:  {str(e)}")
        await websocket.send_json({"status": "error", "message": str(e)})


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
                    f"Updated verbatim {verbatim.id} with status {Status.RUN}"
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
