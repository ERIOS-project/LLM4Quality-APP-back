import os

class Config:
    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/llm4quality")
    PORT = os.getenv("PORT",8080)

    # RabbitMQ Configuration
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
