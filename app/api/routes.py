from fastapi import APIRouter, HTTPException
from uuid import UUID

from app.db.supabase import supabase
from app.services.verification_service import verify_or_fetch_bureau
from app.services.recommendation_service import (
    generate_full_recommendations,
    get_recommendation_for_option
)

router = APIRouter()


# -------------------------------------------------
# Root
# -------------------------------------------------
@router.get("/")
def root():
    return {
        "status": "ok",
        "service": "nerve-engine"
    }


# -------------------------------------------------
# Health
# -------------------------------------------------
@router.get("/health")
def health():
    return {
        "status": "healthy"
    }


# -------------------------------------------------
# Main Processing Endpoint
# -------------------------------------------------
@router.post("/process-customer/{client_id}")
def process_customer(client_id: UUID):

    # -------------------------------------------------
    # 1️⃣ Fetch Client
    # -------------------------------------------------
    response = (
        supabase
        .table("clients")
        .select("*")
        .eq("id", str(client_id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Client not found"
        )

    client = response.data[0]

    # -------------------------------------------------
    # 2️⃣ Validate Required Fields
    # -------------------------------------------------
    required_fields = [
        "first_name",
        "surname",
        "id_number",
        "primary_interest"
    ]

    missing_fields = [
        field for field in required_fields
        if not client.get(field)
    ]

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Client missing required fields: {missing_fields}"
        )

    # -------------------------------------------------
    # 3️⃣ Bureau Verification (if not already done)
    # -------------------------------------------------
    verify_or_fetch_bureau(client)

    # -------------------------------------------------
    # 4️⃣ Generate Full Recommendations (ONLY ONCE)
    # -------------------------------------------------
    generate_full_recommendations(client)

    # -------------------------------------------------
    # 5️⃣ Fetch Recommendation Based On Current Interest
    # -------------------------------------------------
    recommendation = get_recommendation_for_option(client)

    # -------------------------------------------------
    # 6️⃣ Return Clean Response
    # -------------------------------------------------
    return {
        "client_id": client["id"],
        "first_name": client["first_name"],
        "surname": client["surname"],
        "primary_interest": client["primary_interest"],
        "recommendation": recommendation
    }
