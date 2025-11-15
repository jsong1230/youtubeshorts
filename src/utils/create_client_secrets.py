"""
client_secrets.json 파일 생성 스크립트
"""
import json
import config

client_secrets = {
    "installed": {
        "client_id": config.YOUTUBE_CLIENT_ID,
        "project_id": "youtube-shorts-bot",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": config.YOUTUBE_CLIENT_SECRET,
        "redirect_uris": [
            "http://localhost:8080/",
            "http://127.0.0.1:8080/",
            "http://localhost/"
        ]
    }
}

with open('client_secrets.json', 'w') as f:
    json.dump(client_secrets, f, indent=2)

print("✅ client_secrets.json 파일이 생성되었습니다!")

