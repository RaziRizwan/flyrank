"""
routers/auth.py -- signup and login. Thin: validate, hash/verify, issue a token. No SQL
here -- everything goes through repository.py.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

import auth
import repository
from schemas import SignupRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


@router.post("/signup", status_code=201)
def signup(payload: SignupRequest):
    if not payload.email or not payload.password:
        return error(400, "email and password are required")
    if len(payload.password) < 8:
        return error(400, "password must be at least 8 characters")
    if repository.get_user_by_email(payload.email) is not None:
        return error(400, "an account with this email already exists")

    tenant_name = payload.company_name or payload.email.split("@")[0]
    password_hash = auth.hash_password(payload.password)
    user = repository.create_tenant_and_user(payload.email, password_hash, tenant_name)
    return JSONResponse(status_code=201, content={
        "id": user["id"], "tenant_id": user["tenant_id"], "email": user["email"],
    })


@router.post("/login")
def login(payload: LoginRequest):
    if not payload.email or not payload.password:
        return error(400, "email and password are required")

    user = repository.get_user_by_email(payload.email)
    if user is None or not auth.verify_password(payload.password, user["password_hash"]):
        return error(401, "invalid email or password")

    token = auth.create_access_token(user["id"], user["tenant_id"])
    return {"access_token": token, "token_type": "bearer"}
