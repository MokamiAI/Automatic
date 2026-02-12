from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.db.supabase import supabase
from app.services.verification_service import verify_or_fetch_bureau
from app.services.recommendation_service import recommend

router = APIRouter()


@router.get("/")
def root():
    return {"status": "ok", "service": "nerve-engine"}


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.post("/process-customer/{client_id}")
def process_customer(client_id: UUID):

    response = (
        supabase
        .table("clients")
        .select("*")
        .eq("id", str(client_id))
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Client not found")

    client = response.data[0]

    if not client.get("primary_interest"):
        raise HTTPException(
            status_code=400,
            detail="Client primary_interest missing"
        )

    # Bureau enrichment
    verify_or_fetch_bureau(client)

    # Generate recommendation
    best, next_best = recommend(client)

    return {
        "client_id": client["id"],
        "first_name": client["first_name"],
        "surname": client["surname"],
        "primary_interest": client["primary_interest"],
        "best_product": best,
        "next_best_product": next_best
    }
