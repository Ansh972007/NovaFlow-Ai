INDUSTRY_SCHEMAS = {
    "retail": {
        "entities": ["Customer", "Order", "Product", "Inventory"],
        "kpis": ["conversion_rate", "average_order_value"],
        "rules": ["validate_stock_availability", "apply_coupon_discount"]
    },
    "healthcare": {
        "entities": ["Patient", "Appointment", "EHR_Record", "Prescription"],
        "kpis": ["patient_wait_time", "readmission_rate"],
        "rules": ["check_hipaa_compliance", "verify_insurance_eligibility"]
    },
    "finance": {
        "entities": ["Account", "Transaction", "Loan", "Portfolio"],
        "kpis": ["loan_to_value", "transaction_velocity"],
        "rules": ["kyc_aml_verification", "detect_fraud_patterns"]
    }
}


def get_ontology_schema(industry: str) -> dict:
    """Retrieve database templates and compliance rules for a specified business vertical."""
    return INDUSTRY_SCHEMAS.get(industry.lower(), {
        "entities": ["GenericItem", "EventLog"],
        "kpis": ["throughput_rate"],
        "rules": ["validate_generic_schema"]
    })
