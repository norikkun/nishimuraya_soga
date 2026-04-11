from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(
        label="お名前",
        max_length=100,
        widget=forms.TextInput(attrs={"id": "contact-name"}),
    )
    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={"id": "contact-email"}),
    )
    phone = forms.CharField(
        label="電話番号（任意）",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"id": "contact-phone", "inputmode": "tel"}),
    )
    message = forms.CharField(
        label="お問い合わせ内容",
        widget=forms.Textarea(attrs={"id": "contact-message", "rows": 7}),
    )
