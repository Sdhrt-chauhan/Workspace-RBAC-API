# FastAPI Enterprise RBAC & Task Management API

A production-ready, secure backend application built with **FastAPI**, **SQLAlchemy**, and **JSON Web Tokens (JWT)**. This project demonstrates enterprise-level architecture including granular **Role-Based Access Control (RBAC)** and secure local database file management.

## 🚀 Features

- **JWT-Based Authentication**: Secure user registration and token-based login flow using OAuth2.
- **Role-Based Access Control (RBAC)**: 
  - `developer` role: Authorized to create and view tasks, but restricted from deletion (`403 Forbidden`).
  - `admin` role: Full administrative privileges including task deletion.
- **Task Management (CRUD)**: Complete endpoints to create, read, and delete workspace tasks.
- **Robust Path Management**: Uses `pathlib` to ensure the SQLite database (`workspace.db`) persists cleanly inside the project directory regardless of execution context.
- **Interactive API Docs**: Built-in Swagger UI (`/docs`) supporting seamless bearer token authorization.

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **Security**: Passlib (Bcrypt hashing), python-jose (JWT)
- **Server**: Uvicorn

## ⚙️ Running Locally

1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/fastapi-rbac-workspace.git](https://github.com/your-username/fastapi-rbac-workspace.git)
   cd fastapi-rbac-workspace
  1. Create and activate a virtual environment:
       python -m venv .venv
        # On Windows:
        .venv\Scripts\Activate.ps1
  2. Install dependencies:
       pip install fastapi uvicorn sqlalchemy pydantic passlib python-jose
  3. Run the application:
       python main.py
  4. Open your browser and navigate to http://127.0.0.1:8000/docs to test the API endpoints.
     
