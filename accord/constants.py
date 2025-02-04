import os
from pathlib import Path
from accord.utils import get_config

config = get_config()

CONCATENATE_EMBEDDED_FILE_PATH = os.path.join(config.artifacts_root,"embedded", "concatenate.pkl")
CONCATENATE_DOCUMENT_FILE_PATH = os.path.join(config.artifacts_root,"document", "concatenate.pkl")