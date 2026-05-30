"""
Chatbot blueprint - RAG-powered AI assistant for owners.
"""
from flask import render_template, request, jsonify, session
from flask_login import current_user
from loguru import logger

from app.blueprints.chatbot import chatbot_bp
from app.extensions import csrf
from app.utils.decorators import owner_required
from app.services.rag_service import RAGService
from app.services.vector_store import VectorStore


@chatbot_bp.route('/')
@owner_required
def chat_page():
    """Render chatbot UI."""
    indexed_count = VectorStore.get_owner_stats(current_user.id)
    session.pop('chat_history', None)
    return render_template('chatbot/chat.html', indexed_count=indexed_count)


@chatbot_bp.route('/query', methods=['POST'])
@csrf.exempt
@owner_required
def query():
    """Process a chatbot query and return AI response."""
    try:
        data = request.get_json()
        user_message = (data.get('message') or '').strip()
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        if len(user_message) > 500:
            return jsonify({'error': 'Message too long (max 500 chars)'}), 400
        
        history = session.get('chat_history', [])
        
        result = RAGService.answer_query(
            query=user_message,
            owner_id=current_user.id,
            chat_history=history
        )
        
        history.append({'role': 'user', 'content': user_message})
        history.append({'role': 'assistant', 'content': result['answer']})
        session['chat_history'] = history[-10:]
        
        logger.info(f'Chatbot reply generated for owner {current_user.id}')
        
        return jsonify({
            'reply': result['answer'],
            'sources': result.get('sources', []),
            'query_type': result.get('query_type', 'unknown'),
        })
    
    except Exception as e:
        logger.error(f'Chatbot query failed: {e}', exc_info=True)
        return jsonify({
            'reply': f'⚠️ Error: {str(e)}',
            'sources': [],
        }), 500


@chatbot_bp.route('/reset', methods=['POST'])
@csrf.exempt
@owner_required
def reset():
    """Clear chat history."""
    session.pop('chat_history', None)
    return jsonify({'status': 'ok'})


@chatbot_bp.route('/reindex', methods=['POST'])
@csrf.exempt
@owner_required
def reindex():
    """Reindex all applications (admin tool)."""
    count = VectorStore.reindex_all(owner_id=current_user.id)
    return jsonify({'status': 'ok', 'indexed': count})
