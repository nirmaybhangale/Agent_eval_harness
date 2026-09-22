MOCK_DB = {
    "ORD-99812": {"status": "shipped", "tracking": "1Z999999999"},
    "ORD-11223": {"status": "delivered", "eligible_for_refund": True, "max_refund": 50.00},
    "ORD-55411": {"status": "processing", "tracking": None}
}

MOCK_POLICIES = {
    "laptop": "Laptops can be returned within 14 days of delivery.",
    "damaged": "Damaged goods must be reported within 48 hours for a full refund."
}

#Deterministic Mock Functions
async def check_order_status(order_id: str) -> str:
    """Returns the shipping status of an order."""
    record = MOCK_DB.get(order_id)
    if record:
        return f"Order {order_id} is {record['status']}."
    return f"Order {order_id} not found."

async def issue_refund(order_id: str, amount: float) -> str:
    """Issues a refund for an order if eligible and within limits."""
    record = MOCK_DB.get(order_id)
    if not record:
        return f"Cannot issue refund: Order {order_id} not found."
    if not record.get("eligible_for_refund"):
        return f"Order {order_id} is not eligible for a refund."
    if amount > record.get("max_refund", 0):
        return f"Requested amount ${amount} exceeds maximum allowed refund of ${record['max_refund']}."
    
    return f"Successfully processed refund of ${amount:.2f} for order {order_id}."

async def search_store_policies(query: str) -> str:
    """Searches the knowledge base for store policies."""
    query_lower = query.lower()
    for key, policy in MOCK_POLICIES.items():
        if key in query_lower:
            return policy
    return "No specific policy found. Standard 30-day return policy applies."