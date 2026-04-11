from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class NewsStaticImageStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        location = Path(settings.BASE_DIR) / "static" / "img"
        base_url = f"{settings.STATIC_URL.rstrip('/')}/img/"
        super().__init__(location=location, base_url=base_url)


news_static_image_storage = NewsStaticImageStorage()
