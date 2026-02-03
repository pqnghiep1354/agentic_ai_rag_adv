"""
Neo4j graph database repository.
Handles knowledge graph construction and multi-hop traversal for GraphRAG.
"""

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

from app.core.config import settings
from app.utils.chunking import (Chunk, extract_entities,
                                extract_legal_references)

logger = logging.getLogger(__name__)


class GraphRepository:
    """
    Repository for Neo4j graph database operations.

    Graph Structure:
    - Document nodes (root)
    - Section nodes (Chapters, Sections)
    - Article nodes (Articles, Clauses)
    - Chunk nodes (text chunks)
    - Entity nodes (Laws, Decrees, etc.)

    Relationships:
    - CONTAINS: hierarchical structure (Document->Section->Article->Chunk)
    - REFERENCES: legal references between chunks
    - CITES: citations to other laws/documents
    - RELATES_TO: entity relationships
    """

    def __init__(
        self,
        uri: str = settings.NEO4J_URI,
        user: str = settings.NEO4J_USER,
        password: str = settings.NEO4J_PASSWORD,
    ):
        """
        Initialize Neo4j driver.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        logger.info(f"Connecting to Neo4j at {uri}")

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # Verify connection
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def create_document_node(
        self,
        document_id: int,
        filename: str,
        metadata: Dict[str, Any],
    ) -> None:
        """
        Create a Document node in the graph.

        Args:
            document_id: Database document ID
            filename: Document filename
            metadata: Document metadata
        """
        with self.driver.session() as session:
            session.execute_write(
                self._create_document_node_tx,
                document_id,
                filename,
                metadata,
            )

    @staticmethod
    def _create_document_node_tx(
        tx, document_id: int, filename: str, metadata: Dict[str, Any]
    ):
        """Transaction function to create document node."""
        query = """
        MERGE (d:Document {document_id: $document_id})
        SET d.filename = $filename,
            d.title = $title,
            d.page_count = $page_count,
            d.created_at = datetime()
        RETURN d
        """
        result = tx.run(
            query,
            document_id=document_id,
            filename=filename,
            title=metadata.get("title", filename),
            page_count=metadata.get("page_count", 0),
        )
        logger.debug(f"Created document node: {document_id}")
        return result.single()

    def create_chunk_nodes(
        self,
        chunks: List[Chunk],
    ) -> None:
        """
        Create Chunk nodes and build hierarchical structure.

        Creates:
        - Chunk nodes with text and metadata
        - CONTAINS relationships (Document->Chunk)
        - Parent-child relationships between chunks

        Args:
            chunks: List of Chunk objects
        """
        if not chunks:
            return

        with self.driver.session() as session:
            for chunk in chunks:
                session.execute_write(
                    self._create_chunk_node_tx,
                    chunk,
                )

    @staticmethod
    def _create_chunk_node_tx(tx, chunk: Chunk):
        """Transaction function to create chunk node and relationships."""
        # Create chunk node
        query = """
        MERGE (c:Chunk {chunk_id: $chunk_id})
        SET c.text = $text,
            c.page_number = $page_number,
            c.hierarchy_level = $hierarchy_level,
            c.hierarchy_path = $hierarchy_path,
            c.created_at = datetime()
        WITH c
        MATCH (d:Document {document_id: $document_id})
        MERGE (d)-[:CONTAINS]->(c)
        RETURN c
        """

        result = tx.run(
            query,
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            page_number=chunk.page_number,
            hierarchy_level=chunk.hierarchy_level,
            hierarchy_path=chunk.hierarchy_path,
            document_id=chunk.document_id,
        )

        # Create parent relationship if exists
        if chunk.parent_chunk_id:
            parent_query = """
            MATCH (parent:Chunk {chunk_id: $parent_chunk_id})
            MATCH (child:Chunk {chunk_id: $chunk_id})
            MERGE (parent)-[:HAS_CHILD]->(child)
            """
            tx.run(
                parent_query,
                parent_chunk_id=chunk.parent_chunk_id,
                chunk_id=chunk.chunk_id,
            )

        return result.single()

    def create_references(
        self,
        chunks: List[Chunk],
    ) -> None:
        """
        Extract and create reference relationships between chunks.

        Analyzes chunk text for legal references and creates
        REFERENCES relationships between chunks.

        Args:
            chunks: List of Chunk objects
        """
        logger.info(f"Creating reference relationships for {len(chunks)} chunks")

        with self.driver.session() as session:
            for chunk in chunks:
                # Extract legal references
                references = extract_legal_references(chunk.text)

                if references:
                    session.execute_write(
                        self._create_reference_relationships_tx,
                        chunk.chunk_id,
                        references,
                    )

    @staticmethod
    def _create_reference_relationships_tx(
        tx,
        source_chunk_id: str,
        references: List[str],
    ):
        """Transaction function to create REFERENCES relationships."""
        # For each reference, find chunks that mention it
        for ref in references:
            query = """
            MATCH (source:Chunk {chunk_id: $source_chunk_id})
            MATCH (target:Chunk)
            WHERE target.chunk_id <> $source_chunk_id
              AND target.text CONTAINS $reference
            MERGE (source)-[r:REFERENCES {reference_text: $reference}]->(target)
            RETURN count(r) as count
            """
            result = tx.run(
                query,
                source_chunk_id=source_chunk_id,
                reference=ref,
            )
            count = result.single()["count"]
            if count > 0:
                logger.debug(
                    f"Created {count} REFERENCES from {source_chunk_id} for '{ref}'"
                )

    def create_entity_nodes(
        self,
        chunks: List[Chunk],
    ) -> None:
        """
        Extract entities and create entity nodes with relationships.

        Extracts:
        - Laws
        - Decrees
        - Circulars
        - Decisions
        - Articles
        - Clauses

        Args:
            chunks: List of Chunk objects
        """
        logger.info(f"Creating entity nodes from {len(chunks)} chunks")

        with self.driver.session() as session:
            for chunk in chunks:
                entities = extract_entities(chunk.text)

                # Create entity nodes and relationships
                for entity_type, entity_list in entities.items():
                    if entity_list:
                        session.execute_write(
                            self._create_entity_nodes_tx,
                            chunk.chunk_id,
                            entity_type,
                            entity_list,
                        )

    @staticmethod
    def _create_entity_nodes_tx(
        tx,
        chunk_id: str,
        entity_type: str,
        entities: List[str],
    ):
        """Transaction function to create entity nodes."""
        # Map entity types to node labels
        label_map = {
            "laws": "Law",
            "decrees": "Decree",
            "circulars": "Circular",
            "decisions": "Decision",
            "articles": "Article",
            "clauses": "Clause",
        }

        label = label_map.get(entity_type, "Entity")

        for entity in entities:
            query = f"""
            MERGE (e:{label} {{name: $entity_name}})
            WITH e
            MATCH (c:Chunk {{chunk_id: $chunk_id}})
            MERGE (c)-[:MENTIONS]->(e)
            RETURN e
            """
            tx.run(
                query,
                entity_name=entity,
                chunk_id=chunk_id,
            )

    def find_related_chunks(
        self,
        chunk_ids: List[str],
        max_depth: int = 2,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Find related chunks using graph traversal (multi-hop reasoning).

        Traverses:
        1. Direct references (REFERENCES relationship)
        2. Shared entities (via MENTIONS)
        3. Hierarchical neighbors (parent/child, siblings)

        Args:
            chunk_ids: Starting chunk IDs (from vector search)
            max_depth: Maximum traversal depth (1-3 recommended)
            max_results: Maximum number of results

        Returns:
            List of related chunks with relevance scores
        """
        if not chunk_ids:
            return []

        logger.debug(
            f"Finding related chunks for {len(chunk_ids)} seeds, depth={max_depth}"
        )

        with self.driver.session() as session:
            result = session.execute_read(
                self._find_related_chunks_tx,
                chunk_ids,
                max_depth,
                max_results,
            )

            return result

    @staticmethod
    def _find_related_chunks_tx(
        tx,
        chunk_ids: List[str],
        max_depth: int,
        max_results: int,
    ):
        """Transaction function to find related chunks."""
        query = """
        // Start from seed chunks
        MATCH (start:Chunk)
        WHERE start.chunk_id IN $chunk_ids

        // Multi-hop traversal
        CALL {
            WITH start
            MATCH path = (start)-[r:REFERENCES|MENTIONS|HAS_CHILD|CONTAINS*1..$max_depth]-(related:Chunk)
            WHERE related.chunk_id <> start.chunk_id
            RETURN DISTINCT related, length(path) as distance
        }

        // Calculate relevance score
        WITH related,
             distance,
             1.0 / (1.0 + distance) as path_score

        // Return top results
        RETURN DISTINCT
            related.chunk_id as chunk_id,
            related.text as text,
            related.page_number as page_number,
            related.hierarchy_level as hierarchy_level,
            related.hierarchy_path as hierarchy_path,
            path_score as relevance_score
        ORDER BY relevance_score DESC
        LIMIT $max_results
        """

        result = tx.run(
            query,
            chunk_ids=chunk_ids,
            max_depth=max_depth,
            max_results=max_results,
        )

        related_chunks = []
        for record in result:
            related_chunks.append(
                {
                    "chunk_id": record["chunk_id"],
                    "text": record["text"],
                    "page_number": record["page_number"],
                    "hierarchy_level": record["hierarchy_level"],
                    "hierarchy_path": record["hierarchy_path"],
                    "relevance_score": record["relevance_score"],
                }
            )

        logger.debug(f"Found {len(related_chunks)} related chunks")
        return related_chunks

    def delete_document_graph(self, document_id: int) -> None:
        """
        Delete all nodes and relationships for a document.

        Args:
            document_id: Document ID to delete
        """
        logger.info(f"Deleting graph for document_id={document_id}")

        with self.driver.session() as session:
            session.execute_write(
                self._delete_document_graph_tx,
                document_id,
            )

    @staticmethod
    def _delete_document_graph_tx(tx, document_id: int):
        """Transaction function to delete document graph."""
        query = """
        MATCH (d:Document {document_id: $document_id})
        OPTIONAL MATCH (d)-[:CONTAINS*]->(n)
        DETACH DELETE d, n
        """
        result = tx.run(query, document_id=document_id)
        logger.info(f"Deleted graph for document_id={document_id}")
        return result

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.

        Returns:
            Dictionary with node and relationship counts
        """
        with self.driver.session() as session:
            result = session.execute_read(self._get_graph_stats_tx)
            return result

    @staticmethod
    def _get_graph_stats_tx(tx):
        """Transaction function to get graph stats."""
        query = """
        MATCH (n)
        WITH labels(n)[0] as label, count(n) as count
        RETURN label, count
        ORDER BY count DESC
        """
        result = tx.run(query)

        node_counts = {}
        for record in result:
            node_counts[record["label"]] = record["count"]

        # Get relationship counts
        rel_query = """
        MATCH ()-[r]->()
        WITH type(r) as rel_type, count(r) as count
        RETURN rel_type, count
        ORDER BY count DESC
        """
        rel_result = tx.run(rel_query)

        relationship_counts = {}
        for record in rel_result:
            relationship_counts[record["rel_type"]] = record["count"]

        return {
            "nodes": node_counts,
            "relationships": relationship_counts,
        }


# Global graph repository instance (singleton)
_graph_repo: Optional[GraphRepository] = None


def get_graph_repository() -> GraphRepository:
    """
    Get or create global graph repository instance.

    Returns:
        GraphRepository instance
    """
    global _graph_repo

    if _graph_repo is None:
        logger.info("Initializing global graph repository")
        _graph_repo = GraphRepository()

    return _graph_repo
