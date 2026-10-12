"""WTForms validation shared by HTML submissions and the JSON search API."""
from wtforms import Form, TextAreaField
from wtforms.validators import DataRequired, Length


class TextInputForm(Form):
    text = TextAreaField(validators=[DataRequired(message='Please enter an answer.')])


def validate_text(value, limit=2000):
    if not isinstance(value, str):
        return 'Please enter an answer.'
    form = TextInputForm(data={'text': value})
    length = Length(max=limit, message=f'Please use no more than {limit:,} characters.')
    if form.validate(extra_validators={'text': [length]}):
        return None
    return form.text.errors[0]
