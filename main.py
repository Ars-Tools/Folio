from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.agents import router as agents_router, load_agents
from api.auth import router as auths_router
from api.approvals import router as approvals_router
from api.providers import router as providers_router
from api.skills import router as skills_router
from api.tokens import router as tokens_router
from core.db import init_db, engine
from models.provider import Provider
from models.token import Token, TokenKind

from sqlmodel import Session as DBSession, select
from contextlib import asynccontextmanager
import os
import secrets


def _seed_db():
    """Seed database with default data from existing agents/ directory."""
    with DBSession(engine) as db:
        # Seed default provider if not exists
        if not db.get(Provider, "local"):
            db.add(Provider(
                id="local",
                name="Apple On-Device",
                kind="openai-chat",
                endpoint="http://127.0.0.1:11535/v1",
                apikey="local",
            ))
            db.commit()

        # Seed initial admin user token if no user tokens exist
        user_tokens = db.exec(
            select(Token).where(Token.kind == TokenKind.user)
        ).all()
        if not user_tokens:
            admin_token = f"fol_{secrets.token_urlsafe(32)}"
            db.add(Token(id=admin_token, name="admin", kind=TokenKind.user))
            db.commit()
            print(f"\n{'='*60}")
            print(f"  Initial admin token created:")
            print(f"  {admin_token}")
            print(f"{'='*60}\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — create tables, seed, load agents
    init_db()
    _seed_db()
    load_agents()
    yield
    # cleanup

app = FastAPI(lifespan=lifespan)
app.include_router(auths_router)
app.include_router(agents_router)
app.include_router(approvals_router)
app.include_router(providers_router)
app.include_router(skills_router)
app.include_router(tokens_router)

# Mount frontend if built
if os.path.exists("ui/dist"):
    app.mount("/assets", StaticFiles(directory="ui/dist/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API routes are already handled above.
        # If the path is not an API route and not an asset, serve index.html
        # Note: Ideally API routes should be under /api scope to easier distinction
        if full_path.startswith(("api", "agent", "auth", "approval", "provider", "skill", "token", "capabilit")):
             # Use default 404 behavior? The route matched here, so we need to return 404 manually or let it fall through?
             # Depends on if we rely on FastAPI's default 404. 
             # Since this catch-all matches everything, standard 404 won't trigger for non-matched paths.
             # We should probably return 404 JSON for API-like paths.
             from fastapi import HTTPException
             raise HTTPException(status_code=404, detail="Not Found")
        
        return FileResponse("ui/dist/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)