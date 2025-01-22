import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB Configuration
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb-service:27017/llm_quality")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "llm4quality")
    PORT = os.getenv("PORT", 8080)

    # RabbitMQ Configuration
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

    # Azure Configuration
    APP_CLIENT_ID = os.getenv("APP_CLIENT_ID", "")
    TENANT_ID = os.getenv("TENANT_ID", "")
    CLIENT_ID = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
    AUTHORITY = os.getenv("AUTHORITY", "")
    API_SCOPE = os.getenv("API_SCOPE", "")
    SCOPE_DESCRIPTION = os.getenv("SCOPE_DESCRIPTION", "user_impersonation")
    SCOPE_NAME = f"api://{APP_CLIENT_ID}/{SCOPE_DESCRIPTION}"
    SCOPES = {SCOPE_NAME: SCOPE_DESCRIPTION}


    @property
    def OPENAPI_AUTHORIZATION_URL(self) -> str:
        """
        Construct the Azure AD OpenAPI authorization URL.
        """
        return (
            f"https://login.microsoftonline.com/{self.TENANT_ID}/oauth2/v2.0/authorize"
        )

    @property
    def OPENAPI_TOKEN_URL(self) -> str:
        """
        Construct the Azure AD OpenAPI token URL.
        """
        return f"https://login.microsoftonline.com/{self.TENANT_ID}/oauth2/v2.0/token"
