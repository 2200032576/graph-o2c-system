import os
from groq import Groq

# ==============================
# 🔑 CLIENT
# ==============================
client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))


# ==============================
# 🧠 SCHEMA
# ==============================
SCHEMA = """
Neo4j Graph Schema:
  Nodes   : Customer, SalesOrder, SalesOrderItem, Product, Delivery, Invoice, Payment
  Edges   :
    (Customer)-[:PLACED]->(SalesOrder)
    (SalesOrder)-[:HAS_ITEM]->(SalesOrderItem)
    (SalesOrderItem)-[:OF_PRODUCT]->(Product)
    (SalesOrderItem)-[:DELIVERED_IN]->(Delivery)
    (SalesOrderItem)-[:BILLED_IN]->(Invoice)
    (Invoice)-[:PAID_BY]->(Payment)
"""


# ==============================
# 🛑 GUARDRAIL
# ==============================
GUARDRAIL_SYSTEM = """You are a strict topic classifier.
Allowed topic: SAP Order-to-Cash (O2C) data (orders, invoices, deliveries, payments, customers, products).

Respond ONLY with YES or NO.
"""

def is_domain_query(question: str) -> bool:
    # Fast keyword filter first
    keywords = ["order", "invoice", "delivery", "payment", "customer", "product"]
    if any(k in question.lower() for k in keywords):
        return True

    # Fallback to LLM
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": GUARDRAIL_SYSTEM},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_tokens=5,
    )
    return resp.choices[0].message.content.strip().upper().startswith("YES")


# ==============================
# 🧠 CYPHER GENERATION
# ==============================
CYPHER_SYSTEM = f"""
You are an expert Neo4j Cypher query generator.

{SCHEMA}

STRICT RULES:
- Output ONLY raw Cypher. No explanation.
- MUST start with MATCH.
- Use LIMIT 50 unless specified.
- NEVER use CREATE, DELETE, MERGE, SET.
- NEVER use generic (n)-->() patterns.

RELATIONSHIPS (IMPORTANT):
(SalesOrderItem)-[:OF_PRODUCT]->(Product)
(SalesOrderItem)-[:DELIVERED_IN]->(Delivery)
(SalesOrderItem)-[:BILLED_IN]->(Invoice)
(Invoice)-[:PAID_BY]->(Payment)

VARIABLE RULES:
- Do NOT reuse variables
- Use:
  i = Invoice
  si = SalesOrderItem
  p = Product
  d = Delivery
  pay = Payment

BUSINESS LOGIC:
- unpaid → Invoice without Payment
- undelivered → Item without Delivery
- unbilled → Item without Invoice

JOIN RULE:
- Product ↔ Invoice must go through SalesOrderItem

EXAMPLES:

Unpaid invoices:
MATCH (i:Invoice)
OPTIONAL MATCH (i)-[:PAID_BY]->(pay:Payment)
WHERE pay IS NULL
RETURN i LIMIT 50

Top products in invoices:
MATCH (si:SalesOrderItem)-[:OF_PRODUCT]->(p:Product)
MATCH (si)-[:BILLED_IN]->(i:Invoice)
RETURN p.id, COUNT(*) AS count
ORDER BY count DESC
LIMIT 5

Full flow:
MATCH (c:Customer)-[:PLACED]->(o:SalesOrder)
-[:HAS_ITEM]->(si:SalesOrderItem)
OPTIONAL MATCH (si)-[:DELIVERED_IN]->(d:Delivery)
OPTIONAL MATCH (si)-[:BILLED_IN]->(i:Invoice)
OPTIONAL MATCH (i)-[:PAID_BY]->(pay:Payment)
RETURN c,o,si,d,i,pay LIMIT 50
"""

def generate_cypher(question: str) -> str:
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": CYPHER_SYSTEM},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_tokens=400,
    )

    query = resp.choices[0].message.content.strip()
    query = query.replace("```cypher", "").replace("```", "").strip()
    return query


# ==============================
# 🔍 VALIDATION
# ==============================
def validate_cypher(query: str):
    q = query.lower()

    if not q.startswith("match"):
        return False, "Query must start with MATCH"

    if any(x in q for x in ["create", "delete", "merge", "set"]):
        return False, "Unsafe query detected"

    if "(n)" in q:
        return False, "Generic query not allowed"

    return True, "OK"


# ==============================
# 🧾 RESULT → NATURAL LANGUAGE
# ==============================
ANSWER_SYSTEM = """
You are a business assistant for SAP O2C data.

Given:
- User question
- Cypher query
- Raw results

Return a clear 2-3 sentence answer based ONLY on data.

If empty → explain possible reason (missing data, not loaded, etc.)
"""

def generate_answer(question: str, cypher: str, results: list) -> str:
    preview = str(results[:10])

    prompt = f"""
Question: {question}

Cypher:
{cypher}

Results:
{preview}
"""

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=300,
    )

    return resp.choices[0].message.content.strip()