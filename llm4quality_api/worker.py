import pika
import json
import time
import logging
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Optional, Dict
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = "localhost"
WORKER_REQUESTS_QUEUE = "worker_requests"
WORKER_RESPONSES_QUEUE = "worker_responses"
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds


# Verbatim model
class Verbatim(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    content: str
    status: str
    result: Optional[Dict[str, Dict[str, str]]] = None
    year: int
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        populate_by_name = True

    def to_json(self):
        return self.model_dump_json(by_alias=True, exclude_unset=True)

    @classmethod
    def from_json(cls, data: dict):
        return cls(
            id=str(data.get("id")) if data.get("id") else None,
            content=data["content"],
            status=data["status"],
            result=data.get("result"),
            year=data["year"],
            created_at=data.get("created_at"),
        )


def connect_to_rabbitmq():
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(
                f"Attempting to connect to RabbitMQ (Attempt {attempt + 1}/{MAX_RETRIES})..."
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            logger.info("Successfully connected to RabbitMQ.")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"RabbitMQ connection failed: {e}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Max retries reached. Could not connect to RabbitMQ.")
                raise


def process_verbatim_pipeline(verbatim: Verbatim) -> Verbatim:
    """
    Process the pipeline for a given verbatim message.
    """
    try:

        output_dir = f"/tmp/output_{verbatim.id}"
        input_csv = f"/tmp/input_{verbatim.id}.csv"

        # Write content to a CSV file
        with open(input_csv, "w") as csv_file:
            csv_file.write(verbatim.content)

        # Mocked processing
        print("Gonna mock the Evaluation, sleeping for 5 seconds")
        time.sleep(5)

        # Simulated result
        processed_result = {
            "circuit_de_prise_en_charge": {
                "La fluidité et la personnalisation du parcours": {
                    "positive": 0,
                    "negative": 0,
                },
                "L’accueil et l’admission": {"positive": 0, "negative": 0},
                "Le circuit administratif": {"positive": 0, "negative": 0},
                "La rapidité de prise en charge et le temps d’attente": {
                    "positive": 0,
                    "negative": 0,
                },
                "L’accès au bloc": {"positive": 0, "negative": 0},
                "La sortie de l’établissement": {"positive": 0, "negative": 1},
                "Le suivi du patient après le séjour hospitalier": {
                    "positive": 1,
                    "negative": 0,
                },
                "Les frais supplémentaires et dépassements d’honoraires": {
                    "positive": 0,
                    "negative": 0,
                },
            },
            "professionnalisme_de_l_equipe": {
                "L’information et les explications": {"positive": 0, "negative": 0},
                "L’humanité et la disponibilité des professionnels": {
                    "positive": 0,
                    "negative": 0,
                },
                "Les prises en charges médicales et paramédicales": {
                    "positive": 0,
                    "negative": 0,
                },
                "Droits des patients": {"positive": 0, "negative": 0},
                "Gestion de la douleur et médicaments": {"positive": 0, "negative": 0},
                "Maternité et pédiatrie": {"positive": 0, "negative": 0},
            },
            "qualite_hoteliere": {
                "L’accès à l’établissement": {"positive": 0, "negative": 0},
                "Les locaux et les chambres": {"positive": 0, "negative": 0},
                "L’intimité": {"positive": 0, "negative": 0},
                "Le calme/volume sonore": {"positive": 0, "negative": 0},
                "La température de la chambre": {"positive": 0, "negative": 0},
                "Les repas et collations": {"positive": 0, "negative": 0},
                "Les services WiFi et TV": {"positive": 0, "negative": 0},
            },
        }

        # Update the Verbatim instance
        verbatim.result = processed_result
        verbatim.status = "SUCCESS"
        return verbatim

    except Exception as e:
        logger.error(f"Error in processing pipeline: {e}")
        # Return an error Verbatim object
        return Verbatim(
            **verbatim,
            status="ERROR",
            result=None,
        )


def callback(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(isinstance(message, dict))
        logger.info(f"Received message: {message}")

        verbatim = Verbatim.from_json(json.loads(message))
        processed_verbatim = process_verbatim_pipeline(verbatim)

        publish_message(WORKER_RESPONSES_QUEUE, processed_verbatim.to_json())
        logger.info(
            f"Processed and published result for verbatim ID: {processed_verbatim.id}"
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def publish_message(queue, message):
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(exchange="", routing_key=queue, body=message)
    connection.close()


def main():
    connection = connect_to_rabbitmq()
    channel = connection.channel()

    channel.queue_declare(queue=WORKER_REQUESTS_QUEUE, durable=True)
    channel.basic_consume(queue=WORKER_REQUESTS_QUEUE, on_message_callback=callback)

    logger.info(f"Listening for messages on {WORKER_REQUESTS_QUEUE}...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
        channel.stop_consuming()
        connection.close()


if __name__ == "__main__":
    main()
