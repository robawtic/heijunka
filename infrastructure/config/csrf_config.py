from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel
from infrastructure.config.settings import settings

class CSRFSettings(BaseModel):
    secret_key: str = settings.csrf_secret

@CsrfProtect.load_config
def get_csrf_config():
    return CSRFSettings()