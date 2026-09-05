
from typing import Optional
from fastapi import FastAPI, Depends, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase_auth.errors import AuthApiError

from auth import supabase, bearer_scheme, get_current_user, error

app = FastAPI(title="Auth API", version="1.0")


class SignupRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


class LoginRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


@app.post("/auth/signup", status_code=201)
def signup(payload: SignupRequest):
    if not payload.email or not payload.password:
        return error(400, "email and password are required")
    try:
        result = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
    except AuthApiError as e:
        return error(400, str(e))
    return JSONResponse(status_code=201, content={
        "id": result.user.id, "email": result.user.email, "created_at": str(result.user.created_at)
    })


@app.post("/auth/login")
def login(payload: LoginRequest):
    if not payload.email or not payload.password:
        return error(400, "email and password are required")
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except AuthApiError:
        return error(401, "Invalid login credentials")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def profile(user = Depends(get_current_user)):
    if isinstance(user, JSONResponse):
        return user
    return {"id": user.id, "email": user.email, "created_at": str(user.created_at)}


@app.get("/protected/dashboard")
def dashboard(user = Depends(get_current_user)):
    if isinstance(user, JSONResponse):
        return user
    return {"message": f"Welcome back, {user.email}", "widgets": ["tasks", "stats"]}


@app.post("/auth/logout", status_code=204)
def logout(user = Depends(get_current_user)):
    if isinstance(user, JSONResponse):
        return user
    # Caveat (see the notebook's Stage 4 note): this revokes the refresh token server-side;
    # the bearer access token already issued remains valid until it naturally expires.
    try:
        supabase.auth.sign_out()
    except AuthApiError:
        pass
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
