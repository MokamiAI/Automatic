def get_mock_xds_profile(id_number: str):
    return {
        "monthly_income": 18000,
        "employment_status": "Employed",
        "credit_score": 640,
        "has_existing_loans": True,
        "raw": {
            "source": "XDS",
            "id_number": id_number,
            "risk_flag": "LOW"
        }
    }
