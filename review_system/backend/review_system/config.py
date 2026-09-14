from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("REVIEW_DATA_DIR", ROOT / "review_system" / "data"))
DATABASE_URL = os.getenv("REVIEW_DATABASE_URL", f"sqlite:///{DATA_DIR / 'review.db'}")
SECRET_KEY = os.getenv("REVIEW_SECRET_KEY", "dev-only-change-me")
SOURCE_ROOT = Path(os.getenv("REVIEW_SOURCE_ROOT", ROOT / "src" / "verifier_grounded_benchmark"))
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
