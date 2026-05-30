"""
Sentence Transformer embedding service.
Singleton pattern - loads model once, reuses across requests.
"""
from sentence_transformers import SentenceTransformer
from loguru import logger
from flask import current_app


class EmbeddingService:
    """Generate semantic embeddings using sentence-transformers."""
    
    _model = None
    _model_name = None
    
    @classmethod
    def get_model(cls):
        """Lazy load model on first use."""
        if cls._model is None:
            model_name = current_app.config.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            logger.info(f'Loading embedding model: {model_name} (first time may take 30s)...')
            cls._model = SentenceTransformer(model_name)
            cls._model_name = model_name
            logger.info(f'✅ Embedding model loaded: {model_name} (dim={cls._model.get_sentence_embedding_dimension()})')
        return cls._model
    
    @classmethod
    def encode(cls, texts, batch_size=32):
        """
        Generate embeddings for one or more texts.
        
        Args:
            texts: str or List[str]
            batch_size: batch size for encoding
        
        Returns:
            List[List[float]] - embeddings
        """
        model = cls.get_model()
        
        # Handle single string
        single = isinstance(texts, str)
        if single:
            texts = [texts]
        
        # Clean texts
        texts = [str(t).strip()[:5000] for t in texts if t]  # Limit length
        if not texts:
            return []
        
        try:
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            result = embeddings.tolist()
            return result[0] if single else result
        except Exception as e:
            logger.error(f'Embedding generation failed: {e}')
            return [] if single else [[] for _ in texts]
    
    @classmethod
    def get_dimension(cls):
        """Get embedding dimension."""
        return cls.get_model().get_sentence_embedding_dimension()
