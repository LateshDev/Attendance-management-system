from flask import Blueprint, render_template, request, Response, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from calendar import monthrange

from app.models import (
    db, Batch, Student, Subject, AttendanceSession, AttendanceRecord,
    BatchStudent, Setting
)
from app.utils.decorators import teacher_or_admin_required, check_batch_access
from app.utils.exporters import (
    generate_csv_response, generate_excel_response, generate_pdf_report
)

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    threshold = float(Setting.get_value('low_attendance_threshold', 75.0))
    return render_template('reports/index.html', threshold=threshold)


# ==========================================
# 1. BATCH ATTENDANCE REPORT
# ==========================================

@reports_bp.route('/batch')
@login_required
def batch_report():
    batch_id = request.args.get('batch_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    export = request.args.get('export', '').strip().lower()

    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    subjects = Subject.query.filter_by(status='Active').order_by(Subject.subject_name).all()

    selected_batch = None
    rows = []
    summary_stats = {}

    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if batch_id:
        selected_batch = Batch.query.get_or_404(batch_id)
        if not check_batch_access(selected_batch, current_user):
            abort(403)

        students = selected_batch.get_enrolled_students()
        total_present_all = 0
        total_absent_all = 0
        total_leave_all = 0
        total_classes_all = 0

        for st in students:
            stats = st.calculate_attendance_stats(
                batch_id=batch_id,
                subject_id=subject_id,
                start_date=start_date,
                end_date=end_date
            )
            rows.append({
                'roll_number': st.roll_number,
                'student_name': st.student_name,
                'mobile': st.mobile_number or '-',
                'total_classes': stats['total_classes'],
                'present': stats['present'],
                'absent': stats['absent'],
                'leave': stats['leave'],
                'percentage': stats['percentage']
            })
            total_present_all += stats['present']
            total_absent_all += stats['absent']
            total_leave_all += stats['leave']
            total_classes_all += stats['total_classes']

        avg_pct = round((total_present_all / total_classes_all) * 100.0, 1) if total_classes_all > 0 else 0.0
        summary_stats = {
            'Total Students': len(students),
            'Total Class Sessions': total_classes_all,
            'Total Present': total_present_all,
            'Total Absent': total_absent_all,
            'Average Attendance': f"{avg_pct}%"
        }

    # EXPORT HANDLING
    if export and selected_batch:
        headers = ['Roll No', 'Student Name', 'Total Classes', 'Present', 'Absent', 'Leave', 'Attendance %']
        export_data = [
            [r['roll_number'], r['student_name'], r['total_classes'], r['present'], r['absent'], r['leave'], f"{r['percentage']}%"]
            for r in rows
        ]

        title = f"Batch Attendance Report - {selected_batch.batch_name} ({selected_batch.batch_code})"
        meta_dict = {
            'Batch': selected_batch.batch_name,
            'Course': selected_batch.course_name,
            'Date Range': f"{start_date_str or 'All'} to {end_date_str or 'Today'}"
        }

        if export == 'csv':
            csv_bytes = generate_csv_response(f"batch_report_{selected_batch.batch_code}.csv", headers, export_data)
            return Response(
                csv_bytes,
                mimetype='text/csv',
                headers={"Content-Disposition": f"attachment;filename=batch_{selected_batch.batch_code}_report.csv"}
            )
        elif export == 'excel':
            meta_list = list(meta_dict.items()) + list(summary_stats.items())
            xlsx_bytes = generate_excel_response(
                f"batch_report_{selected_batch.batch_code}.xlsx",
                "Batch Attendance",
                title,
                meta_list,
                headers,
                export_data
            )
            return Response(
                xlsx_bytes,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment;filename=batch_{selected_batch.batch_code}_report.xlsx"}
            )
        elif export == 'pdf':
            pdf_bytes = generate_pdf_report(title, meta_dict, headers, export_data, summary_stats=summary_stats)
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={"Content-Disposition": f"attachment;filename=batch_{selected_batch.batch_code}_report.pdf"}
            )

    threshold = float(Setting.get_value('low_attendance_threshold', 75.0))

    return render_template(
        'reports/batch_report.html',
        batches=batches,
        subjects=subjects,
        selected_batch=selected_batch,
        selected_batch_id=batch_id,
        selected_subject_id=subject_id,
        start_date_str=start_date_str,
        end_date_str=end_date_str,
        rows=rows,
        summary_stats=summary_stats,
        threshold=threshold
    )


# ==========================================
# 2. LOW ATTENDANCE REPORT
# ==========================================

@reports_bp.route('/low-attendance')
@login_required
def low_attendance():
    batch_id = request.args.get('batch_id', type=int)
    threshold_input = request.args.get('threshold', type=float)
    export = request.args.get('export', '').strip().lower()

    default_threshold = float(Setting.get_value('low_attendance_threshold', 75.0))
    threshold = threshold_input if threshold_input is not None else default_threshold

    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    query = Student.query.filter_by(status='Active')
    if batch_id:
        query = query.join(BatchStudent).filter(BatchStudent.batch_id == batch_id, BatchStudent.status == 'Active')
    elif current_user.is_teacher:
        t_batch_ids = [b.id for b in batches]
        query = query.join(BatchStudent).filter(BatchStudent.batch_id.in_(t_batch_ids), BatchStudent.status == 'Active')

    all_students = query.order_by(Student.roll_number).all()
    low_records = []

    for st in all_students:
        stats = st.calculate_attendance_stats(batch_id=batch_id)
        # Only evaluate if student has at least 1 class session
        if stats['total_classes'] > 0 and stats['percentage'] < threshold:
            st_batches = ", ".join([b.batch_code for b in st.get_batches()])
            low_records.append({
                'student': st,
                'roll_number': st.roll_number,
                'student_name': st.student_name,
                'batches': st_batches or '-',
                'mobile': st.mobile_number or '-',
                'total_classes': stats['total_classes'],
                'present': stats['present'],
                'absent': stats['absent'],
                'percentage': stats['percentage']
            })

    # Sort lowest percentage first
    low_records.sort(key=lambda x: x['percentage'])

    # EXPORT
    if export:
        headers = ['Roll No', 'Student Name', 'Batch', 'Mobile', 'Total Classes', 'Present', 'Absent', 'Attendance %']
        export_data = [
            [r['roll_number'], r['student_name'], r['batches'], r['mobile'], r['total_classes'], r['present'], r['absent'], f"{r['percentage']}%"]
            for r in low_records
        ]
        title = f"Low Attendance Report (Threshold: < {threshold}%)"
        meta_dict = {
            'Threshold': f"{threshold}%",
            'Total Identified': str(len(low_records)),
            'Generated': date.today().strftime('%d-%m-%Y')
        }

        if export == 'csv':
            csv_bytes = generate_csv_response("low_attendance_report.csv", headers, export_data)
            return Response(csv_bytes, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=low_attendance_report.csv"})
        elif export == 'excel':
            xlsx_bytes = generate_excel_response("low_attendance.xlsx", "Defaulters", title, list(meta_dict.items()), headers, export_data)
            return Response(xlsx_bytes, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={"Content-Disposition": "attachment;filename=low_attendance_report.xlsx"})
        elif export == 'pdf':
            pdf_bytes = generate_pdf_report(title, meta_dict, headers, export_data)
            return Response(pdf_bytes, mimetype='application/pdf', headers={"Content-Disposition": "attachment;filename=low_attendance_report.pdf"})

    return render_template(
        'reports/low_attendance.html',
        batches=batches,
        selected_batch_id=batch_id,
        threshold=threshold,
        low_records=low_records
    )


# ==========================================
# 3. DAILY ATTENDANCE REPORT
# ==========================================

@reports_bp.route('/daily')
@login_required
def daily_report():
    today_str = date.today().strftime('%Y-%m-%d')
    date_str = request.args.get('session_date', today_str).strip()
    batch_id = request.args.get('batch_id', type=int)
    export = request.args.get('export', '').strip().lower()

    try:
        report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        report_date = date.today()
        date_str = today_str

    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    query = AttendanceSession.query.filter(AttendanceSession.session_date == report_date)
    if batch_id:
        query = query.filter(AttendanceSession.batch_id == batch_id)
    elif current_user.is_teacher:
        t_batch_ids = [b.id for b in batches]
        query = query.filter(AttendanceSession.batch_id.in_(t_batch_ids))

    sessions = query.all()
    rows = []
    for s in sessions:
        rows.append({
            'batch_code': s.batch.batch_code,
            'batch_name': s.batch.batch_name,
            'subject_name': s.subject.subject_name,
            'marked_by': s.marked_by.full_name,
            'total': s.total_records,
            'present': s.present_count,
            'absent': s.absent_count,
            'leave': s.leave_count,
            'percentage': s.attendance_percentage
        })

    if export:
        headers = ['Batch Code', 'Batch Name', 'Subject', 'Marked By', 'Total', 'Present', 'Absent', 'Leave', 'Attendance %']
        export_data = [
            [r['batch_code'], r['batch_name'], r['subject_name'], r['marked_by'], r['total'], r['present'], r['absent'], r['leave'], f"{r['percentage']}%"]
            for r in rows
        ]
        title = f"Daily Attendance Summary - {report_date.strftime('%d-%m-%Y')}"
        meta_dict = {'Date': report_date.strftime('%d-%m-%Y'), 'Sessions Count': str(len(sessions))}

        if export == 'csv':
            csv_bytes = generate_csv_response(f"daily_report_{date_str}.csv", headers, export_data)
            return Response(csv_bytes, mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename=daily_report_{date_str}.csv"})
        elif export == 'excel':
            xlsx_bytes = generate_excel_response(f"daily_{date_str}.xlsx", "Daily Summary", title, list(meta_dict.items()), headers, export_data)
            return Response(xlsx_bytes, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={"Content-Disposition": f"attachment;filename=daily_{date_str}.xlsx"})
        elif export == 'pdf':
            pdf_bytes = generate_pdf_report(title, meta_dict, headers, export_data)
            return Response(pdf_bytes, mimetype='application/pdf', headers={"Content-Disposition": f"attachment;filename=daily_{date_str}.pdf"})

    return render_template(
        'reports/daily_report.html',
        batches=batches,
        selected_batch_id=batch_id,
        date_str=date_str,
        report_date=report_date,
        rows=rows
    )


# ==========================================
# 4. SUBJECT-WISE ATTENDANCE REPORT
# ==========================================

@reports_bp.route('/subjects')
@login_required
def subject_report():
    batch_id = request.args.get('batch_id', type=int)
    batches = Batch.query.filter_by(status='Active').order_by(Batch.batch_name).all()
    if current_user.is_teacher:
        batches = [b for b in batches if b.teacher_id == current_user.id]

    subjects = Subject.query.filter_by(status='Active').order_by(Subject.subject_name).all()
    selected_batch = None
    subject_stats = []

    if batch_id:
        selected_batch = Batch.query.get_or_404(batch_id)
        for sub in subjects:
            sessions = AttendanceSession.query.filter_by(batch_id=batch_id, subject_id=sub.id).all()
            if sessions:
                s_ids = [s.id for s in sessions]
                records = AttendanceRecord.query.filter(AttendanceRecord.session_id.in_(s_ids)).all()
                total = len(records)
                p = sum(1 for r in records if r.status == 'Present')
                a = sum(1 for r in records if r.status == 'Absent')
                l = sum(1 for r in records if r.status == 'Leave')
                pct = round((p / total) * 100.0, 1) if total > 0 else 0.0
                subject_stats.append({
                    'subject': sub,
                    'total_sessions': len(sessions),
                    'total_records': total,
                    'present': p,
                    'absent': a,
                    'leave': l,
                    'percentage': pct
                })

    return render_template(
        'reports/subject_report.html',
        batches=batches,
        selected_batch_id=batch_id,
        selected_batch=selected_batch,
        subject_stats=subject_stats
    )
