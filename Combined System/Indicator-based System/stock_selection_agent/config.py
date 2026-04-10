import os
from dotenv import load_dotenv

class Config:
    DEEPSEEK_API_KEY = None
    DEEPSEEK_BASE_URL = None
    DEEPSEEK_MODEL = None

    @staticmethod
    def get_config_dir():
        app_name = "stock-selection-agent"
        base_dir = os.getenv("APPDATA", os.path.expanduser("~"))
        config_dir = os.path.join(base_dir, app_name)
        return config_dir

    @staticmethod
    def get_env_path():
        config_dir = Config.get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, ".env")

    @classmethod
    def load(cls):
        # Also load from project root .env
        project_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(project_env_path):
            load_dotenv(project_env_path, override=True)

        env_path = cls.get_env_path()
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)

        cls.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
        cls.DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        cls.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    @classmethod
    def validate(cls):
        cls.load()
        if not cls.DEEPSEEK_API_KEY:
            raise ValueError("Missing DEEPSEEK_API_KEY in environment")

# Load on import
Config.load()
