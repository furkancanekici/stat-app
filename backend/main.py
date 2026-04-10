from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import validate, enrich, compare, etabs

app = FastAPI(title="STAT API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(validate.router, prefix="/api")
app.include_router(enrich.router, prefix="/api")
app.include_router(compare.router, prefix="/api")
app.include_router(etabs.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0"}
