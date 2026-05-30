"""
ChromaDB vector store wrapper.
Handles indexing and semantic search for resumes.
"""
import chromadb
from chromadb.config import Settings
from flask import current_app
from loguru import logger
from app.services.embeddings import EmbeddingService


class VectorStore:
    """ChromaDB wrapper for resume vector storage."""
    
    _client = None
    _collection = None
    COLLECTION_NAME = 'resumes'
    
    @classmethod
    def get_client(cls):
        """Get or create ChromaDB persistent client."""
        if cls._client is None:
            persist_dir = current_app.config['CHROMA_PERSIST_DIR']
            cls._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            logger.info(f'✅ ChromaDB client initialized at: {persist_dir}')
        return cls._client
    
    @classmethod
    def get_collection(cls):
        """Get or create the resumes collection."""
        if cls._collection is None:
            client = cls.get_client()
            cls._collection = client.get_or_create_collection(
                name=cls.COLLECTION_NAME,
                metadata={'description': 'Candidate resume embeddings'}
            )
            logger.info(f'✅ ChromaDB collection ready: {cls.COLLECTION_NAME} ({cls._collection.count()} docs)')
        return cls._collection
    
    @classmethod
    def index_application(cls, application):
        """
        Index a candidate application into ChromaDB.
        
        Args:
            application: Application model instance
        """
        try:
            collection = cls.get_collection()
            
            # Build searchable document text
            doc_text = cls._build_document_text(application)
            
            # Generate embedding
            embedding = EmbeddingService.encode(doc_text)
            if not embedding:
                logger.error(f'Failed to embed application {application.id}')
                return False
            
            # Metadata - all values must be str, int, float, or bool (no None)
            metadata = {
                'application_id': int(application.id),
                'user_id': int(application.user_id),
                'job_id': int(application.job_id),
                'owner_id': int(application.job.posted_by_id),
                'candidate_name': str(application.full_name or 'Unknown'),
                'candidate_email': str(application.email or ''),
                'job_title': str(application.job.title or ''),
                'skills': str(application.skills or ''),
                'experience_years': float(application.experience_years or 0),
                'match_score': float(application.match_score or 0),
                'status': str(application.status or 'Pending'),
                'applied_at': application.applied_at.isoformat() if application.applied_at else '',
            }
            
            # Use application ID as unique doc ID
            doc_id = f'app_{application.id}'
            
            # Upsert (insert or update)
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[doc_text],
                metadatas=[metadata]
            )
            
            # Mark as indexed
            application.is_indexed = True
            
            logger.info(f'✅ Indexed application {application.id} ({application.full_name})')
            return True
        
        except Exception as e:
            logger.error(f'Failed to index application {application.id}: {e}')
            return False
    
    @classmethod
    def search(cls, query, owner_id, top_k=5, filters=None):
        """
        Semantic search over indexed applications.
        
        Args:
            query: search query string
            owner_id: restrict results to this owner's candidates
            top_k: number of results
            filters: additional metadata filters (dict)
        
        Returns:
            List of dicts with metadata and similarity scores
        """
        try:
            collection = cls.get_collection()
            
            # Generate query embedding
            query_embedding = EmbeddingService.encode(query)
            if not query_embedding:
                return []
            
            # Build where clause (owner_id is mandatory for data isolation)
            where_clause = {'owner_id': int(owner_id)}
            if filters:
                # Combine with AND logic
                conditions = [where_clause] + [{k: v} for k, v in filters.items()]
                where_clause = {'$and': conditions} if len(conditions) > 1 else where_clause
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
            )
            
            # Format results
            formatted = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    formatted.append({
                        'id': doc_id,
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if results.get('distances') else None,
                        'similarity': 1 - results['distances'][0][i] if results.get('distances') else None,
                    })
            
            logger.info(f'🔍 Search "{query[:50]}" → {len(formatted)} results')
            return formatted
        
        except Exception as e:
            logger.error(f'Search failed: {e}')
            return []
    
    @classmethod
    def delete_application(cls, application_id):
        """Remove an application from the index."""
        try:
            collection = cls.get_collection()
            collection.delete(ids=[f'app_{application_id}'])
            logger.info(f'Deleted application {application_id} from index')
            return True
        except Exception as e:
            logger.error(f'Failed to delete from index: {e}')
            return False
    
    @classmethod
    def get_owner_stats(cls, owner_id):
        """Get count of indexed candidates for an owner."""
        try:
            collection = cls.get_collection()
            results = collection.get(where={'owner_id': int(owner_id)})
            return len(results['ids']) if results.get('ids') else 0
        except Exception as e:
            logger.error(f'Stats failed: {e}')
            return 0
    
    @classmethod
    def reindex_all(cls, owner_id=None):
        """Reindex all applications (useful after bug fixes)."""
        from app.models.application import Application
        from app.models.job import Job
        from app.extensions import db
        
        query = Application.query.join(Job)
        if owner_id:
            query = query.filter(Job.posted_by_id == owner_id)
        
        applications = query.all()
        success = 0
        for app in applications:
            if cls.index_application(app):
                success += 1
        
        db.session.commit()
        logger.info(f'Reindexed {success}/{len(applications)} applications')
        return success
    
    @staticmethod
    def _build_document_text(application):
        """Build searchable text representation of an application."""
        parts = [
            f"Candidate: {application.full_name or 'Unknown'}",
            f"Applied for: {application.job.title}",
            f"Experience: {application.experience_years} years",
            f"Skills: {application.skills or 'Not specified'}",
        ]
        
        if application.education:
            parts.append(f"Education: {application.education}")
        
        if application.ai_summary:
            parts.append(f"Summary: {application.ai_summary}")
        
        if application.resume_text:
            # Add first part of raw resume text
            parts.append(f"Resume content: {application.resume_text[:2000]}")
        
        return '\n'.join(parts)
