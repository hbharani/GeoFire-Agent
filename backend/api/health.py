from fastapi import APIRouter

router = APIRouter(tags=["ops"])

@router.get("/health")
async def health():
    return {"status": "ok"}
