
import os
from typing import Optional
from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from supabase_auth.errors import AuthApiError
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]  # the ANON key -- never the service_role key

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

bearer_scheme = HTTPBearer(auto_error=False)


def error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """The one reusable guard -- every protected route depends on this and nothing else."""
    if credentials is None:
        return error(401, "Access token required")
    try:
        result = supabase.auth.get_user(credentials.credentials)
    except AuthApiError:
        return error(401, "Invalid or expired token")
    if result is None or result.user is None:
        return error(401, "Invalid or expired token")
    return result.user
