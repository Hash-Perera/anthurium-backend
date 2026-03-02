from fastapi import FastAPI
from routes.health import router as health_router
from routes.disease import router as disease_router

app = FastAPI(title="LeafGuard Disease API")

app.include_router(health_router)
app.include_router(disease_router)

