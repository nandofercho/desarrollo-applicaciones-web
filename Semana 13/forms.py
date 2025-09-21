from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Email

class ProductoForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=120)])
    cantidad = IntegerField('Cantidad', validators=[DataRequired(), NumberRange(min=0)])
    precio = DecimalField('Precio', places=2, validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Guardar')

class UsuarioForm(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Guardar")