
import os
import shutil
import uuid

from fastapi import (
    FastAPI,
    Request,
    Depends,
    Form,
    UploadFile,
    File
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models

from auth import hash_password, verify_password

from pdf_reader import extract_text_from_pdf
from chunking import split_text_into_chunks
from vector_store import add_chunks, search_chunks
from ai_model import ask_ai


# ==========================================
# APP
# ==========================================

app = FastAPI()


# ==========================================
# SESSION
# ==========================================

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY")
)


# ==========================================
# DATABASE
# ==========================================

Base.metadata.create_all(bind=engine)


# ==========================================
# STATIC FILES
# ==========================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


# ==========================================
# TEMPLATES
# ==========================================

templates = Jinja2Templates(
    directory="templates"
)


# ==========================================
# HOME
# ==========================================

@app.get("/")
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )


# ==========================================
# SIGNUP PAGE
# ==========================================

@app.get("/signup")
async def signup(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="signup.html"
    )


# ==========================================
# SIGNUP
# ==========================================

@app.post("/auth/signup")
async def signup_user(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    # --------------------------------------
    # Check existing user
    # --------------------------------------

    existing_user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )

    if existing_user:

        return {
            "success": False,
            "message":
                "Email already registered."
        }


    # --------------------------------------
    # Hash password
    # --------------------------------------

    hashed_password = hash_password(
        password
    )


    # --------------------------------------
    # Create user
    # --------------------------------------

    new_user = models.User(
        name=name,
        email=email,
        password=hashed_password
    )

    db.add(new_user)

    db.commit()

    db.refresh(new_user)


    # --------------------------------------
    # Signup successful
    # --------------------------------------

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# ==========================================
# LOGIN PAGE
# ==========================================

@app.get("/login")
async def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


# ==========================================
# LOGIN
# ==========================================
@app.post("/auth/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Wrong email or password."
            },
            status_code=401
        )

    if not verify_password(
        password,
        user.password
    ):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Wrong password."
            },
            status_code=401
        )

    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["user_email"] = user.email

    return RedirectResponse(
        url="/dashboard",
        status_code=303
    )




# ==========================================
# DASHBOARD
# ==========================================

@app.get("/dashboard")
async def dashboard(
    request: Request
):

    # --------------------------------------
    # Check login
    # --------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            url="/login",
            status_code=303
        )


    # --------------------------------------
    # User information
    # --------------------------------------

    user_name = request.session.get(
        "user_name",
        "User"
    )

    user_email = request.session.get(
        "user_email",
        ""
    )


    # --------------------------------------
    # Dashboard page
    # --------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user_name": user_name,
            "user_email": user_email
        }
    )


# ==========================================
# LOGOUT
# ==========================================

@app.get("/logout")
async def logout(
    request: Request
):

    request.session.clear()

    return RedirectResponse(
        url="/",
        status_code=303
    )


# ==========================================
# UPLOAD PDF
# ==========================================

@app.post("/upload-pdf")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # --------------------------------------
    # Check login
    # --------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return {
            "success": False,
            "message":
                "Please login first."
        }


    # --------------------------------------
    # Check file
    # --------------------------------------

    if not file.filename:

        return {
            "success": False,
            "message":
                "Please select a PDF file."
        }


    if not file.filename.lower().endswith(
        ".pdf"
    ):

        return {
            "success": False,
            "message":
                "Only PDF files are allowed."
        }


    # --------------------------------------
    # Create uploads folder
    # --------------------------------------

    os.makedirs(
        "uploads",
        exist_ok=True
    )


    # --------------------------------------
    # Generate document ID
    # --------------------------------------

    document_id = str(
        uuid.uuid4()
    )


    # --------------------------------------
    # File path
    # --------------------------------------

    file_path = os.path.join(
        "uploads",
        f"{document_id}_{file.filename}"
    )


    # --------------------------------------
    # Save PDF
    # --------------------------------------

    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    try:

        # ----------------------------------
        # Extract PDF text
        # ----------------------------------

        text = extract_text_from_pdf(
            file_path
        )


        if not text.strip():

            raise Exception(
                "No readable text found in PDF."
            )


        # ----------------------------------
        # Split text into chunks
        # ----------------------------------

        chunks = split_text_into_chunks(
            text
        )


        if not chunks:

            raise Exception(
                "No text chunks created."
            )


        # ----------------------------------
        # Add chunks to ChromaDB
        # ----------------------------------

        saved_chunks = add_chunks(
            chunks,
            document_id
        )


        # ----------------------------------
        # Save document in database
        # ----------------------------------

        new_document = models.Document(
            user_id=user_id,
            document_name=file.filename,
            file_path=file_path,
            document_id=document_id
        )

        db.add(new_document)

        db.commit()

        db.refresh(
            new_document
        )


        # ----------------------------------
        # Console information
        # ----------------------------------

        print(
            "\n=============================="
        )

        print(
            "PDF UPLOAD SUCCESS"
        )

        print(
            "=============================="
        )

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

        print(
            "==============================\n"
        )


    except Exception as error:

        print(
            "PDF ERROR:",
            error
        )


        # ----------------------------------
        # Remove failed file
        # ----------------------------------

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )


        return {
            "success": False,
            "message":
                "Unable to process PDF."
        }


    # --------------------------------------
    # Success response
    # --------------------------------------

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


# ==========================================
# ASK QUESTION
# ==========================================

@app.post("/ask")
async def ask_question(
    request: Request,
    question: str = Form(...),
    document_id: str = Form(...),
    db: Session = Depends(get_db)
):

    try:

        # ----------------------------------
        # Check login
        # ----------------------------------

        user_id = request.session.get(
            "user_id"
        )

        if not user_id:

            return {
                "success": False,
                "message":
                    "Please login first."
            }


        # ----------------------------------
        # Check document ownership
        # ----------------------------------

        document = (
            db.query(models.Document)
            .filter(
                models.Document.document_id
                == document_id,

                models.Document.user_id
                == user_id
            )
            .first()
        )


        if not document:

            return {
                "success": False,
                "message":
                    "You do not have access to this document."
            }


        # ----------------------------------
        # Search relevant chunks
        # ----------------------------------

        chunks = search_chunks(
            question,
            document_id,
            n_results=3
        )


        if not chunks:

            return {
                "success": False,
                "message":
                    "No relevant information found in this document."
            }


        # ----------------------------------
        # Create context
        # ----------------------------------

        context = "\n\n".join(
            chunks
        )


        # ----------------------------------
        # Ask AI
        # ----------------------------------

        answer = ask_ai(
            question,
            context
        )


        # ----------------------------------
        # Return answer
        # ----------------------------------

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


# ==========================================
# MY DOCUMENTS
# ==========================================

@app.get("/documents")
async def my_documents(
    request: Request,
    db: Session = Depends(get_db)
):

    # --------------------------------------
    # Check login
    # --------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            url="/login",
            status_code=303
        )


    # --------------------------------------
    # User information
    # --------------------------------------

    user_name = request.session.get(
        "user_name",
        "User"
    )

    user_email = request.session.get(
        "user_email",
        ""
    )


    # --------------------------------------
    # Get documents
    # --------------------------------------

    documents = (
        db.query(models.Document)
        .filter(
            models.Document.user_id
            == user_id
        )
        .order_by(
            models.Document.id.desc()
        )
        .all()
    )


    # --------------------------------------
    # Documents page
    # --------------------------------------

    return templates.TemplateResponse(
        request=request,
        name="documents.html",
        context={
            "documents": documents,
            "user_name": user_name,
            "user_email": user_email
        }
    )

