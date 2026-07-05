from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


# 0004_alter_newsarticle_image.py から参照されるため残しています。
# 現在の投稿画像は Django 標準ストレージを使い、MEDIA_ROOT に保存します。
@deconstructible
class NewsStaticImageStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        location = Path(settings.BASE_DIR) / "static" / "img"
        base_url = f"{settings.STATIC_URL.rstrip('/')}/img/"
        super().__init__(location=location, base_url=base_url)


news_static_image_storage = NewsStaticImageStorage()
