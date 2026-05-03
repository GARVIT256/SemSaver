"""
Neo4j graph store for concept nodes and relationships.

Relationships:
  RELATED_TO   — concepts co-occurring in the same chunk
  PREREQUISITE — concept from earlier chunk → concept from later chunk (same doc)
  PART_OF      — substring containment (e.g. "array" PART_OF "ArrayList")
"""
import logging
from neo4j import GraphDatabase
from config import settings

logger = logging.getLogger(__name__)
_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def create_indexes():
    driver = get_driver()
    with driver.session() as s:
        s.run(
            "CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)"
        )


# ── Node upsert ──────────────────────────────────────────────────────────────

def upsert_concept(name: str):
    if not name or not name.strip():
        return
    driver = get_driver()
    with driver.session() as s:
        s.run(
            "MERGE (c:Concept {name: $name})",
            name=name.strip().lower(),
        )


def upsert_concepts(names: list[str]):
    """Batch upsert multiple concept names."""
    if not names:
        return
    normalized = list({n.strip().lower() for n in names if n.strip()})
    if not normalized:
        return
    driver = get_driver()
    with driver.session() as s:
        s.run(
            "UNWIND $names AS name MERGE (c:Concept {name: name})",
            names=normalized,
        )


# ── Relationship upsert ──────────────────────────────────────────────────────

def _merge_rel(session, from_name: str, to_name: str, rel_type: str):
    from_n = from_name.strip().lower()
    to_n = to_name.strip().lower()
    if not from_n or not to_n or from_n == to_n:
        return
    # Ensure nodes exist
    session.run("MERGE (:Concept {name: $name})", name=from_n)
    session.run("MERGE (:Concept {name: $name})", name=to_n)

    if rel_type == "RELATED_TO":
        session.run(
            "MATCH (a:Concept {name:$a}),(b:Concept {name:$b}) MERGE (a)-[:RELATED_TO]->(b)",
            a=from_n, b=to_n,
        )
    elif rel_type == "PREREQUISITE":
        session.run(
            "MATCH (a:Concept {name:$a}),(b:Concept {name:$b}) MERGE (a)-[:PREREQUISITE]->(b)",
            a=from_n, b=to_n,
        )
    elif rel_type == "PART_OF":
        session.run(
            "MATCH (a:Concept {name:$a}),(b:Concept {name:$b}) MERGE (a)-[:PART_OF]->(b)",
            a=from_n, b=to_n,
        )


def build_graph_from_chunks(chunks: list[dict]):
    """
    Build graph from an ordered list of chunks using efficient batching.
    """
    if not chunks:
        return

    driver = get_driver()
    all_keywords_per_chunk = []
    unique_keywords = set()

    for chunk in chunks:
        kws = [kw.strip().lower() for kw in chunk.get("keywords", []) if kw.strip()]
        all_keywords_per_chunk.append(kws)
        unique_keywords.update(kws)

    if not unique_keywords:
        return

    with driver.session() as s:
        # 0. Batch upsert all concepts first
        s.run(
            "UNWIND $names AS name MERGE (:Concept {name: name})",
            names=list(unique_keywords)
        )

        # 1. RELATED_TO: co-occurrence within chunk
        related_to_pairs = set()
        for kws in all_keywords_per_chunk:
            for i, kw_a in enumerate(kws):
                for kw_b in kws[i + 1:]:
                    if kw_a != kw_b:
                        # Sort to treat (A, B) and (B, A) as the same for set storage
                        related_to_pairs.add(tuple(sorted((kw_a, kw_b))))

        if related_to_pairs:
            s.run(
                """
                UNWIND $pairs AS pair
                MATCH (a:Concept {name: pair[0]})
                MATCH (b:Concept {name: pair[1]})
                MERGE (a)-[:RELATED_TO]->(b)
                MERGE (b)-[:RELATED_TO]->(a)
                """,
                pairs=[list(p) for p in related_to_pairs]
            )

        # 2. PREREQUISITE: chunk[i] keywords -> chunk[i+1] keywords
        prereq_pairs = set()
        for i in range(len(all_keywords_per_chunk) - 1):
            for kw_a in all_keywords_per_chunk[i]:
                for kw_b in all_keywords_per_chunk[i + 1]:
                    if kw_a != kw_b:
                        prereq_pairs.add((kw_a, kw_b))

        if prereq_pairs:
            s.run(
                """
                UNWIND $pairs AS pair
                MATCH (a:Concept {name: pair[0]})
                MATCH (b:Concept {name: pair[1]})
                MERGE (a)-[:PREREQUISITE]->(b)
                """,
                pairs=[list(p) for p in prereq_pairs]
            )

        # 3. PART_OF: substring containment
        part_of_pairs = []
        flat = list(unique_keywords)
        for kw_a in flat:
            for kw_b in flat:
                if kw_a != kw_b and kw_a in kw_b:
                    part_of_pairs.append((kw_a, kw_b))

        if part_of_pairs:
            s.run(
                """
                UNWIND $pairs AS pair
                MATCH (a:Concept {name: pair[0]})
                MATCH (b:Concept {name: pair[1]})
                MERGE (a)-[:PART_OF]->(b)
                """,
                pairs=[list(p) for p in part_of_pairs]
            )


# ── Graph retrieval ──────────────────────────────────────────────────────────

def get_prereq_chain(concept_name: str, max_depth: int = 5) -> list[str]:
    """
    Follow PREREQUISITE edges from concept_name.
    Returns the longest prerequisite chain found.
    """
    name = concept_name.strip().lower()
    driver = get_driver()
    with driver.session() as s:
        result = s.run(
            f"""
            MATCH path = (start:Concept {{name: $name}})-[:PREREQUISITE*1..{max_depth}]->(dep:Concept)
            RETURN [node IN nodes(path) | node.name] AS chain
            ORDER BY length(path) DESC
            LIMIT 1
            """,
            name=name,
        )
        record = result.single()
        if record:
            return record["chain"]
    return [name]


def get_related(concept_name: str, limit: int = 5) -> list[str]:
    """Return concepts directly RELATED_TO the given concept."""
    name = concept_name.strip().lower()
    driver = get_driver()
    with driver.session() as s:
        result = s.run(
            "MATCH (a:Concept {name:$name})-[:RELATED_TO]->(b:Concept) "
            "RETURN b.name AS name LIMIT $limit",
            name=name, limit=limit,
        )
        return [r["name"] for r in result]


def find_existing_concepts(names: list[str]) -> list[str]:
    """Return which of the given names exist as Concept nodes (case-insensitive)."""
    if not names:
        return []
    normalized = [n.strip().lower() for n in names if n.strip()]
    driver = get_driver()
    with driver.session() as s:
        result = s.run(
            "MATCH (c:Concept) WHERE c.name IN $names RETURN c.name AS name",
            names=normalized,
        )
        return [r["name"] for r in result]
