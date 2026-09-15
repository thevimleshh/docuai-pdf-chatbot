import random
import os
import shutil

from fastapi import (
    FastAPI,
    Request,
    Depends,
    Form,
    UploadFile,
    File
)
import uuid
from vector_store import add_chunks,search_chunks
from ai_model import ask_ai
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models

from auth import hash_password, verify_password
from google_service import send_verification_email
from email_verify import router as email_verify_router

from pdf_reader import extract_text_from_pdf
from chunking import split_text_into_chunks


app = FastAPI()
app.add_middleware(
    SessionMiddleware,
   secret_key=os.getenv("SECRET_KEY")
)


# ==============================
# DATABASE
# ==============================

Base.metadata.create_all(bind=engine)


# ==============================
# EMAIL VERIFICATION ROUTER
# ==============================

app.include_router(email_verify_router)


# ==============================
# STATIC FILES
# ==============================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ==============================
# TEMPLATES
# ==============================

templates = Jinja2Templates(
    directory="templates"
)


# ==============================
# HOME
# ==============================

@app.get("/")
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )


# ==============================
# SIGNUP PAGE
# ==============================

@app.get("/signup")
async def signup(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="signup.html"
    )


# ==============================
# SIGNUP
# ==============================

@app.post("/auth/signup")
async def signup_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    if existing_user:

        return {
            "success": False,
            "message": "Email already registered"
        }


    # Generate 6 digit verification code
    verification_code = str(
        random.randint(100000, 999999)
    )


    # Hash password
    hashed_password = hash_password(password)


    # Create user
    new_user = models.User(
        name=name,
        email=email,
        password=hashed_password,
        is_verified=False,
        verification_code=verification_code
    )


    db.add(new_user)
    db.commit()
    db.refresh(new_user)


    # Send verification email
    try:

        send_verification_email(
            email,
            verification_code
        )

    except Exception as error:

        print("EMAIL ERROR:", error)

        db.delete(new_user)
        db.commit()

        return {
            "success": False,
            "message": "Unable to send verification email."
        }


    # Redirect to verification page
    return RedirectResponse(
        url=f"/verify-email?email={email}",
        status_code=303
    )


# ==============================
# LOGIN PAGE
# ==============================

@app.get("/login")
async def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

# ==============================
# LOGIN
# ==============================

@app.post("/auth/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    user = (
        db.query(models.User)
        .filter(models.User.email == email)
        .first()
    )

    # User does not exist
    if not user:

        return {
            "success": False,
            "message": "Invalid email or password."
        }

    # Email not verified
    if not user.is_verified:

        return {
            "success": False,
            "message": "Please verify your email first."
        }

    # Password check
    if not verify_password(
        password,
        user.password
    ):

        return {
            "success": False,
            "message": "Invalid email or password."
        }

    # ==============================
    # SAVE USER IN SESSION
    # ==============================

    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_email"] = user.email

    # Login successful
    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )

# ==============================
# DASHBOARD
# ==============================

@app.get("/dashboard")
async def dashboard(request: Request):

    # Check logged-in user
    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # Get user information from session
    user_name = request.session.get(
        "user_name",
        "User"
    )

    user_email = request.session.get(
        "user_email",
        ""
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user_name": user_name,
            "user_email": user_email
        }
    )
# ==============================
# LOGOUT
# ==============================

@app.get("/logout")
async def logout(request: Request):

    # Clear login session
    request.session.clear()

    # Go back to home page
    return RedirectResponse(
        url="/",
        status_code=303
    )
# ==============================
# PDF UPLOAD
# ==============================

@app.post("/upload-pdf")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # ==============================
    # CHECK LOGIN
    # ==============================

    user_id = request.session.get("user_id")

    if not user_id:

        return {
            "success": False,
            "message": "Please login first."
        }


    # ==============================
    # CHECK PDF
    # ==============================

    if not file.filename.lower().endswith(".pdf"):

        return {
            "success": False,
            "message": "Only PDF files are allowed."
        }


    # ==============================
    # CREATE UPLOAD FOLDER
    # ==============================

    os.makedirs(
        "uploads",
        exist_ok=True
    )


    # ==============================
    # CREATE UNIQUE DOCUMENT ID
    # ==============================

    document_id = str(
        uuid.uuid4()
    )


    # ==============================
    # SAVE PDF FILE
    # ==============================

    file_path = os.path.join(
        "uploads",
        f"{document_id}_{file.filename}"
    )


    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    try:

        # ==============================
        # EXTRACT PDF TEXT
        # ==============================

        text = extract_text_from_pdf(
            file_path
        )


        # ==============================
        # CREATE CHUNKS
        # ==============================

        chunks = split_text_into_chunks(
            text
        )


        # ==============================
        # STORE CHUNKS IN CHROMADB
        # ==============================

        saved_chunks = add_chunks(
            chunks,
            document_id
        )


        # ==============================
        # SAVE DOCUMENT IN MYSQL
        # ==============================

        new_document = models.Document(

            user_id=user_id,

            document_name=file.filename,

            file_path=file_path,

            document_id=document_id
        )


        db.add(
            new_document
        )

        db.commit()

        db.refresh(
            new_document
        )


        # ==============================
        # SUCCESS LOG
        # ==============================

        print("\n==============================")
        print("PDF UPLOAD SUCCESS")
        print("==============================")

        print(
            "User ID:",
            user_id
        )

        print(
            "Document ID:",
            document_id
        )

        print(
            "Filename:",
            file.filename
        )

        print(
            "Total chunks:",
            saved_chunks
        )

        print("==============================\n")


    except Exception as error:

        print(
            "PDF ERROR:",
            error
        )

        # Remove uploaded file if processing fails
        if os.path.exists(file_path):

            os.remove(file_path)

        return {
            "success": False,
            "message": "Unable to process PDF."
        }


    # ==============================
    # RESPONSE
    # ==============================

    return {

        "success": True,

        "message":
            "PDF uploaded and processed successfully.",

        "filename":
            file.filename,

        "document_id":
            document_id,

        "total_chunks":
            saved_chunks
    }


@app.get("/test-search")
async def test_search(question: str):

    results = search_chunks(
        question,
        n_results=3
    )

    return {
        "question": question,
        "results": results
    }
@app.get("/test-ai")
async def test_ai(question: str):

    answer = ask_ai(
        question,
        "The student is studying Bachelor of Engineering."
    )

    return {
        "question": question,
        "answer": answer
    }

# ==============================
# ASK QUESTION
# ==============================

@app.post("/ask")
async def ask_question(
    request: Request,
    question: str = Form(...),
    document_id: str = Form(...),
    db: Session = Depends(get_db)
):

    try:

        # ==============================
        # CHECK LOGIN
        # ==============================

        user_id = request.session.get(
            "user_id"
        )

        if not user_id:

            return {
                "success": False,
                "message": "Please login first."
            }


        # ==============================
        # CHECK DOCUMENT OWNERSHIP
        # ==============================

        document = (
            db.query(models.Document)
            .filter(
                models.Document.document_id == document_id,
                models.Document.user_id == user_id
            )
            .first()
        )


        if not document:

            return {
                "success": False,
                "message": "You do not have access to this document."
            }


        # ==============================
        # SEARCH DOCUMENT CHUNKS
        # ==============================

        chunks = search_chunks(
            question,
            document_id,
            n_results=3
        )


        # ==============================
        # NO RESULTS
        # ==============================

        if not chunks:

            return {
                "success": False,
                "message":
                    "No relevant information found in this document."
            }


        # ==============================
        # CREATE CONTEXT
        # ==============================

        context = "\n\n".join(
            chunks
        )


        # ==============================
        # ASK AI
        # ==============================

        answer = ask_ai(
            question,
            context
        )


        # ==============================
        # RESPONSE
        # ==============================

        return {

            "success": True,

            "question":
                question,

            "answer":
                answer
        }


    except Exception as error:

        print(
            "ASK ERROR:",
            error
        )

        return {

            "success": False,

            "message":
                "Unable to answer the question."
        }
    # ==============================
# MY DOCUMENTS
# ==============================

@app.get("/documents")
async def my_documents(
    request: Request,
    db: Session = Depends(get_db)
):

    # CHECK LOGIN
    user_id = request.session.get("user_id")

    if not user_id:

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # CURRENT USER KE DOCUMENTS
    documents = (
        db.query(models.Document)
        .filter(
            models.Document.user_id == user_id
        )
        .order_by(
            models.Document.id.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={
            "documents": documents
        }
    )

