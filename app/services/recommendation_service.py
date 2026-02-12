from datetime import datetime
from app.db.supabase import supabase


# -------------------------------------------------
# Risk Band Calculator
# -------------------------------------------------
def calculate_risk_band(score: int):
    if score >= 700:
        return "LOW"
    elif score >= 600:
        return "MEDIUM"
    return "HIGH"


# -------------------------------------------------
# Interest Mapping
# -------------------------------------------------
def map_interest_to_option(primary_interest):

    interest_map = {
        "Account Opening": 1,
        "FNB Connect": 2,
        "Insurance": 3,
        "FNB Loan": 4,
        "Loan": 4
    }

    if isinstance(primary_interest, int):
        return primary_interest

    return interest_map.get(primary_interest)


# -------------------------------------------------
# Category Mapping
# -------------------------------------------------
def get_category_prefix(option: int):
    mapping = {
        1: "account",
        2: "connect",
        3: "insurance",
        4: "loan"
    }
    return mapping.get(option)


# -------------------------------------------------
# Clean Benefit-Based Reason Builder
# -------------------------------------------------
def build_reason_from_benefits(product: dict):

    benefits = product.get("benefits") or []

    if not benefits:
        return "Strong value offering"

    top = benefits[:3]
    return ", ".join(top)


# -------------------------------------------------
# Main Recommendation Engine
# -------------------------------------------------
def recommend(client: dict):

    client_id = client["id"]

    option = map_interest_to_option(client.get("primary_interest"))

    if not option:
        return None, None

    category_prefix = get_category_prefix(option)

    if not category_prefix:
        return None, None

    # -------------------------------------------------
    # Load Bureau Profile
    # -------------------------------------------------
    bureau_response = (
        supabase
        .table("bureau_profiles")
        .select("*")
        .eq("user_id", client_id)
        .execute()
    )

    bureau_data = bureau_response.data

    if not bureau_data:
        return None, None

    bureau = bureau_data[0]

    if bureau.get("fraud_id_verified") is False:
        return {
            "product_name": "Application Blocked",
            "reason": "Identity verification failed"
        }, None

    presage_score = bureau.get("presage_score", 0)

    # -------------------------------------------------
    # Load Products
    # -------------------------------------------------
    product_response = (
        supabase
        .table("products")
        .select("*")
        .eq("option", option)
        .execute()
    )

    products = product_response.data

    if not products:
        return None, None

    # -------------------------------------------------
    # Eligibility Filter
    # -------------------------------------------------
    eligible = []

    for product in products:

        rules = product.get("eligibility_rules") or {}

        min_score = rules.get("min_credit_score", 0)
        credit_required = rules.get("credit_check", False)
        employment_required = rules.get("employment_required", False)

        if credit_required and presage_score < min_score:
            continue

        if employment_required and not bureau.get("employment_status"):
            continue

        eligible.append(product)

    if not eligible:
        return None, None

    # Loan prioritisation
    if option == 4:
        loan_products = [p for p in eligible if "LOAN" in p["product_code"]]
        other_products = [p for p in eligible if "LOAN" not in p["product_code"]]
        eligible = loan_products + other_products

    eligible.sort(
        key=lambda p: p.get("eligibility_rules", {}).get("min_credit_score", 0),
        reverse=True
    )

    best = eligible[0]
    next_best = eligible[1] if len(eligible) > 1 else None

    # -------------------------------------------------
    # Store in fnb_recommendations
    # -------------------------------------------------
    existing = (
        supabase
        .table("fnb_recommendations")
        .select("id")
        .eq("customer_id", client_id)
        .execute()
        .data
    )

    update_payload = {
        "customer_id": client_id,
        "generated_at": datetime.utcnow().isoformat(),
        "enrichment_complete": True,
        f"{category_prefix}_rec_1_name": best["product_name"],
        f"{category_prefix}_rec_1_reason": build_reason_from_benefits(best)
    }

    if next_best:
        update_payload[f"{category_prefix}_rec_2_name"] = next_best["product_name"]
        update_payload[f"{category_prefix}_rec_2_reason"] = build_reason_from_benefits(next_best)

    if existing:
        supabase.table("fnb_recommendations") \
            .update(update_payload) \
            .eq("customer_id", client_id) \
            .execute()
    else:
        update_payload["id"] = f"rec-{client_id}"
        supabase.table("fnb_recommendations") \
            .insert(update_payload) \
            .execute()

    # -------------------------------------------------
    # Return API Response
    # -------------------------------------------------
    best_product = {
        "product_name": best["product_name"],
        "benefits": best["benefits"]
    }

    next_product = None

    if next_best:
        next_product = {
            "product_name": next_best["product_name"],
            "benefits": next_best["benefits"]
        }

    return best_product, next_product
