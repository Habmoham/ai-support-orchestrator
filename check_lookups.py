import json
import os

print("=== Checking customers.json (billing) ===")
customers_path = os.path.join("mock_data", "customers.json")
print(f"Exists: {os.path.exists(customers_path)}")
if os.path.exists(customers_path):
    with open(customers_path, "r") as f:
        data = json.load(f)
    for c in data["customers"]:
        print(f"  {c['email']!r}")
    target = "sarah.chen@example.com"
    match = any(c["email"].lower() == target.lower() for c in data["customers"])
    print(f"Match for {target!r}: {match}")

print("\n=== Checking orders.json (refund) ===")
orders_path = os.path.join("mock_data", "orders.json")
print(f"Exists: {os.path.exists(orders_path)}")
if os.path.exists(orders_path):
    with open(orders_path, "r") as f:
        data = json.load(f)
    for o in data["orders"]:
        print(f"  {o['customer_email']!r}")
    target = "priya.nair@example.com"
    match = any(o["customer_email"].lower() == target.lower() for o in data["orders"])
    print(f"Match for {target!r}: {match}")

print("\n=== Checking what DATA_PATH resolves to from inside agents/ ===")
billing_data_path = os.path.join(os.path.dirname(os.path.abspath("agents/billing.py")), "..", "mock_data", "customers.json")
billing_data_path = os.path.normpath(billing_data_path)
print(f"billing.py would look at: {billing_data_path}")
print(f"Exists: {os.path.exists(billing_data_path)}")

refund_data_path = os.path.join(os.path.dirname(os.path.abspath("agents/refund.py")), "..", "mock_data", "orders.json")
refund_data_path = os.path.normpath(refund_data_path)
print(f"refund.py would look at: {refund_data_path}")
print(f"Exists: {os.path.exists(refund_data_path)}")
