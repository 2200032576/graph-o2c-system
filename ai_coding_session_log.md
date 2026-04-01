# AI Coding Session Log — O2C Graph Intelligence System
**Tool:** Claude (claude.ai)
**Project:** Graph-Based Data Modeling and Query System
**Dates:** 24 March 2026 – 26 March 2026

---

## Session 1 — 24 March 2026, 10:15 AM

**Prompt:**
> I have a SAP Order-to-Cash dataset with sales orders, deliveries, invoices, and payments. I want to build a graph database using Neo4j. How should I model the nodes and relationships?

**AI Response Summary:**
Suggested node types: Customer, SalesOrder, SalesOrderItem, Product, Delivery, Invoice, Payment. Proposed relationships: PLACED, HAS_ITEM, OF_PRODUCT, DELIVERED_IN, BILLED_IN, PAID_BY. Explained why graph DB is better than relational for tracing O2C flows.

**Outcome:** Finalized graph schema.

---

## Session 2 — 24 March 2026, 11:40 AM

**Prompt:**
> Write a Python script to load JSONL files from the SAP dataset into Neo4j using MERGE statements. I need to load sales order headers, items, deliveries, billing documents, and payments.

**AI Response Summary:**
Generated `load_data.py` with separate sections for each entity. Used MERGE to avoid duplicates. Added composite key for SalesOrderItem (`salesOrder/salesOrderItem`). Handled null reference fields with `.get()` fallbacks.

**Outcome:** `load_data.py` working, 429 nodes and 407 relationships loaded into AuraDB.

---

## Session 3 — 24 March 2026, 2:30 PM

**Prompt:**
> How do I connect Neo4j AuraDB from Python? My local bolt:// URI is not working with the cloud instance.

**AI Response Summary:**
Explained difference between `bolt://` (local) and `neo4j+s://` (AuraDB TLS). Updated `db.py` to use environment variables with fallback defaults. Added `get_graph_sample()` and `get_node_neighbors()` helper functions.

**Outcome:** `db.py` successfully connecting to AuraDB.

---

## Session 4 — 24 March 2026, 4:00 PM

**Prompt:**
> Build a Streamlit UI with two panels — left panel shows a pyvis graph visualization with expandable nodes, right panel is a chat interface for natural language queries. Dark theme.

**AI Response Summary:**
Generated full `app.py` with two-column layout. Used pyvis Network for graph rendering inside `components.html`. Added node color map per entity type. Built chat bubble UI with CSS. Added sidebar with graph stats and example queries.

**Outcome:** Full UI working locally.

---

## Session 5 — 24 March 2026, 6:15 PM

**Prompt:**
> Write the LLM integration using Groq API. It should take a natural language question, generate a Cypher query using schema-aware prompting, run it on Neo4j, and return a human-readable answer. Also add guardrails to reject off-topic questions.

**AI Response Summary:**
Generated `llm.py` with three functions: `is_domain_query()` (guardrail using keyword filter + LLM fallback), `generate_cypher()` (schema-injected system prompt with strict rules), `generate_answer()` (converts raw results to business language). Added Cypher validation to block write operations.

**Outcome:** End-to-end NL → Cypher → Answer pipeline working.

---

## Session 6 — 25 March 2026, 9:00 AM

**Prompt:**
> The LLM is generating invalid Cypher with GROUP BY instead of WITH. Fix the prompting strategy.

**AI Response Summary:**
Identified that the LLM was confusing SQL and Cypher syntax. Updated CYPHER_SYSTEM prompt with explicit examples using WITH for aggregation. Added variable naming rules to avoid conflicts. Added JOIN RULE comment explaining Product ↔ Invoice must go through SalesOrderItem.

**Outcome:** Cypher generation accuracy improved significantly.

---

## Session 7 — 25 March 2026, 11:30 AM

**Prompt:**
> How do I deploy this Streamlit app with Neo4j AuraDB? The app uses environment variables for credentials.

**AI Response Summary:**
Explained Streamlit Community Cloud deployment. Updated `db.py` and `llm.py` to read from `st.secrets` with fallback to env vars. Created `.streamlit/secrets.toml` structure. Added `secrets.toml` to `.gitignore`. Gave step-by-step deployment instructions.

**Outcome:** App deployed at `https://graph-o2c-system-ihsbjmqsxjbjaqhpqrfatd.streamlit.app`

---

## Session 8 — 25 March 2026, 2:00 PM

**Prompt:**
> ModuleNotFoundError: pyvis not found on Streamlit Cloud. Also groq module missing.

**AI Response Summary:**
Identified missing packages in `requirements.txt`. Added `pyvis`, `groq`, `streamlit`, `neo4j`, `pandas`, `python-dotenv`, `requests` to requirements file.

**Outcome:** Deployment succeeded after push.

---

## Session 9 — 26 March 2026, 9:00 AM

**Prompt:**
> Pressing Enter in the chat input doesn't submit the query, I have to click the button manually. Fix this in Streamlit.

**AI Response Summary:**
Explained Streamlit's limitation with Enter key. Implemented workaround using session state to detect input changes and auto-trigger send. Split input and button into columns for better UI layout.

**Outcome:** Enter key now submits queries.

---

## Session 10 — 26 March 2026, 10:30 AM

**Prompt:**
> Update the example queries in the sidebar to cover basic queries, business insights, analytics, flow tracing, and edge cases.

**AI Response Summary:**
Reorganized example queries into 5 categories: Basic, Business Insights, Analytics, Flow, and Edge Cases. Added 17 queries total covering unpaid invoices, incomplete flows, product analytics, and full O2C lifecycle tracing.

**Outcome:** Final version pushed and deployed.

---

## Key Architectural Decisions (AI-Assisted)

| Decision | Rationale |
|---|---|
| Neo4j AuraDB (Free) | Cloud-hosted, no infra management, free tier sufficient |
| Groq (llama-3.1-8b-instant) | Fast inference, free tier, good Cypher generation |
| Streamlit | Rapid UI development, built-in deployment, Python-native |
| Schema-aware prompting | Injects full graph schema into every LLM call for accuracy |
| Keyword + LLM guardrail | Fast keyword filter first, LLM fallback for ambiguous queries |
| MERGE in load_data.py | Idempotent loading, safe to re-run without duplicates |

---

## Debugging Patterns

- **Auth errors** → Switched from hardcoded env vars to `st.secrets` for cloud deployment
- **Invalid Cypher** → Added explicit WITH aggregation examples to system prompt
- **Missing modules** → Iteratively fixed `requirements.txt` based on deployment logs
- **Enter key** → Used session state diff to detect new input and auto-trigger send
