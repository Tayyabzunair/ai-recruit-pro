"""
RAG (Retrieval-Augmented Generation) service.
Combines vector search with LLM generation for intelligent Q&A.
"""
from loguru import logger
from app.services.vector_store import VectorStore
from app.services.ai_service import AIService
from app.models.application import Application
from app.models.job import Job
from app.extensions import db
from sqlalchemy import func, desc


class RAGService:
    """RAG pipeline for owner's chatbot queries."""
    
    @classmethod
    def answer_query(cls, query, owner_id, chat_history=None):
        """
        Main RAG entry point.
        
        Args:
            query: User's question
            owner_id: Current user ID (data isolation)
            chat_history: Previous messages [{role, content}, ...]
        
        Returns:
            dict: {answer, sources, query_type}
        """
        try:
            # 1. Classify query intent
            query_type = cls._classify_query(query)
            logger.info(f'Query type: {query_type} | Query: {query[:80]}')
            
            # 2. Route to appropriate handler
            if query_type == 'stats':
                return cls._handle_stats_query(query, owner_id)
            elif query_type == 'list_jobs':
                return cls._handle_jobs_query(query, owner_id)
            else:
                # Default: semantic search over candidates
                return cls._handle_candidate_query(query, owner_id, chat_history)
        
        except Exception as e:
            logger.error(f'RAG query failed: {e}')
            return {
                'answer': '⚠️ Sorry, I encountered an error processing your query. Please try again.',
                'sources': [],
                'query_type': 'error',
            }
    
    @classmethod
    def _classify_query(cls, query):
        """Simple rule-based query classifier."""
        q = query.lower()
        
        # Stats keywords
        stats_kw = ['how many', 'count', 'total', 'statistics', 'stats', 'kitne', 'kitni', 
                    'number of', 'overview', 'summary of all']
        if any(k in q for k in stats_kw):
            return 'stats'
        
        # Job-listing keywords
        job_kw = ['list jobs', 'all jobs', 'my jobs', 'job postings', 'kaunsi jobs', 
                  'which jobs', 'show jobs', 'open positions']
        if any(k in q for k in job_kw) and 'candidate' not in q:
            return 'list_jobs'
        
        return 'candidates'
    
    @classmethod
    def _handle_candidate_query(cls, query, owner_id, chat_history=None):
        """RAG pipeline for candidate-related questions."""
        # 1. Semantic search
        results = VectorStore.search(query, owner_id=owner_id, top_k=5)
        
        if not results:
            return {
                'answer': "I couldn't find any candidates matching your query. Either no one has applied yet, or your query doesn't match any indexed candidates.\n\n💡 **Tip:** Try posting jobs and waiting for applications, then ask me again!",
                'sources': [],
                'query_type': 'candidates',
            }
        
        # 2. Build context from search results
        context = cls._build_context(results)
        
        # 3. Build chat history context
        history_text = ''
        if chat_history:
            recent = chat_history[-4:]  # Last 2 turns
            for msg in recent:
                role = '👤 User' if msg['role'] == 'user' else '🤖 You'
                history_text += f'{role}: {msg["content"]}\n'
        
        # 4. Generate answer with Gemini
        prompt = cls._build_rag_prompt(query, context, history_text)
        answer = AIService.generate(prompt)
        
        # 5. Format sources for UI
        sources = [
            {
                'id': r['metadata'].get('application_id'),
                'name': r['metadata'].get('candidate_name'),
                'job': r['metadata'].get('job_title'),
                'score': round(r['metadata'].get('match_score', 0), 1),
                'similarity': round(r['similarity'] * 100, 1) if r.get('similarity') else 0,
            }
            for r in results
        ]
        
        return {
            'answer': answer,
            'sources': sources,
            'query_type': 'candidates',
        }
    
    @classmethod
    def _handle_stats_query(cls, query, owner_id):
        """Handle statistics queries with direct DB access."""
        # Fetch real stats
        total_jobs = Job.query.filter_by(posted_by_id=owner_id).count()
        active_jobs = Job.query.filter_by(posted_by_id=owner_id, is_active=True).count()
        
        apps_q = Application.query.join(Job).filter(Job.posted_by_id == owner_id)
        total_apps = apps_q.count()
        
        status_counts = db.session.query(
            Application.status, func.count(Application.id)
        ).join(Job).filter(Job.posted_by_id == owner_id).group_by(Application.status).all()
        
        status_summary = {s: c for s, c in status_counts}
        
        avg_score = db.session.query(func.avg(Application.match_score)).join(Job).filter(
            Job.posted_by_id == owner_id
        ).scalar() or 0
        
        # Build context
        context = f"""
HIRING STATISTICS:
- Total Jobs Posted: {total_jobs}
- Active Jobs: {active_jobs}
- Total Applications: {total_apps}
- Average Match Score: {avg_score:.1f}%

Application Status Breakdown:
{chr(10).join(f'  - {s}: {c}' for s, c in status_summary.items()) or '  (No applications yet)'}
        """
        
        prompt = f"""You are a professional recruitment analytics assistant. The owner asked:

"{query}"

Here are the REAL statistics from their account:
{context}

Instructions:
1. Answer in a friendly, professional tone
2. Use **bold** for key numbers
3. Use bullet points if listing multiple items
4. Give actionable insights if relevant
5. Match the language style of the question (English/Roman Urdu)
6. Keep it concise (3-6 sentences)

Answer:"""
        
        answer = AIService.generate(prompt)
        
        return {
            'answer': answer,
            'sources': [],
            'query_type': 'stats',
        }
    
    @classmethod
    def _handle_jobs_query(cls, query, owner_id):
        """Handle job-listing queries."""
        jobs = Job.query.filter_by(posted_by_id=owner_id).order_by(desc(Job.created_at)).limit(10).all()
        
        if not jobs:
            return {
                'answer': "You haven't posted any jobs yet. Click '**Post New Job**' to get started!",
                'sources': [],
                'query_type': 'list_jobs',
            }
        
        # Build context
        jobs_info = []
        for j in jobs:
            jobs_info.append(
                f"- **{j.title}** ({j.location}, {j.job_type}) — "
                f"{j.applications_count} applications, "
                f"{'Active' if j.is_active else 'Inactive'}"
            )
        
        context = '\n'.join(jobs_info)
        
        prompt = f"""You are a recruitment assistant. The owner asked:

"{query}"

Here are their job postings:
{context}

Provide a concise, well-formatted answer with markdown. Highlight key metrics."""
        
        answer = AIService.generate(prompt)
        
        return {
            'answer': answer,
            'sources': [],
            'query_type': 'list_jobs',
        }
    
    @classmethod
    def _build_context(cls, results):
        """Build context string from retrieved candidates."""
        parts = []
        for i, r in enumerate(results, 1):
            meta = r['metadata']
            parts.append(f"""
[CANDIDATE {i}]
- Name: {meta.get('candidate_name')}
- Email: {meta.get('candidate_email')}
- Applied for: {meta.get('job_title')}
- Match Score: {meta.get('match_score', 0):.1f}%
- Experience: {meta.get('experience_years', 0)} years
- Skills: {meta.get('skills', 'N/A')}
- Status: {meta.get('status')}
- Similarity to query: {r.get('similarity', 0)*100:.1f}%

Resume excerpt:
{r['document'][:800]}
            """.strip())
        
        return '\n\n'.join(parts)
    
    @classmethod
    def _build_rag_prompt(cls, query, context, history=''):
        """Build the final RAG prompt for Gemini."""
        return f"""You are an expert AI Recruitment Assistant helping a hiring manager find the right candidates.

{f'CONVERSATION HISTORY:{chr(10)}{history}' if history else ''}

RETRIEVED CANDIDATES (from semantic search):
{context}

USER QUERY: "{query}"

INSTRUCTIONS:
1. **Answer based ONLY on the retrieved candidates above.** Do not make up information.
2. If the query asks for a list/ranking, present candidates with their names, match scores, and key skills.
3. If the query asks for analysis, give insights based on the data.
4. Use **markdown formatting**:
   - **Bold** for candidate names and key data
   - Bullet points for lists
   - Tables if comparing multiple candidates
5. Be professional but conversational.
6. If a candidate has a high match score (>80%), highlight them as top picks.
7. If retrieved candidates don't match the query well, acknowledge that politely.
8. Match the language of the user (English or Roman Urdu).
9. Keep response focused — don't list ALL candidates if the user asked for "top 3".
10. End with a brief suggestion or next step if relevant.

ANSWER:"""
