"""
Email notification service with HTML templates.
Sends emails in background thread for non-blocking requests.
"""
from threading import Thread
from flask import current_app, render_template, url_for
from flask_mail import Message
from loguru import logger

from app.extensions import mail


def send_async_email(app, msg):
    """Send email in background thread."""
    with app.app_context():
        try:
            mail.send(msg)
            logger.info(f'✅ Email sent to {msg.recipients}')
        except Exception as e:
            logger.error(f'❌ Email failed: {e}')


def send_email(subject, recipients, html_body, text_body=None):
    """
    Send email asynchronously.
    
    Args:
        subject: Email subject
        recipients: List of email addresses or single email
        html_body: HTML content
        text_body: Optional plain text fallback
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    
    # Check if mail is configured
    if not current_app.config.get('MAIL_USERNAME'):
        logger.warning('⚠️ MAIL not configured, skipping email')
        return False
    
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            html=html_body,
            body=text_body or 'Please view this email in HTML format.',
            sender=current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
        )
        
        # Send in background thread
        app = current_app._get_current_object()
        Thread(target=send_async_email, args=(app, msg), daemon=True).start()
        return True
    
    except Exception as e:
        logger.error(f'Email setup failed: {e}')
        return False


def _safe_url(endpoint, **kwargs):
    """
    Build an external URL, falling back to '#' if URL building fails
    (e.g. when called outside a request context).
    """
    try:
        return url_for(endpoint, _external=True, **kwargs)
    except Exception as e:
        logger.warning(f'URL building failed for {endpoint}: {e}')
        return '#'


class EmailService:
    """High-level email notification methods."""
    
    @staticmethod
    def send_welcome(user):
        """Welcome email on signup."""
        try:
            # Send users to login page after signup
            cta_url = _safe_url('auth.login')
            
            html = render_template(
                'emails/welcome.html',
                user=user,
                cta_url=cta_url,
            )
            send_email(
                subject=f'🎉 Welcome to AI Recruit Pro, {user.name}!',
                recipients=user.email,
                html_body=html
            )
        except Exception as e:
            logger.error(f'send_welcome failed: {e}')
    
    @staticmethod
    def send_application_received(application):
        """Notify owner about new application."""
        try:
            owner = application.job.posted_by
            
            # Direct link to the candidate detail page
            review_url = _safe_url('owner.candidate_detail', app_id=application.id)
            
            html = render_template(
                'emails/application_received.html',
                application=application,
                owner=owner,
                job=application.job,
                review_url=review_url,
            )
            send_email(
                subject=f'🎯 New Application: {application.full_name} for {application.job.title}',
                recipients=owner.email,
                html_body=html
            )
        except Exception as e:
            logger.error(f'send_application_received failed: {e}')
    
    @staticmethod
    def send_application_confirmation(application):
        """Notify candidate their application was received."""
        try:
            # Direct link to candidate's "My Applications" page
            dashboard_url = _safe_url('candidate.my_applications')
            
            html = render_template(
                'emails/application_confirmation.html',
                application=application,
                job=application.job,
                dashboard_url=dashboard_url,
            )
            send_email(
                subject=f'✅ Application Received - {application.job.title}',
                recipients=application.email,
                html_body=html
            )
        except Exception as e:
            logger.error(f'send_application_confirmation failed: {e}')
    
    @staticmethod
    def send_status_update(application, old_status, new_status):
        """Notify candidate about status change."""
        try:
            # Don't notify for trivial status changes
            if old_status == new_status:
                return
            
            # Get a friendly message based on status
            messages = {
                'Reviewed': 'Your application has been reviewed by the hiring team.',
                'Shortlisted': '🎉 Great news! You\'ve been shortlisted for this position.',
                'Interview': '📅 You\'ve been invited for an interview! Check back for details.',
                'Hired': '🎊 Congratulations! You\'ve been selected for this role!',
                'Rejected': 'Thank you for applying. We\'ve decided to move forward with other candidates.',
            }
            
            message = messages.get(new_status, f'Your application status has been updated to: {new_status}')
            
            # Link to candidate's applications page so they can view the update
            view_url = _safe_url('candidate.my_applications')
            
            html = render_template(
                'emails/status_update.html',
                application=application,
                job=application.job,
                new_status=new_status,
                message=message,
                view_url=view_url,
            )
            send_email(
                subject=f'📬 Application Update: {application.job.title}',
                recipients=application.email,
                html_body=html
            )
        except Exception as e:
            logger.error(f'send_status_update failed: {e}')
