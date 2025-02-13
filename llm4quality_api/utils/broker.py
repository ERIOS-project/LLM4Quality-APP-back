import pika
import json
import time
from llm4quality_api.config.config import Config


def publish_message(queue, message):
    """Publish a message to RabbitMQ."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=Config.RABBITMQ_HOST, port=Config.RABBITMQ_PORT, credentials=pika.PlainCredentials(Config.RABBITMQ_USERNAME, Config.RABBITMQ_PASSWORD))
    )
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(exchange="", routing_key=queue, body=json.dumps(message))
    connection.close()


def consume_messages(queue, callback):
    """Consume messages from RabbitMQ with retry logic."""
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=Config.RABBITMQ_HOST)
            )
            channel = connection.channel()
            channel.queue_declare(queue=queue, durable=True)

            channel.basic_consume(
                queue=queue, on_message_callback=callback, auto_ack=True
            )
            print(f"Connected to RabbitMQ. Listening on {queue}...")
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            print("RabbitMQ connection failed. Retrying in 5 seconds...")
            time.sleep(5)
