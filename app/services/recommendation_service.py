from app.db.supabase import supabase
import uuid


# -------------------------------------------------
# Risk Band
# -------------------------------------------------
def calculate_risk_band(score: int):
    if score >= 700:
        return "LOW"
    elif score >= 600:
        return "MEDIUM"
    return "HIGH"


# -------------------------------------------------
# Generate Full Recommendations (Profile Aware)
# -------------------------------------------------
def generate_full_recommendations(client: dict):

    client_id = client["id"]

    # -------------------------------------------------
    # Load Bureau Profile
    # -------------------------------------------------
    bureau_data = (
        supabase
        .table("bureau_profiles")
        .select("*")
        .eq("user_id", client_id)
        .execute()
        .data
    )

    if not bureau_data:
        return

    bureau = bureau_data[0]
    score = bureau.get("presage_score", 0)

    # -------------------------------------------------
    # Check existing
    # -------------------------------------------------
    existing = (
        supabase
        .table("fnb_recommendations")
        .select("*")
        .eq("customer_id", client_id)
        .execute()
        .data
    )

    if existing:
        recommendation_payload = existing[0]
        update_mode = True
    else:
        recommendation_payload = {
            "id": f"rec-{uuid.uuid4()}",
            "customer_id": client_id,
            "enrichment_complete": True
        }
        update_mode = False

    # =================================================
    # OPTION 1, 2, 4 → products table
    # =================================================
    for option in [1, 2, 4]:

        products = (
            supabase
            .table("products")
            .select("*")
            .eq("option", option)
            .execute()
            .data or []
        )

        eligible = []

        for product in products:

            rules = product.get("eligibility_rules") or {}

            min_score = rules.get("min_credit_score", 0)
            credit_required = rules.get("credit_check", False)
            employment_required = rules.get("employment_required", False)

            if credit_required and score < min_score:
                continue

            if employment_required and not bureau.get("employment_status"):
                continue

            eligible.append(product)

        if not eligible:
            continue

        eligible.sort(
            key=lambda p: p.get("eligibility_rules", {}).get("min_credit_score", 0),
            reverse=True
        )

        best = eligible[0]
        next_best = eligible[1] if len(eligible) > 1 else None

        best_reason = ", ".join(best.get("benefits", [])[:2])
        next_reason = ", ".join(next_best.get("benefits", [])[:2]) if next_best else None

        if option == 1:
            recommendation_payload["account_rec_1_name"] = best["product_name"]
            recommendation_payload["account_rec_1_reason"] = best_reason
            recommendation_payload["account_rec_2_name"] = next_best["product_name"] if next_best else None
            recommendation_payload["account_rec_2_reason"] = next_reason

        elif option == 2:
            recommendation_payload["connect_rec_1_name"] = best["product_name"]
            recommendation_payload["connect_rec_1_reason"] = best_reason
            recommendation_payload["connect_rec_2_name"] = next_best["product_name"] if next_best else None
            recommendation_payload["connect_rec_2_reason"] = next_reason

        elif option == 4:
            recommendation_payload["loan_rec_1_name"] = best["product_name"]
            recommendation_payload["loan_rec_1_reason"] = best_reason
            recommendation_payload["loan_rec_2_name"] = next_best["product_name"] if next_best else None
            recommendation_payload["loan_rec_2_reason"] = next_reason

    # =================================================
    # OPTION 3 → INSURANCE PROFILE BASED
    # =================================================

    insurance_products = (
        supabase
        .table("insurance_products")
        .select("*")
        .eq("active", True)
        .execute()
        .data or []
    )

    categories = (
        supabase
        .table("insurance_categories")
        .select("*")
        .execute()
        .data or []
    )

    category_map = {c["id"]: c["name"] for c in categories}

    scored_products = []

    for product in insurance_products:

        category_name = category_map.get(product["category_id"], "")

        score_rank = 0

        # ------------------------------
        # Relevance Rules
        # ------------------------------
        if category_name == "Car Insurance" and client.get("owns_car"):
            score_rank += 3

        if category_name == "Home Insurance" and client.get("owns_home"):
            score_rank += 3

        if category_name == "Life Insurance":
            score_rank += 2

        if category_name == "Health Insurance":
            score_rank += 1

        scored_products.append((score_rank, product))

    scored_products.sort(key=lambda x: x[0], reverse=True)

    if scored_products:

        best_insurance = scored_products[0][1]
        next_insurance = scored_products[1][1] if len(scored_products) > 1 else None

        recommendation_payload["insurance_rec_1_name"] = best_insurance["name"]
        recommendation_payload["insurance_rec_1_reason"] = best_insurance.get("description")

        if next_insurance:
            recommendation_payload["insurance_rec_2_name"] = next_insurance["name"]
            recommendation_payload["insurance_rec_2_reason"] = next_insurance.get("description")

    # =================================================
    # SAVE
    # =================================================
    if update_mode:
        supabase.table("fnb_recommendations").upsert(
    recommendation_payload,
    on_conflict="customer_id"
).execute()
    else:
        supabase.table("fnb_recommendations") \
            .insert(recommendation_payload) \
            .execute()


# -------------------------------------------------
# Fetch Recommendation Based on Primary Interest
# -------------------------------------------------
def get_recommendation_for_option(client: dict):

    client_id = client["id"]
    raw_interest = client.get("primary_interest")

    # -------------------------------------------------
    # Convert Primary Interest To Option Number
    # -------------------------------------------------
    option_map = {
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "FNB Accounts": 1,
        "FNB Connect": 2,
        "FNB Insurance": 3,
        "FNB Loan": 4,
        "Accounts": 1,
        "Connect": 2,
        "Insurance": 3,
        "Loan": 4
    }

    option = option_map.get(str(raw_interest))

    if not option:
        return None

    # -------------------------------------------------
    # Fetch Stored Recommendation
    # -------------------------------------------------
    rec_data = (
        supabase
        .table("fnb_recommendations")
        .select("*")
        .eq("customer_id", client_id)
        .execute()
        .data
    )

    if not rec_data:
        return None

    rec = rec_data[0]

    mapping = {
        1: ("account_rec_1_name", "account_rec_1_reason",
            "account_rec_2_name", "account_rec_2_reason"),
        2: ("connect_rec_1_name", "connect_rec_1_reason",
            "connect_rec_2_name", "connect_rec_2_reason"),
        3: ("insurance_rec_1_name", "insurance_rec_1_reason",
            "insurance_rec_2_name", "insurance_rec_2_reason"),
        4: ("loan_rec_1_name", "loan_rec_1_reason",
            "loan_rec_2_name", "loan_rec_2_reason"),
    }

    fields = mapping.get(option)

    if not fields:
        return None

    return {
        "best_product": rec.get(fields[0]),
        "best_reason": rec.get(fields[1]),
        "next_best_product": rec.get(fields[2]),
        "next_best_reason": rec.get(fields[3]),
    }
