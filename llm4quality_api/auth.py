from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2AuthorizationCodeBearer
from msal import ConfidentialClientApplication
from starlette.requests import Request
import os
from fastapi import WebSocket, WebSocketDisconnect
import json

from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configurations
client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")
authority = os.environ.get("AUTHORITY")
api_scope = [os.environ.get("API_SCOPE")]

app = ConfidentialClientApplication(
    client_id,
    authority=authority,
    client_credential=client_secret,
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://login.microsoftonline.com/4c1633ed-3be4-4aa7-a440-b4b227becdde/oauth2/v2.0/authorize",
    tokenUrl="https://login.microsoftonline.com/4c1633ed-3be4-4aa7-a440-b4b227becdde/oauth2/v2.0/token",
)

async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    result = app.acquire_token_on_behalf_of(token, scopes=api_scope)

    if "error" in result:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return result["id_token_claims"]


async def get_current_user_websocket(token: str = Depends(oauth2_scheme)):
    result = app.acquire_token_on_behalf_of(token, scopes=api_scope)

    if "error" in result:
        # If the token is invalid, close the websocket connection
        return

    # If the token is valid, return the claims
    return result["id_token_claims"]
