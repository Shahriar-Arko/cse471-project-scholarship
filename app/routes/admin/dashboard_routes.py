from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.routes.admin import admin_bp
from app.models.user import User
from app.models.professor import Professor
from app.models.scholarship import Scholarship
from app.models.evaluator import Evaluator # <-- REQUIRED IMPORT

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if getattr(current_user, 'role', '') != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('auth.login'))

    # Fetch Pending Evaluators
    pending_evaluators = list(Evaluator.objects(is_approved=False))
    pending_evaluators_count = len(pending_evaluators)

    return render_template('admin/admin_dashboard.html', 
                       students_count=User.objects().count(), 
                       professors_count=Professor.objects().count(), 
                       scholarships_count=Scholarship.objects().count(),
                       pending_evaluators=pending_evaluators,
                       pending_evaluators_count=pending_evaluators_count)

# --- THIS IS THE MISSING ROUTE FLASK WAS LOOKING FOR ---
@admin_bp.route('/approve-evaluator/<evaluator_id>', methods=['POST'])
@login_required
def approve_evaluator(evaluator_id):
    if getattr(current_user, 'role', '') != 'admin':
        return redirect(url_for('admin.admin_dashboard'))

    evaluator = Evaluator.objects(id=evaluator_id).first()
    
    if evaluator:
        evaluator.is_approved = True
        evaluator.save()
        flash(f'Evaluator {evaluator.full_name} has been approved!', 'success')
    else:
        flash('Evaluator not found.', 'error')
        
    return redirect(url_for('admin.admin_dashboard'))



@admin_bp.route('/reject-evaluator/<evaluator_id>', methods=['POST'])
@login_required
def reject_evaluator(evaluator_id):
    if getattr(current_user, 'role', '') != 'admin':
        return redirect(url_for('admin.admin_dashboard'))

    from app.models.evaluator import Evaluator
    evaluator = Evaluator.objects(id=evaluator_id).first()
    
    if evaluator:
        name = evaluator.full_name
        evaluator.delete() # This permanently removes them from the database
        flash(f'Registration request from {name} has been rejected and deleted.', 'info')
    else:
        flash('Evaluator not found.', 'error')
        
    return redirect(url_for('admin.admin_dashboard'))