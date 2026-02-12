import random
from datetime import datetime
from app.db.supabase import supabase


def generate_mock_xds(client: dict):

    return {
        "bureau": "XDS",
        "enquiry_reason": "Credit assessment",
        "enquiry_date": datetime.utcnow().isoformat(),
        "enquiry_type": "Consumer Credit Enquiry",

        "marital_status": random.choice(["Single", "Married"]),
        "gender": random.choice(["Male", "Female"]),
        "title": "Mr",
        "first_name": client["first_name"],
        "second_name": "",
        "surname": client["surname"],
        "maiden_name": None,
        "id_number": client["id_number"],
        "passport_number": None,
        "date_of_birth": client["date_of_birth"],
        "email": None,
        "cellular": client["phone"],
        "telephone_work": None,
        "telephone_home": None,
        "residential_address": "Johannesburg",
        "postal_address": "Johannesburg",
        "current_employer": "Private Company",

        "fraud_id_verified": True,
        "fraud_deceased_status": "Not Deceased",
        "fraud_found_on_database": False,

        "presage_score": random.randint(500, 750),
        "nlr_score": random.randint(500, 750),

        "raw_payload": {"mock": True}
    }


def verify_or_fetch_bureau(client: dict):

    client_id = client["id"]

    # 1️⃣ Check if profile exists
    existing = (
        supabase
        .table("bureau_profiles")
        .select("*")
        .eq("user_id", client_id)
        .execute()
        .data
    )

    if existing:
        return existing[0]

    # 2️⃣ Generate mock XDS profile
    profile = generate_mock_xds(client)

    profile["user_id"] = client_id

    result = (
        supabase
        .table("bureau_profiles")
        .insert(profile)
        .execute()
    )

    return result.data[0]
