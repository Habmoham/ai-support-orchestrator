import os
import json

# Mirrors the exact path logic used in agents/billing.py
data_path = os.path.join(os.path.dirname(os.path.abspath("agents/billing.py")), "..", "mock_data", "customers.json")
data_path = os.path.normpath(data_path)

print(f"Looking for file at: {data_path}")
print(f"File exists: {os.path.exists(data_path)}")

if os.path.exists(data_path):
    with open(data_path, "r") as f:
        data = json.load(f)
    print(f"\nCustomers found in file: {len(data.get('customers', []))}")
    for c in data.get("customers", []):
        print(f"  - {c['name']}: {c['email']}")
else:
    print("\nFile not found at that path. Checking current directory structure:")
    for root, dirs, files in os.walk("."):
        if ".git" in root or "venv" in root:
            continue
        for f in files:
            print(os.path.join(root, f))
