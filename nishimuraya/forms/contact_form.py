from django import forms

# 入力欄共通スタイル（Tailwindユーティリティ）。旧 .contact-form input/textarea 相当。
FIELD_CLASS = (
    "w-full border border-field-line rounded-[10px] "
    "bg-field-bg text-[#f3ebe3] text-[15px] px-[14px] py-3 "
    "max-[640px]:text-[14px]"
)


class ContactForm(forms.Form):
    name = forms.CharField(
        label="お名前",
        max_length=100,
        widget=forms.TextInput(attrs={"id": "contact-name", "class": FIELD_CLASS}),
    )
    email = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={"id": "contact-email", "class": FIELD_CLASS}),
    )
    phone = forms.CharField(
        label="電話番号（任意）",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"id": "contact-phone", "inputmode": "tel", "class": FIELD_CLASS}),
    )
    message = forms.CharField(
        label="お問い合わせ内容",
        widget=forms.Textarea(attrs={"id": "contact-message", "rows": 7, "class": FIELD_CLASS + " resize-y"}),
    )
