from imagekitio import AsyncImageKit

from app.core.settings import get_settings

settings = get_settings()

imagekit_client = AsyncImageKit(
    private_key=settings.imagekit_private_key.get_secret_value()
)
