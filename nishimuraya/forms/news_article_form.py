from django import forms

from ..models import NewsArticle


class NewsImageClearableFileInput(forms.ClearableFileInput):
    template_name = "nishimuraya/widgets/news_clearable_file_input.html"
    initial_text = "現在の写真"
    input_text = "新しい写真に差し替え"
    clear_checkbox_label = "この写真を削除する"


class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = NewsArticle
        fields = ["title", "content", "image"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "タイトルを入力してください"}),
            "content": forms.Textarea(
                attrs={
                    "rows": 12,
                    "placeholder": "本文を入力してください",
                }
            ),
            "image": NewsImageClearableFileInput(attrs={"accept": "image/*"}),
        }
