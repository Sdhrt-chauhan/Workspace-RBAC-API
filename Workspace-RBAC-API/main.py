from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import bcrypt
import jwt
from datetime import datetime, timedelta
import enum
import uvicorn
from pathlib import Path

# 1. Configuration & Security Constants
SECRET_KEY = "supersecretkeyforworkspacejwtsecurity"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'workspace.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="Enterprise RBAC Workspace API", description="Multi-tenant team workspace with Role-Based Access Control")

# 2. OAuth2 & Bcrypt Setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

def hash_password(password: str):
    pwd_bytes = password[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password, hashed_password):
    pwd_bytes = plain_password[:72].encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 3. Roles Enum & Database Models
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.DEVELOPER)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    status = Column(String, default="Pending")
    owner_id = Column(Integer, ForeignKey("users.id"))

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Pydantic Schemas
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.DEVELOPER

class UserLogin(BaseModel):
    username: str
    password: str

class TaskCreate(BaseModel):
    title: str
    description: str
    status: str = "Pending"

# 5. Security & RBAC Dependencies
def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# RBAC Middleware Factory: Checks if user has required role
def require_role(allowed_roles: list[str]):
    def role_verifier(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Role '{current_user.role}' is not authorized for this action."
            )
        return current_user
    return role_verifier

# 6. API Endpoints
@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, db = Depends(get_db)):
    existing_user = db.query(User).filter((User.email == user_data.email) | (User.username == user_data.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered!")
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "success", "message": f"User '{new_user.username}' created with role '{new_user.role}'!"}

@app.post("/api/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    # OAuth2PasswordRequestForm automatically looks for 'username' and 'password' fields
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}
# --- TASK & RBAC ENDPOINTS ---
@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    # Any logged in user can create a task
    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        owner_id=current_user.id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"status": "success", "message": "Task created successfully!", "task_id": new_task.id}

@app.get("/api/tasks")
def get_tasks(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    # Users can view tasks
    tasks = db.query(Task).all()
    return {"status": "success", "tasks": tasks}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, current_user: User = Depends(require_role(["admin", "manager"])), db = Depends(get_db)):
    # ONLY Admin or Manager can delete tasks! Developers will get 403 Forbidden.
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"status": "success", "message": f"Task {task_id} deleted successfully by {current_user.role} ({current_user.username})!"}

@app.get("/")
def home():
    return {"message": "Welcome to Enterprise Workspace & RBAC API. Tasks & RBAC active!"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)