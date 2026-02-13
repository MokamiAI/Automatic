import time
from app.db.supabase import supabase
from app.services.verification_service import verify_or_fetch_bureau
from app.services.recommendation_service import generate_full_recommendations


def process_clients():

    while True:
        try:

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

                # Check bureau exists
                bureau = (
                    supabase
                    .table("bureau_profiles")
                    .select("user_id")
                    .eq("user_id", client["id"])
                    .execute()
                    .data
                )

                if not bureau:
                    verify_or_fetch_bureau(client)

                generate_full_recommendations(client)

        except Exception as e:
            print("Auto processor error:", e)

        time.sleep(10)  # Every 10 seconds
