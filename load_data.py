import pandas as pd
import os
from db import run_query

# =========================
# CLEAR DATABASE
# =========================
print("Clearing existing data...")
run_query("MATCH (n) DETACH DELETE n")
print("✅ Database cleared")

DATA_ROOT = "data/sap-order-to-cash-dataset/sap-o2c-data/"
LIMIT = 500  # load more rows for richer graph

def first_file(path):
    files = [f for f in os.listdir(path) if f.endswith(".jsonl") or f.endswith(".json")]
    return os.path.join(path, files[0])

# =========================
# LOAD SALES ORDERS
# =========================
df = pd.read_json(first_file(DATA_ROOT + "sales_order_headers/"), lines=True).head(LIMIT)
print(f"Loading {len(df)} Sales Orders...")

for _, row in df.iterrows():
    run_query("""
    MERGE (c:Customer {id: $cust})
    MERGE (o:SalesOrder {id: $oid})
      ON CREATE SET o.amount = $amt
    MERGE (c)-[:PLACED]->(o)
    """, {
        "cust": str(row["soldToParty"]),
        "oid":  str(row["salesOrder"]),
        "amt":  float(row["totalNetAmount"]) if pd.notnull(row.get("totalNetAmount")) else 0.0,
    })
print("✅ SalesOrders inserted")

# =========================
# LOAD ITEMS + PRODUCTS
# =========================
items_df = pd.read_json(first_file(DATA_ROOT + "sales_order_items/"), lines=True).head(LIMIT)
print(f"Loading {len(items_df)} Items...")

for _, row in items_df.iterrows():
    # Composite key: salesOrder + salesOrderItem  (e.g. "10000001/10")
    item_id = f"{row['salesOrder']}/{row['salesOrderItem']}"
    run_query("""
    MERGE (o:SalesOrder {id: $oid})
    MERGE (i:SalesOrderItem {id: $iid})
      ON CREATE SET i.salesOrder = $oid, i.itemNum = $item_num
    MERGE (p:Product {id: $pid})
    MERGE (o)-[:HAS_ITEM]->(i)
    MERGE (i)-[:OF_PRODUCT]->(p)
    """, {
        "oid":      str(row["salesOrder"]),
        "iid":      item_id,
        "item_num": str(row["salesOrderItem"]),
        "pid":      str(row["material"]),
    })
print("✅ Items + Products inserted")

# =========================
# LOAD DELIVERIES
# =========================
delivery_df = pd.read_json(first_file(DATA_ROOT + "outbound_delivery_items/"), lines=True).head(LIMIT)
print(f"Loading {len(delivery_df)} Delivery items...")

for _, row in delivery_df.iterrows():
    ref_doc  = row.get("referenceSDDocument")  or row.get("referenceSdDocument")  or row.get("salesOrder")
    ref_item = row.get("referenceSDDocumentItem") or row.get("referenceSdDocumentItem") or row.get("salesOrderItem")
    if pd.isnull(ref_doc) or pd.isnull(ref_item):
        continue
    item_id = f"{ref_doc}/{ref_item}"
    run_query("""
    MERGE (i:SalesOrderItem {id: $iid})
    MERGE (d:Delivery {id: $did})
    MERGE (i)-[:DELIVERED_IN]->(d)
    """, {
        "iid": item_id,
        "did": str(row["deliveryDocument"]),
    })
print("✅ Deliveries inserted")

# =========================
# LOAD BILLING / INVOICES
# =========================
billing_df = pd.read_json(first_file(DATA_ROOT + "billing_document_items/"), lines=True).head(LIMIT)
print(f"Loading {len(billing_df)} Billing items...")

for _, row in billing_df.iterrows():
    ref_doc  = row.get("referenceSDDocument")  or row.get("referenceSdDocument")  or row.get("salesOrder")
    ref_item = row.get("referenceSDDocumentItem") or row.get("referenceSdDocumentItem") or row.get("salesOrderItem")
    if pd.isnull(ref_doc) or pd.isnull(ref_item):
        continue
    item_id = f"{ref_doc}/{ref_item}"
    run_query("""
    MERGE (i:SalesOrderItem {id: $iid})
    MERGE (b:Invoice {id: $bid})
      ON CREATE SET b.amount = $amt
    MERGE (i)-[:BILLED_IN]->(b)
    """, {
        "iid": item_id,
        "bid": str(row["billingDocument"]),
        "amt": float(row["netAmount"]) if pd.notnull(row.get("netAmount")) else 0.0,
    })
print("✅ Invoices inserted")

# =========================
# LOAD PAYMENTS
# =========================
payments_df = pd.read_json(first_file(DATA_ROOT + "payments_accounts_receivable/"), lines=True).head(LIMIT)
print(f"Loading {len(payments_df)} Payments...")

for _, row in payments_df.iterrows():
    invoice_id = row.get("referenceDocument") or row.get("billingDocument") or row.get("assignmentReference")
    if pd.isnull(invoice_id):
        continue
    run_query("""
    MERGE (b:Invoice {id: $bid})
    MERGE (p:Payment {id: $pid})
      ON CREATE SET p.amount = $amt
    MERGE (b)-[:PAID_BY]->(p)
    """, {
        "bid": str(invoice_id),
        "pid": str(row.get("accountingDocument", "UNKNOWN")),
        "amt": float(row.get("amount", 0)) if pd.notnull(row.get("amount")) else 0.0,
    })
print("✅ Payments inserted")

# =========================
# VERIFY
# =========================
print("\n📊 Final counts:")
for label in ["Customer", "SalesOrder", "SalesOrderItem", "Product", "Delivery", "Invoice", "Payment"]:
    count = run_query(f"MATCH (n:{label}) RETURN count(n) AS c")[0]["c"]
    print(f"  {label}: {count}")

print("\n🎉 FULL O2C PIPELINE READY")