from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import database components and routers
from app.db.connection import engine
from app.api.checkout import router as checkout_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("Database tables initialized successfully.")
    
    yield # Application runs here
    
    # --- SHUTDOWN ---
    await engine.dispose()
    print("Database connections closed.")

# Initialize Verve Gate API with lifespan
app = FastAPI(
    title="Verve Gate",
    description="Unified Cross-Border Payment Gateway API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for the React Frontend (supports Vite on 5173 and standard 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(checkout_router)
app.include_router(auth_router)
app.include_router(admin_router)

# Basic health check route
@app.get("/")
async def root():
    return {"message": "Verve Gate API is running smoothly."}