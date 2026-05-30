"""
Candidate blueprint routes - browse jobs, apply, track applications.
"""
import os
from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user
from sqlalchemy import desc, or_
from loguru import logger

from app.blueprints.candidate import candidate_bp
from app.extensions import db, csrf
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.utils.decorators import candidate_required
from app.utils.validators import allowed_file, safe_filename
from app.services.resume_parser import ResumeParser
from app.services.matcher import SkillMatcher


@candidate_bp.route('/dashboard')
@candidate_required
def dashboard():
    """Candidate main dashboard."""
    recent_jobs = Job.query.filter_by(is_active=True).order_by(desc(Job.created_at)).limit(6).all()

    my_apps = Application.query.filter_by(user_id=current_user.id).order_by(
        desc(Application.applied_at)
    ).limit(5).all()

    total_applied = Application.query.filter_by(user_id=current_user.id).count()
    interviews = Application.query.filter_by(
        user_id=current_user.id, status=ApplicationStatus.INTERVIEW
    ).count()
    shortlisted = Application.query.filter_by(
        user_id=current_user.id, status=ApplicationStatus.SHORTLISTED
    ).count()
    hired = Application.query.filter_by(
        user_id=current_user.id, status=ApplicationStatus.HIRED
    ).count()

    applied_job_ids = {a.job_id for a in Application.query.filter_by(user_id=current_user.id).all()}

    return render_template('candidate/dashboard.html',
                           recent_jobs=recent_jobs,
                           my_applications=my_apps,
                           applied_job_ids=applied_job_ids,
                           total_applied=total_applied,
                           interviews=interviews,
                           shortlisted=shortlisted,
                           hired=hired)


@candidate_bp.route('/jobs')
@candidate_required
def jobs():
    """Browse all active jobs with filters."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    location = request.args.get('location', '').strip()
    job_type = request.args.get('type', '')

    query = Job.query.filter_by(is_active=True)

    if search:
        query = query.filter(or_(
            Job.title.ilike(f'%{search}%'),
            Job.skills.ilike(f'%{search}%'),
            Job.description.ilike(f'%{search}%'),
        ))
    if location:
        query = query.filter(Job.location.ilike(f'%{location}%'))
    if job_type:
        query = query.filter_by(job_type=job_type)

    jobs_page = query.order_by(desc(Job.created_at)).paginate(page=page, per_page=9, error_out=False)

    applied_job_ids = {a.job_id for a in Application.query.filter_by(user_id=current_user.id).all()}

    return render_template('candidate/jobs.html',
                           jobs=jobs_page,
                           applied_job_ids=applied_job_ids,
                           search=search,
                           location=location,
                           job_type=job_type)


@candidate_bp.route('/jobs/<int:job_id>')
@candidate_required
def job_detail(job_id):
    """Job detail view."""
    job = Job.query.get_or_404(job_id)
    already_applied = Application.query.filter_by(
        user_id=current_user.id, job_id=job_id
    ).first() is not None

    return render_template('candidate/job_detail.html', job=job, already_applied=already_applied)


@candidate_bp.route('/apply/<int:job_id>', methods=['GET', 'POST'])
@candidate_required
def apply(job_id):
    """Upload resume to apply."""
    job = Job.query.get_or_404(job_id)

    if not job.is_active:
        flash('This job is no longer accepting applications.', 'warning')
        return redirect(url_for('candidate.jobs'))

    existing = Application.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if existing:
        flash('You have already applied to this job.', 'info')
        return redirect(url_for('candidate.my_applications'))

    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)

        file = request.files['resume']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Only PDF files are allowed.', 'danger')
            return redirect(request.url)

        filename = safe_filename(file.filename, current_user.id)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(filepath)
            logger.info(f'Resume saved: {filename}')

            data, raw_text = ResumeParser.parse(filepath)

            return render_template('candidate/confirm_application.html',
                                   job=job,
                                   data=data,
                                   raw_text=raw_text,
                                   filename=filename)
        except Exception as e:
            logger.error(f'Resume processing failed: {e}')
            flash('Failed to process resume. Please try again.', 'danger')
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(request.url)

    return render_template('candidate/apply.html', job=job)


@candidate_bp.route('/apply/finalize', methods=['POST'])
@candidate_required
def finalize_application():
    """Save the application after confirmation and auto-index to vector store."""
    job_id = request.form.get('job_id', type=int)
    job = Job.query.get_or_404(job_id)

    existing = Application.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if existing:
        flash('Already applied to this job.', 'warning')
        return redirect(url_for('candidate.my_applications'))

    skills = request.form.get('skills', '')
    experience_years = float(request.form.get('experience_years', 0) or 0)

    match_score = SkillMatcher.calculate_match(
        candidate_skills=skills,
        job_skills=job.skills,
        experience_years=experience_years,
    )

    application = Application(
        user_id=current_user.id,
        job_id=job_id,
        full_name=request.form.get('full_name'),
        email=request.form.get('email'),
        phone=request.form.get('phone'),
        skills=skills,
        experience_years=experience_years,
        education=request.form.get('education'),
        ai_summary=request.form.get('summary'),
        resume_filename=request.form.get('filename'),
        resume_text=request.form.get('raw_text', '')[:10000],
        match_score=match_score,
        status=ApplicationStatus.PENDING,
    )

    db.session.add(application)
    db.session.commit()

    # 🌟 Auto-index to ChromaDB for RAG (non-critical)
    try:
        from app.services.vector_store import VectorStore
        VectorStore.index_application(application)
        db.session.commit()
        logger.info(f'✅ Application {application.id} indexed to vector store')
    except Exception as e:
        logger.error(f'⚠️ Failed to index application {application.id}: {e}')

    # 🌟 Send notification emails (non-blocking, non-critical)
    try:
        from app.services.email_service import EmailService
        EmailService.send_application_confirmation(application)
        EmailService.send_application_received(application)
    except Exception as e:
        logger.error(f'Email notification failed: {e}')

    logger.info(f'Application submitted: User {current_user.id} → Job {job_id}, score={match_score}')
    flash(f'Application submitted successfully! Match score: {match_score}%', 'success')
    return redirect(url_for('candidate.my_applications'))


# ============================================================
# MY APPLICATIONS — track all submitted applications
# ============================================================
@candidate_bp.route('/applications')
@candidate_required
def my_applications():
    """Show all applications submitted by the current candidate (paginated)."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()

    query = Application.query.filter_by(user_id=current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    # Paginate so template can use .items / .pages / .has_prev / .has_next
    applications = query.order_by(desc(Application.applied_at)).paginate(
        page=page, per_page=10, error_out=False
    )

    # Stats for the header cards (always over ALL apps, not filtered ones)
    all_apps = Application.query.filter_by(user_id=current_user.id).all()
    stats = {
        'total': len(all_apps),
        'pending': sum(1 for a in all_apps if a.status == ApplicationStatus.PENDING),
        'shortlisted': sum(1 for a in all_apps if a.status == ApplicationStatus.SHORTLISTED),
        'interview': sum(1 for a in all_apps if a.status == ApplicationStatus.INTERVIEW),
        'hired': sum(1 for a in all_apps if a.status == ApplicationStatus.HIRED),
        'rejected': sum(1 for a in all_apps if a.status == ApplicationStatus.REJECTED),
    }

    return render_template('candidate/my_applications.html',
                           applications=applications,
                           stats=stats,
                           status_filter=status_filter)


@candidate_bp.route('/applications/<int:application_id>/withdraw', methods=['POST'])
@candidate_required
def withdraw_application(application_id):
    """Let a candidate withdraw a pending application."""
    application = Application.query.get_or_404(application_id)

    # Ownership check
    if application.user_id != current_user.id:
        abort(403)

    # Only allow withdrawing if still pending
    if application.status != ApplicationStatus.PENDING:
        flash('You can only withdraw applications that are still pending.', 'warning')
        return redirect(url_for('candidate.my_applications'))

    try:
        # Best-effort vector store cleanup
        try:
            from app.services.vector_store import VectorStore
            VectorStore.delete_application(application.id)
        except Exception as e:
            logger.warning(f'Vector store cleanup failed for app {application.id}: {e}')

        db.session.delete(application)
        db.session.commit()
        flash('Application withdrawn successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Withdraw failed: {e}')
        flash('Could not withdraw application. Please try again.', 'danger')

    return redirect(url_for('candidate.my_applications'))
