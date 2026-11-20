"""
Plant Areas Management Routes.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models.plant import PlantArea
from models.user import User
from services.auth_service import login_required, roles_required
from services.audit_service import log_action

plant_areas_bp = Blueprint("plant_areas", __name__)


@plant_areas_bp.route("/plant-areas")
@login_required
def index():
    areas = PlantArea.query.order_by(PlantArea.name).all()
    return render_template("plant_areas/index.html", areas=areas)


@plant_areas_bp.route("/plant-areas/new", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        description = request.form.get("description", "").strip()

        if not name or not code:
            flash("Name and Code are required.", "danger")
            return render_template("plant_areas/form.html", area=None)

        if PlantArea.query.filter((PlantArea.name == name) | (PlantArea.code == code)).first():
            flash("A plant area with this Name or Code already exists.", "danger")
            return render_template("plant_areas/form.html", area=None)

        area = PlantArea(name=name, code=code, description=description, is_active=True)
        db.session.add(area)
        db.session.commit()
        log_action("CREATE_PLANT_AREA", "PlantArea", area.id, f"Created plant area '{area.name}' ({area.code})")
        flash(f"Plant area '{area.name}' created successfully.", "success")
        return redirect(url_for("plant_areas.index"))

    return render_template("plant_areas/form.html", area=None)


@plant_areas_bp.route("/plant-areas/<int:area_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def edit(area_id):
    area = PlantArea.query.get_or_404(area_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        description = request.form.get("description", "").strip()

        if not name or not code:
            flash("Name and Code are required.", "danger")
            return render_template("plant_areas/form.html", area=area)

        duplicate = PlantArea.query.filter(
            ((PlantArea.name == name) | (PlantArea.code == code)) & (PlantArea.id != area.id)
        ).first()
        if duplicate:
            flash("Another plant area with this Name or Code already exists.", "danger")
            return render_template("plant_areas/form.html", area=area)

        area.name = name
        area.code = code
        area.description = description
        db.session.commit()
        log_action("EDIT_PLANT_AREA", "PlantArea", area.id, f"Updated plant area '{area.name}'")
        flash(f"Plant area '{area.name}' updated successfully.", "success")
        return redirect(url_for("plant_areas.index"))

    return render_template("plant_areas/form.html", area=area)


@plant_areas_bp.route("/plant-areas/<int:area_id>/toggle", methods=["POST"])
@login_required
@roles_required(User.ROLE_ADMIN)
def toggle(area_id):
    area = PlantArea.query.get_or_404(area_id)
    area.is_active = not area.is_active
    db.session.commit()
    log_action("TOGGLE_PLANT_AREA", "PlantArea", area.id, f"Plant area {area.name} active state set to {area.is_active}")
    flash(f"Plant area '{area.name}' status updated to {'Active' if area.is_active else 'Deactivated'}.", "info")
    return redirect(url_for("plant_areas.index"))
