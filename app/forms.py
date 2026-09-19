from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField, SelectField,
    DateField, TextAreaField, FloatField, IntegerField, HiddenField
)
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo, NumberRange, ValidationError
from datetime import date
from app.models import User, Student, Batch, Subject


class LoginForm(FlaskForm):
    login_id = StringField('Email or Username', validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class UserForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active Account', default=True)
    submit = SubmitField('Save User')

    def __init__(self, original_user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_user = original_user

    def validate_email(self, field):
        if self.original_user and self.original_user.email.lower() == field.data.lower():
            return
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError('Email is already registered by another account.')

    def validate_username(self, field):
        if self.original_user and self.original_user.username.lower() == field.data.lower():
            return
        user = User.query.filter_by(username=field.data.lower()).first()
        if user:
            raise ValidationError('Username is already taken.')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match.')])
    submit = SubmitField('Update Password')


class BatchForm(FlaskForm):
    batch_name = StringField('Batch Name', validators=[DataRequired(), Length(max=120)])
    batch_code = StringField('Batch Code', validators=[DataRequired(), Length(max=50)])
    course_name = StringField('Course / Class', validators=[DataRequired(), Length(max=120)])
    teacher_id = SelectField('Assigned Teacher (In-Charge)', coerce=int, validators=[Optional()])
    start_date = DateField('Start Date', default=date.today, validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Archived', 'Archived')], default='Active')
    submit = SubmitField('Save Batch')

    def __init__(self, original_batch=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_batch = original_batch

    def validate_batch_code(self, field):
        if self.original_batch and self.original_batch.batch_code.upper() == field.data.upper():
            return
        batch = Batch.query.filter_by(batch_code=field.data.upper()).first()
        if batch:
            raise ValidationError('Batch Code must be unique.')


class StudentForm(FlaskForm):
    roll_number = StringField('Roll Number / Student ID', validators=[DataRequired(), Length(max=50)])
    student_name = StringField('Student Name', validators=[DataRequired(), Length(max=120)])
    father_name = StringField("Father's Name", validators=[Optional(), Length(max=120)])
    mother_name = StringField("Mother's Name", validators=[Optional(), Length(max=120)])
    mobile_number = StringField('Mobile Number', validators=[Optional(), Length(max=20)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    admission_date = DateField('Admission Date', default=date.today, validators=[DataRequired()])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    batch_id = SelectField('Assign to Batch', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Student')

    def __init__(self, original_student=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_student = original_student

    def validate_roll_number(self, field):
        if self.original_student and self.original_student.roll_number.upper() == field.data.upper():
            return
        student = Student.query.filter_by(roll_number=field.data.upper()).first()
        if student:
            raise ValidationError('Roll Number already exists.')


class StudentImportForm(FlaskForm):
    batch_id = SelectField('Enroll in Batch (Optional)', coerce=int, validators=[Optional()])
    file = FileField('CSV or Excel File', validators=[
        FileRequired(),
        FileAllowed(['csv', 'xlsx', 'xls'], 'Only CSV or Excel (.xlsx, .xls) files are supported!')
    ])
    submit = SubmitField('Upload & Import Students')


class SubjectForm(FlaskForm):
    subject_name = StringField('Subject Name', validators=[DataRequired(), Length(max=120)])
    subject_code = StringField('Subject Code', validators=[DataRequired(), Length(max=50)])
    description = StringField('Description', validators=[Optional(), Length(max=255)])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Inactive', 'Inactive')], default='Active')
    submit = SubmitField('Save Subject')

    def __init__(self, original_subject=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_subject = original_subject

    def validate_subject_code(self, field):
        if self.original_subject and self.original_subject.subject_code.upper() == field.data.upper():
            return
        subj = Subject.query.filter_by(subject_code=field.data.upper()).first()
        if subj:
            raise ValidationError('Subject Code must be unique.')


class LeaveRequestForm(FlaskForm):
    student_id = SelectField('Student', coerce=int, validators=[DataRequired()])
    batch_id = SelectField('Batch', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', default=date.today, validators=[DataRequired()])
    end_date = DateField('End Date', default=date.today, validators=[DataRequired()])
    reason = TextAreaField('Reason for Leave', validators=[DataRequired(), Length(min=5, max=1000)])
    submit = SubmitField('Submit Leave Request')

    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError('End date cannot be earlier than start date.')


class LeaveReviewForm(FlaskForm):
    status = SelectField('Action', choices=[('Approved', 'Approve Leave'), ('Rejected', 'Reject Leave')], validators=[DataRequired()])
    review_notes = StringField('Remarks / Review Notes', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Update Leave Status')


class SettingsForm(FlaskForm):
    institution_name = StringField('Institution / School / College Name', validators=[DataRequired(), Length(max=150)])
    contact_email = StringField('Official Contact Email', validators=[Optional(), Email(), Length(max=120)])
    academic_session = StringField('Academic Session / Year', validators=[DataRequired(), Length(max=50)])
    low_attendance_threshold = FloatField('Low Attendance Alert Threshold (%)', validators=[
        DataRequired(), NumberRange(min=1.0, max=100.0, message='Threshold must be between 1% and 100%')
    ])
    submit = SubmitField('Save Settings')
