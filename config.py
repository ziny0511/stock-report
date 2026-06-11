import os

DART_API_KEY = os.environ.get("DART_API_KEY", "")
KRX_API_KEY  = os.environ.get("KRX_API_KEY", "")

# KIS API — 발급 후 GitHub Secrets에 추가
APP_KEY    = os.environ.get("KIS_APP_KEY", "")
APP_SECRET = os.environ.get("KIS_APP_SECRET", "")

REPORT_OUTPUT_DIR = "docs"
