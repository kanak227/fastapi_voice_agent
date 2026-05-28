from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# `/health/agent-domains` is registered on the FastAPI app in `main.create_app`
# so it always attaches even when APIRouter mounts behave inconsistently.
