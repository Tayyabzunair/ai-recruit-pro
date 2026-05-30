"""
Owner blueprint routes - dashboard, job management, candidates.
"""
from datetime import datetime, timedelta
from flask import render_template, redirect, url_for, flash, request, abort, send_from_directory, current_app
from flask_login import current_user
from sqlalchemy import func, desc
from loguru import logger

from app.blueprints.owner import owner_bp
from app.blueprints.owner.forms import JobForm
from app.extensions import db
from app.models.job import Job
from app.models.user import User
from app.models.application import Application, ApplicationStatus
from app.utils.decorators import owner_required


@owner_bp.route('/dashboard')
@owner_required
def dashboard():
    """Owner main dashboard with stats."""
    total_jobs = Job.query.filter_by(posted_by_id=current_user.id).count()
    active_jobs = Job.query.filter_by(posted_by_id=current_user.id, is_active=True).count()

    applications_q = Application.query.join(Job).filter(Job.posted_by_id == current_user.id)
    total_applications = applications_q.count()

    pending_count = applications_q.filter(Application.status == ApplicationStatus.PENDING).count()
    shortlisted_count = applications_q.filter(Application.status == ApplicationStatus.SHORTLISTED).count()
    hired_count = applications_q.filter(Application.status == ApplicationStatus.HIRED).count()

    recent_applications = applications_q.order_by(desc(Application.applied_at)).limit(5).all()
    top_candidates = applications_q.order_by(desc(Application.match_score)).limit(5).all()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_apps = db.session.query(
        func.date(Application.applied_at).label('date'),
        func.count(Application.id).label('count')
    ).join(Job).filter(
        Job.posted_by_id == current_user.id,
        Application.applied_at >= seven_days_ago
    ).group_by(func.date(Application.applied_at)).all()

    chart_labels = []
    chart_values = []
    for row in daily_apps:
        chart_labels.append(str(row[0]))
        chart_values.append(int(row[1]))

    if not chart_labels:
        chart_labels = ['No data yet']
        chart_values = [0]

    chart_data = {
        'labels': chart_labels,
        'values': chart_values,
    }

    return render_template('owner/dashboard.html',
                           total_jobs=total_jobs,
                           active_jobs=active_jobs,
                           total_applications=total_applications,
                           pending_count=pending_count,
                           shortlisted_count=shortlisted_count,
                           hired_count=hired_count,
                           recent_applications=recent_applications,
                           top_candidates=top_candidates,
                           chart_data=chart_data)


# ============================================================
# JOB MANAGEMENT
# ============================================================

@owner_bp.route('/jobs')
@owner_required
def jobs():
    """List all jobs posted by current owner."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')

    query = Job.query.filter_by(posted_by_id=current_user.id)
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)

    jobs_page = query.order_by(desc(Job.created_at)).paginate(page=page, per_page=10, error_out=False)

    return render_template('owner/jobs.html', jobs=jobs_page, status_filter=status_filter)


@owner_bp.route('/jobs/new', methods=['GET', 'POST'])
@owner_required
def post_job():
    """Create new job posting."""
    form = JobForm()
    if form.validate_on_submit():
        job = Job(
            title=form.title.data,
            company=form.company.data or current_user.name,
            location=form.location.data,
            job_type=form.job_type.data,
            experience_level=form.experience_level.data,
            salary_min=form.salary_min.data,
            salary_max=form.salary_max.data,
            salary_currency=form.salary_currency.data,
            description=form.description.data,
            responsibilities=form.responsibilities.data,
            requirements=form.requirements.data,
            benefits=form.benefits.data,
            skills=form.skills.data,
            deadline=form.deadline.data,
            posted_by_id=current_user.id,
        )
        db.session.add(job)
        db.session.commit()
        logger.info(f'New job posted: {job.title} by user {current_user.id}')
        flash(f'Job "{job.title}" posted successfully!', 'success')
        return redirect(url_for('owner.jobs'))

    return render_template('owner/post_job.html', form=form, is_edit=False)


@owner_bp.route('/jobs/<int:job_id>/edit', methods=['GET', 'POST'])
@owner_required
def edit_job(job_id):
    """Edit an existing job posting."""
    job = Job.query.get_or_404(job_id)
    if job.posted_by_id != current_user.id:
        abort(403)

    form = JobForm(obj=job)

    if form.validate_on_submit():
        try:
            job.title = form.title.data
            job.company = form.company.data or current_user.name
            job.location = form.location.data
            job.job_type = form.job_type.data
            job.experience_level = form.experience_level.data
            job.salary_min = form.salary_min.data
            job.salary_max = form.salary_max.data
            job.salary_currency = form.salary_currency.data
            job.description = form.description.data
            job.responsibilities = form.responsibilities.data
            job.requirements = form.requirements.data
            job.benefits = form.benefits.data
            job.skills = form.skills.data
            job.deadline = form.deadline.data

            db.session.commit()
            logger.info(f'Job {job.id} updated by owner {current_user.id}')
            flash(f'Job "{job.title}" updated successfully!', 'success')
            return redirect(url_for('owner.jobs'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Failed to update job {job.id}: {e}')
            flash('Failed to update job. Please try again.', 'danger')

    return render_template('owner/post_job.html', form=form, is_edit=True, job=job)


@owner_bp.route('/jobs/<int:job_id>/delete', methods=['POST'])
@owner_required
def delete_job(job_id):
    """Delete job (cascades applications) + cleanup vector store."""
    job = Job.query.get_or_404(job_id)
    if job.posted_by_id != current_user.id:
        abort(403)

    # Cleanup vector store before deleting
    try:
        from app.services.vector_store import VectorStore
        for application in job.applications:
            VectorStore.delete_application(application.id)
    except Exception as e:
        logger.warning(f'Vector store cleanup failed for job {job.id}: {e}')

    title = job.title
    db.session.delete(job)
    db.session.commit()
    flash(f'Job "{title}" deleted.', 'info')
    return redirect(url_for('owner.jobs'))


@owner_bp.route('/jobs/<int:job_id>/toggle', methods=['POST'])
@owner_required
def toggle_job(job_id):
    """Activate/deactivate job."""
    job = Job.query.get_or_404(job_id)
    if job.posted_by_id != current_user.id:
        abort(403)

    job.is_active = not job.is_active
    db.session.commit()
    flash(f'Job {"activated" if job.is_active else "deactivated"}.', 'info')
    return redirect(url_for('owner.jobs'))


# ============================================================
# CANDIDATE MANAGEMENT
# ============================================================

@owner_bp.route('/candidates')
@owner_required
def candidates():
    """List all candidates who applied to owner's jobs."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    job_filter = request.args.get('job_id', type=int)
    sort_by = request.args.get('sort', 'score')

    query = Application.query.join(Job).filter(Job.posted_by_id == current_user.id)

    if status_filter != 'all':
        query = query.filter(Application.status == status_filter)
    if job_filter:
        query = query.filter(Application.job_id == job_filter)

    if sort_by == 'date':
        query = query.order_by(desc(Application.applied_at))
    else:
        query = query.order_by(desc(Application.match_score))

    applications = query.paginate(page=page, per_page=15, error_out=False)

    owner_jobs = Job.query.filter_by(posted_by_id=current_user.id).order_by(Job.title).all()

    return render_template('owner/candidates.html',
                           applications=applications,
                           owner_jobs=owner_jobs,
                           status_filter=status_filter,
                           job_filter=job_filter,
                           sort_by=sort_by,
                           statuses=ApplicationStatus.ALL)


@owner_bp.route('/candidates/<int:app_id>')
@owner_required
def candidate_detail(app_id):
    """View candidate application details."""
    application = Application.query.get_or_404(app_id)
    if application.job.posted_by_id != current_user.id:
        abort(403)

    from app.services.matcher import SkillMatcher
    skill_analysis = SkillMatcher.get_matched_skills(application.skills, application.job.skills)

    return render_template('owner/candidate_detail.html',
                           application=application,
                           skill_analysis=skill_analysis,
                           statuses=ApplicationStatus.ALL)


@owner_bp.route('/candidates/<int:app_id>/status', methods=['POST'])
@owner_required
def update_status(app_id):
    """Update application status and notify candidate."""
    application = Application.query.get_or_404(app_id)
    if application.job.posted_by_id != current_user.id:
        abort(403)

    new_status = request.form.get('status')
    if new_status not in ApplicationStatus.ALL:
        flash('Invalid status.', 'danger')
        return redirect(request.referrer or url_for('owner.candidates'))

    # Capture old status BEFORE updating
    old_status = application.status

    application.status = new_status
    notes = request.form.get('notes')
    if notes:
        application.notes = notes

    db.session.commit()

    # Send status update email only if status actually changed
    if old_status != new_status:
        try:
            from app.services.email_service import EmailService
            EmailService.send_status_update(application, old_status, new_status)
        except Exception as e:
            logger.error(f'Status email failed: {e}')

    flash(f'Status updated to "{new_status}".', 'success')
    return redirect(request.referrer or url_for('owner.candidates'))


@owner_bp.route('/resume/<int:app_id>')
@owner_required
def view_resume(app_id):
    """Securely serve resume PDF."""
    application = Application.query.get_or_404(app_id)
    if application.job.posted_by_id != current_user.id:
        abort(403)

    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        application.resume_filename,
        as_attachment=False
    )
