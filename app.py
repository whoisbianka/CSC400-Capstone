import argparse
import os
from pathlib import Path

import certifi
from dotenv import load_dotenv

# Load configuration before importing application/networking code.
load_dotenv(Path(__file__).resolve().parent / ".env")

# Use certifi unless an explicit certificate bundle was configured.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault(
    "REQUESTS_CA_BUNDLE",
    os.environ["SSL_CERT_FILE"],
)

from degree_path import create_app

app = create_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    app.run(host="127.0.0.1", port=args.port, debug=False)