from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import authenticate_admin, ensure_default_admin
from app.utils.security import create_access_token

router = APIRouter(prefix="/admin", tags=["admin-auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    ensure_default_admin(db)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if authenticate_admin(db, username, password):
        token = create_access_token(username)
        response = RedirectResponse(url="/admin/dashboard", status_code=303)
        response.set_cookie("session_token", token, httponly=True, max_age=60 * 60 * 12)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"}, status_code=401)


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("session_token")
    return response
