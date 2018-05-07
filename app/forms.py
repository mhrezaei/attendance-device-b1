from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, TextAreaField, RadioField, SelectField

from wtforms import validators, ValidationError


# User Define Form
class UserDefineForm(FlaskForm):
    first_name = StringField("First Name", [validators.DataRequired("Please enter the first name.")], render_kw={"placeholder": "First Name"})
    last_name = StringField("Last Name", [validators.DataRequired("Please enter the last name.")], render_kw={"placeholder": "Last Name"})
    code_melli = IntegerField("Code Melli", [validators.DataRequired("Please enter the code melli.")], render_kw={"placeholder": "Code Melli"})

    submit = SubmitField("Define the user")

# User Enroll Form
class UserEnrollForm(FlaskForm):
    id = IntegerField("ID", [validators.DataRequired("Please enter the id.")], render_kw={"placeholder": "ID"})

    submit = SubmitField("Enroll this user's Finger")


# RFID Form
class RfidWriteForm(FlaskForm):

    submit = SubmitField("Enroll this user's RFID Card")


