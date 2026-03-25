import os
from neo4j import GraphDatabase

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

def run_query(cypher: str, params: dict = None):
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]

def get_graph_sample(limit: int = 150):
    cypher = f"""
    MATCH (n)-[r]->(m)
    RETURN
        id(n)        AS src_id,
        labels(n)[0] AS src_label,
        n.id         AS src_name,
        type(r)      AS rel,
        id(m)        AS tgt_id,
        labels(m)[0] AS tgt_label,
        m.id         AS tgt_name
    LIMIT {limit}
    """
    return run_query(cypher)

def get_node_neighbors(node_id: str, node_label: str, limit: int = 40):
    cypher = """
    MATCH (n {id: $node_id})-[r]-(m)
    RETURN
        id(n)        AS src_id,
        labels(n)[0] AS src_label,
        n.id         AS src_name,
        type(r)      AS rel,
        id(m)        AS tgt_id,
        labels(m)[0] AS tgt_label,
        m.id         AS tgt_name
    LIMIT $limit
    """
    return run_query(cypher, {"node_id": node_id, "limit": limit})