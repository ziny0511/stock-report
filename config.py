# =============================================
# 주식 리포트 시스템 설정
# =============================================
# ⚠️  DART_API_KEY는 GitHub Secrets에서 자동 주입됩니다
# ⚠️  이 파일에 직접 키를 입력하지 마세요

import os

DART_API_KEY = os.environ.get("DART_API_KEY", "")

# KIS API — 발급 후 GitHub Secrets에 추가
APP_KEY    = os.environ.get("KIS_APP_KEY", "")
APP_SECRET = os.environ.get("KIS_APP_SECRET", "")

# 리포트 설정
REPORT_OUTPUT_DIR = "docs"   # GitHub Pages는 docs 폴더를 웹으로 서비스
