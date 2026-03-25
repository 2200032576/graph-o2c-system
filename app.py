import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

from db  import run_query, get_graph_sample, get_node_neighbors
from llm import is_domain_query, generate_cypher, generate_answer

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="O2C Graph Intelligence",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .stApp { background: #0f1117; }
  section[data-testid="stSidebar"] { background: #161b27; border-right: 1px solid #2a2f3e; }
  .chat-bubble-user {
    background: #1e3a5f; color: #e8f4fd; padding: 10px 14px;
    border-radius: 12px 12px 4px 12px; margin: 6px 0; max-width: 85%;
    margin-left: auto; font-size: 14px;
  }
  .chat-bubble-bot {
    background: #1a2236; color: #d4e5f7; padding: 10px 14px;
    border-radius: 12px 12px 12px 4px; margin: 6px 0; max-width: 90%;
    font-size: 14px; border-left: 3px solid #3b82f6;
  }
  .cypher-box {
    background: #0d1117; border: 1px solid #30363d; border-radius: 8px;
    padding: 10px 14px; font-family: monospace; font-size: 12px;
    color: #79c0ff; margin: 6px 0;
  }
  .metric-card {
    background: #1a2236; border: 1px solid #2a3550; border-radius: 10px;
    padding: 16px; text-align: center;
  }
  .metric-card .num { font-size: 28px; font-weight: 700; color: #60a5fa; }
  .metric-card .lbl { font-size: 12px; color: #8899aa; margin-top: 2px; }
  .section-title { color: #94a3b8; font-size: 11px; font-weight: 600;
    letter-spacing: 1px; text-transform: uppercase; margin: 16px 0 8px; }
</style>
""", unsafe_allow_html=True)

# ── Node colour map ──────────────────────────────────────────────────────────
NODE_COLORS = {
    "Customer":      "#f59e0b",
    "SalesOrder":    "#3b82f6",
    "SalesOrderItem":"#8b5cf6",
    "Product":       "#10b981",
    "Delivery":      "#06b6d4",
    "Invoice":       "#f97316",
    "Payment":       "#22c55e",
}
DEFAULT_COLOR = "#94a3b8"

# ── Pyvis graph builder ──────────────────────────────────────────────────────
def build_graph_html(rows: list, height: str = "520px") -> str:
    net = Network(height=height, width="100%", bgcolor="#0f1117", font_color="#e2e8f0")
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.005,
          "springLength": 120,
          "springConstant": 0.08
        },
        "solver": "forceAtlas2Based",
        "stabilization": { "iterations": 150 }
      },
      "edges": {
        "color": { "color": "#334155", "highlight": "#60a5fa" },
        "font": { "size": 10, "color": "#64748b" },
        "smooth": { "type": "continuous" },
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } }
      },
      "nodes": {
        "font": { "size": 11, "color": "#e2e8f0" },
        "borderWidth": 1.5,
        "shadow": false
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "hideEdgesOnDrag": true
      }
    }
    """)

    seen_nodes = set()
    seen_edges = set()

    for row in rows:
        src_id    = row.get("src_id")
        src_label = row.get("src_label", "Node")
        src_name  = str(row.get("src_name") or src_id or "?")
        tgt_id    = row.get("tgt_id")
        tgt_label = row.get("tgt_label", "Node")
        tgt_name  = str(row.get("tgt_name") or tgt_id or "?")
        rel       = row.get("rel", "")

        if src_id not in seen_nodes:
            color = NODE_COLORS.get(src_label, DEFAULT_COLOR)
            net.add_node(src_id, label=src_name[:18],
                         title=f"{src_label}: {src_name}",
                         color=color, size=18)
            seen_nodes.add(src_id)

        if tgt_id not in seen_nodes:
            color = NODE_COLORS.get(tgt_label, DEFAULT_COLOR)
            net.add_node(tgt_id, label=tgt_name[:18],
                         title=f"{tgt_label}: {tgt_name}",
                         color=color, size=18)
            seen_nodes.add(tgt_id)

        edge_key = (src_id, tgt_id, rel)
        if edge_key not in seen_edges:
            net.add_edge(src_id, tgt_id, label=rel, title=rel)
            seen_edges.add(edge_key)

    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
        net.save_graph(f.name)
        html = f.read() if False else open(f.name, encoding="utf-8").read()
    os.unlink(f.name)
    return html

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔗 O2C Graph Intelligence")
    st.markdown("---")

    # Stats
    st.markdown('<div class="section-title">Graph Stats</div>', unsafe_allow_html=True)
    try:
        counts = {
            "Customer":      run_query("MATCH (n:Customer) RETURN count(n) AS c")[0]["c"],
            "SalesOrder":    run_query("MATCH (n:SalesOrder) RETURN count(n) AS c")[0]["c"],
            "Invoice":       run_query("MATCH (n:Invoice) RETURN count(n) AS c")[0]["c"],
            "Payment":       run_query("MATCH (n:Payment) RETURN count(n) AS c")[0]["c"],
        }
        cols = st.columns(2)
        for i, (label, cnt) in enumerate(counts.items()):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="num">{cnt}</div>
                  <div class="lbl">{label}s</div>
                </div>""", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Neo4j not reachable: {e}")

    st.markdown("---")

    # Example queries
    st.markdown('<div class="section-title">Example Queries</div>', unsafe_allow_html=True)
    examples = [
        "Which products are associated with the highest number of billing documents?",
        "Trace the full flow of billing document 90000001",
        "Show sales orders that were delivered but not billed",
        "Which customers have placed the most orders?",
        "Show invoices with no payment",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state["pending_query"] = ex

    st.markdown("---")
    st.markdown('<div class="section-title">Legend</div>', unsafe_allow_html=True)
    for label, color in NODE_COLORS.items():
        st.markdown(
            f'<span style="display:inline-block;width:10px;height:10px;'
            f'border-radius:50%;background:{color};margin-right:6px"></span>'
            f'<span style="font-size:12px;color:#94a3b8">{label}</span><br>',
            unsafe_allow_html=True
        )

# ── Main layout: two columns ─────────────────────────────────────────────────
left_col, right_col = st.columns([6, 5], gap="medium")

# ── LEFT: Graph Visualizer ───────────────────────────────────────────────────
with left_col:
    st.markdown("### 🕸️ Graph Explorer")

    graph_tabs = st.tabs(["Overview", "Expand Node"])

    with graph_tabs[0]:
        graph_limit = st.slider("Nodes to display", 30, 300, 120, 10, key="glimit")
        if st.button("🔄 Refresh Graph", use_container_width=True):
            st.cache_data.clear()

        @st.cache_data(ttl=60)
        def cached_graph(limit):
            return get_graph_sample(limit)

        with st.spinner("Loading graph..."):
            try:
                rows = cached_graph(graph_limit)
                if rows:
                    html = build_graph_html(rows, height="480px")
                    components.html(html, height=490, scrolling=False)
                    st.caption(f"{len(rows)} relationships shown")
                else:
                    st.info("No data in graph yet. Run load_data.py first.")
            except Exception as e:
                st.error(f"Graph error: {e}")

    with graph_tabs[1]:
        st.markdown("Expand all neighbours of a specific node.")
        node_label = st.selectbox("Node type", list(NODE_COLORS.keys()), key="exp_label")
        node_id    = st.text_input("Node ID (e.g. 10000001)", key="exp_id")
        if st.button("Expand", use_container_width=True) and node_id:
            with st.spinner("Expanding..."):
                try:
                    rows = get_node_neighbors(node_id, node_label)
                    if rows:
                        html = build_graph_html(rows, height="440px")
                        components.html(html, height=450, scrolling=False)
                    else:
                        st.warning("No neighbours found for that node.")
                except Exception as e:
                    st.error(f"Expand error: {e}")

# ── RIGHT: Chat Interface ────────────────────────────────────────────────────
with right_col:
    st.markdown("### 💬 Natural Language Query")

    # Session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = ""

    # Chat history display
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style="color:#4a5568;font-size:13px;padding:20px 0">
            Ask anything about your O2C data — orders, deliveries,
            invoices, payments, customers, and products.<br><br>
            Try one of the example queries on the left ←
            </div>
            """, unsafe_allow_html=True)
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>',
                            unsafe_allow_html=True)
            else:
                answer  = msg.get("answer", "")
                cypher  = msg.get("cypher", "")
                raw_res = msg.get("raw", [])
                st.markdown(f'<div class="chat-bubble-bot">{answer}</div>',
                            unsafe_allow_html=True)
                if cypher:
                    with st.expander("🔍 Cypher query", expanded=False):
                        st.code(cypher, language="cypher")
                if raw_res:
                    with st.expander(f"📊 Raw data ({len(raw_res)} rows)", expanded=False):
                        st.dataframe(raw_res, use_container_width=True)

    st.markdown("---")

    # Input — pick up pending query from sidebar buttons
    default_val = st.session_state.pop("pending_query", "") if st.session_state.get("pending_query") else ""
    user_input  = st.text_input(
        "Ask a question…",
        value=default_val,
        placeholder="e.g. Which products appear in the most invoices?",
        key="chat_input",
        label_visibility="collapsed",
    )
    send = st.button("Send ➤", use_container_width=True, type="primary")

    if send and user_input.strip():
        question = user_input.strip()

        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})

        with st.spinner("Thinking..."):
            # Guardrail check
            if not is_domain_query(question):
                answer = ("⚠️ This system is designed to answer questions about the "
                          "O2C dataset only (orders, deliveries, invoices, payments, "
                          "customers, products). Please ask a dataset-related question.")
                st.session_state.messages.append({
                    "role":   "assistant",
                    "answer": answer,
                    "cypher": "",
                    "raw":    [],
                })
            else:
                try:
                    # Generate Cypher
                    cypher = generate_cypher(question)

                    # Safety: read-only guard
                    forbidden = ["create", "delete", "set", "merge", "drop", "remove"]
                    if any(kw in cypher.lower() for kw in forbidden):
                        raise ValueError("Generated query contains write operations — blocked.")

                    # Run query
                    results = run_query(cypher)

                    # Generate NL answer
                    answer = generate_answer(question, cypher, results)

                    st.session_state.messages.append({
                        "role":   "assistant",
                        "answer": answer,
                        "cypher": cypher,
                        "raw":    results,
                    })
                except Exception as e:
                    st.session_state.messages.append({
                        "role":   "assistant",
                        "answer": f"❌ Error: {e}",
                        "cypher": "",
                        "raw":    [],
                    })

        st.rerun()