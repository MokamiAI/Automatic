from app.db.supabase import supabase
from app.services.verification_service import verify_or_fetch_bureau
from app.services.recommendation_service import recommend


def run_auto_processing():

    # 1️⃣ Fetch all clients
    clients = (
        supabase
        .table("clients")
        .select("*")
        .execute()
        .data
    )

    for client in clients:

        if not client.get("primary_interest"):
            continue

        # 2️⃣ Ensure bureau verified
        verify_or_fetch_bureau(client)

        # 3️⃣ Check if recommendation exists
        existing = (
            supabase
            .table("recommendations")
            .select("id")
            .eq("user_id", client["id"])
            .eq("selected_option", int(client["primary_interest"]))
            .execute()
            .data
        )

        if existing:
            continue

        # 4️⃣ Generate recommendation
        recommend(client)
