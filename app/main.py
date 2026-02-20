from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.agents import router as agents_router
from app.api.auth import router as auths_router
from app.core.db import init_db, engine
from app.models.user import User

from sqlmodel import Session as DBSession, select
from contextlib import asynccontextmanager
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # prepare — create tables & seed default user
    init_db()
    with DBSession(engine) as db:
        if not db.exec(select(User).where(User.name == "admin")).first():
            db.add(User(name="admin", password_hash=User.hash_password("admin123")))
            db.commit()
    yield
    # cleanup

app = FastAPI(lifespan=lifespan)
app.include_router(auths_router)
app.include_router(agents_router)

# Mount frontend if built
if os.path.exists("app/ui/dist"):
    app.mount("/assets", StaticFiles(directory="app/ui/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API routes are already handled above.
        # If the path is not an API route and not an asset, serve index.html
        # Note: Ideally API routes should be under /api scope to easier distinction
        if full_path.startswith("api") or full_path.startswith("agent") or full_path.startswith("auth"):
             # Use default 404 behavior? The route matched here, so we need to return 404 manually or let it fall through?
             # Depends on if we rely on FastAPI's default 404. 
             # Since this catch-all matches everything, standard 404 won't trigger for non-matched paths.
             # We should probably return 404 JSON for API-like paths.
             from fastapi import HTTPException
             raise HTTPException(status_code=404, detail="Not Found")
        
        return FileResponse("app/ui/dist/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)