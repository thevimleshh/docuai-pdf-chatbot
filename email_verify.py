from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
import models


router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


@router.get("/verify-email")
async def verify_email_page(
    request: Request,
    email: str = ""
):
    return templates.TemplateResponse(
        request=request,
        name="verify_email.html",
        context={
            "email": email,
            "message": None
        }
    )


@router.post("/verify-email")
async def verify_email(
    request: Request,
    email: str = Form(...),
    verification_code: str = Form(...),
    db: Session = Depends(get_db)
):
    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="verify_email.html",
            context={
                "email": email,
                "message": "User not found."
            }
        )

    if user.verification_code != verification_code:
        return templates.TemplateResponse(
            request=request,
            name="verify_email.html",
            context={
                "email": email,
                "message": "Invalid verification code. Please try again."
            }
        )

    user.is_verified = True
    user.verification_code = None

    db.commit()

    return RedirectResponse(
        url="/login",
        status_code=303
    )