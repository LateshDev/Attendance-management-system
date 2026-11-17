import io
import csv
from datetime import date
from flask import Blueprint, render_template, request, make_response, send_file, flash, redirect, url_for
from flask_login import login_required
from app.models import ClassGroup, Student, Subject, Attendance, AttendanceSession, Teacher
from app.routes.auth import role_required

reports_bp = Blueprint('reports', __name__)

@reports_bp.before_request
@login_required
@role_required('admin', 'hod', 'teacher')
def check_staff():
    pass

@reports_bp.route('/')
def index():
    classes = ClassGroup.query.all()
    selected_class_id = request.args.get('class_id', type=int) or (classes[0].id if classes else None)
    
    selected_class = ClassGroup.query.get(selected_class_id) if selected_class_id else None
    students = Student.query.filter_by(class_id=selected_class_id).order_by(Student.roll_number).all() if selected_class_id else []
    subjects = Subject.query.filter_by(course_id=selected_class.course_id, semester=selected_class.semester).all() if selected_class else []

    # Get all conducted sessions for this class
    sessions = AttendanceSession.query.filter_by(class_id=selected_class_id).all() if selected_class_id else []
    total_conducted = len(sessions)

    # Calculate student statistics
    student_stats = []
    defaulters = []

    for s in students:
        records = Attendance.query.filter_by(student_id=s.id).all()
        s_conducted = len(records)
        s_attended = sum(1 for r in records if r.status in ['Present', 'Late'])
        pct = round((s_attended / s_conducted * 100), 1) if s_conducted > 0 else 0.0

        # Subject-wise
        sub_breakdown = {}
        for sub in subjects:
            sub_recs = [r for r in records if r.session.subject_id == sub.id]
            sub_cond = len(sub_recs)
            sub_att = sum(1 for r in sub_recs if r.status in ['Present', 'Late'])
            sub_pct = round((sub_att / sub_cond * 100), 1) if sub_cond > 0 else 0.0
            sub_breakdown[sub.id] = {'conducted': sub_cond, 'attended': sub_att, 'pct': sub_pct}

        stat = {
            'student': s,
            'conducted': s_conducted,
            'attended': s_attended,
            'percentage': pct,
            'is_defaulter': pct < 75.0 and s_conducted > 0,
            'subjects': sub_breakdown
        }
        student_stats.append(stat)
        if stat['is_defaulter']:
            defaulters.append(stat)

    return render_template(
        'reports/index.html',
        classes=classes,
        selected_class=selected_class,
        students=students,
        subjects=subjects,
        total_conducted=total_conducted,
        student_stats=student_stats,
        defaulters=defaulters
    )


@reports_bp.route('/export/excel/<int:class_id>')
def export_excel(class_id):
    cls = ClassGroup.query.get_or_404(class_id)
    students = Student.query.filter_by(class_id=class_id).order_by(Student.roll_number).all()
    subjects = Subject.query.filter_by(course_id=cls.course_id, semester=cls.semester).all()

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Attendance {cls.section}"

        # Header Title
        ws.merge_cells('A1:G1')
        ws['A1'] = f"FACULTY OF TECHNOLOGY AND COMPUTER APPLICATIONS"
        ws['A1'].font = Font(size=14, bold=True, color="1E3A8A")
        ws['A1'].alignment = Alignment(horizontal="center")

        ws.merge_cells('A2:G2')
        ws['A2'] = f"Attendance Report - {cls.name} Section {cls.section} (Academic Year {cls.academic_year})"
        ws['A2'].font = Font(size=11, bold=True, color="374151")
        ws['A2'].alignment = Alignment(horizontal="center")

        # Table Column Headers
        headers = ["Roll No", "Student Name", "Total Lectures", "Attended", "Attendance %", "Defaulter (<75%)"]
        for sub in subjects:
            headers.append(f"{sub.code} %")

        ws.append([])  # Blank row
        ws.append(headers)

        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=4, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        # Data Rows
        row_idx = 5
        for s in students:
            records = Attendance.query.filter_by(student_id=s.id).all()
            cond = len(records)
            att = sum(1 for r in records if r.status in ['Present', 'Late'])
            pct = round((att / cond * 100), 1) if cond > 0 else 0.0
            is_def = "YES" if (pct < 75.0 and cond > 0) else "NO"

            row_data = [s.roll_number, s.full_name, cond, att, f"{pct}%", is_def]

            for sub in subjects:
                sub_recs = [r for r in records if r.session.subject_id == sub.id]
                sub_cond = len(sub_recs)
                sub_att = sum(1 for r in sub_recs if r.status in ['Present', 'Late'])
                sub_pct = round((sub_att / sub_cond * 100), 1) if sub_cond > 0 else 0.0
                row_data.append(f"{sub_pct}%")

            ws.append(row_data)

            # Highlight defaulters in red
            if is_def == "YES":
                def_cell = ws.cell(row=row_idx, column=6)
                def_cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                def_cell.font = Font(color="DC2626", bold=True)

            row_idx += 1

        # Adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"Attendance_Report_{cls.section}_{date.today().strftime('%Y%m%d')}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except ImportError:
        # CSV Fallback
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Roll No", "Student Name", "Total Lectures", "Attended", "Attendance %", "Defaulter"])
        for s in students:
            records = Attendance.query.filter_by(student_id=s.id).all()
            cond = len(records)
            att = sum(1 for r in records if r.status in ['Present', 'Late'])
            pct = round((att / cond * 100), 1) if cond > 0 else 0.0
            is_def = "YES" if (pct < 75.0 and cond > 0) else "NO"
            writer.writerow([s.roll_number, s.full_name, cond, att, f"{pct}%", is_def])

        resp = make_response(output.getvalue())
        resp.headers["Content-Disposition"] = f"attachment; filename=Attendance_{cls.section}.csv"
        resp.headers["Content-type"] = "text/csv"
        return resp


@reports_bp.route('/export/pdf/<int:class_id>')
def export_pdf(class_id):
    cls = ClassGroup.query.get_or_404(class_id)
    students = Student.query.filter_by(class_id=class_id).order_by(Student.roll_number).all()

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=1,
            spaceAfter=6
        )
        sub_style = ParagraphStyle(
            'SubStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4B5563'),
            alignment=1,
            spaceAfter=15
        )

        elements.append(Paragraph("FACULTY OF TECHNOLOGY AND COMPUTER APPLICATIONS", title_style))
        elements.append(Paragraph(f"Official Attendance & Defaulter Report — {cls.name} {cls.section} (Session {cls.academic_year})", sub_style))

        # Table data
        data = [["Roll No", "Student Name", "Lectures", "Attended", "Attendance %", "Status"]]
        for s in students:
            records = Attendance.query.filter_by(student_id=s.id).all()
            cond = len(records)
            att = sum(1 for r in records if r.status in ['Present', 'Late'])
            pct = round((att / cond * 100), 1) if cond > 0 else 0.0
            status_text = "Defaulter (<75%)" if (pct < 75.0 and cond > 0) else "Eligible"
            data.append([s.roll_number, s.full_name, str(cond), str(att), f"{pct}%", status_text])

        t = Table(data, colWidths=[80, 160, 60, 60, 80, 110])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ]))
        elements.append(t)

        doc.build(elements)
        buffer.seek(0)

        filename = f"Attendance_Report_{cls.section}_{date.today().strftime('%Y%m%d')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except ImportError:
        flash("ReportLab not installed for PDF. Please use Excel export.", "warning")
        return redirect(url_for('reports.index', class_id=class_id))

