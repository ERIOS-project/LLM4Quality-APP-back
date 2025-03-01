from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from llm4quality_api.routes.routes import router
from threading import Thread
from llm4quality_api.config.config import Config
from llm4quality_api.utils.broker import consume_messages
from llm4quality_api.tasks.verbatims import handle_worker_response


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
    title = "LLM4Quality API",
    description = """
    L'API LLM4Quality permet d'analyser et de classifier automatiquement des verbatims afin d'améliorer la qualité des soins en milieu hospitalier.

    Verbatims

    - Création et gestion des verbatims.
    - Suivi des statuts des verbatims en temps réel.

    Classification et Analyse

    - Exécution du pipeline d'analyse basé sur le traitement du langage naturel.
    - Évaluation de la cohérence des classifications.
    """,
    summary = "Une API dédiée à l'analyse des verbatims pour l'amélioration de la qualité des soins.",
    version = "0.1.0",
    contact = {
    "name": "Xavier Corbier",
    "email": "xavier.corbier@umontpellier.fr",
    },
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": Config.APP_CLIENT_ID,
        "scopes": Config.SCOPE_NAME,
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
    app_client_id=Config.APP_CLIENT_ID,
    tenant_id=Config.TENANT_ID,
    scopes=Config.SCOPES,
)

# Include API routes
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(Config.PORT))
