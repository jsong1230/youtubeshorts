import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

def get_authenticated_service():
    """YouTube API 인증 및 서비스 객체 반환"""
    creds = None
    
    # 환경 변수에서 refresh token 확인
    if config.YOUTUBE_REFRESH_TOKEN and config.YOUTUBE_CLIENT_ID and config.YOUTUBE_CLIENT_SECRET:
        try:
            # Refresh token을 사용하여 인증
            from google.oauth2.credentials import Credentials as RefreshCredentials
            
            # Refresh token으로 Credentials 생성
            creds = RefreshCredentials(
                token=None,
                refresh_token=config.YOUTUBE_REFRESH_TOKEN,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=config.YOUTUBE_CLIENT_ID,
                client_secret=config.YOUTUBE_CLIENT_SECRET,
                scopes=SCOPES
            )
            
            # Access token 갱신
            request = Request()
            creds.refresh(request)
            
            # 토큰 저장
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            
            print("✅ 환경 변수에서 인증 정보를 사용하여 인증 완료")
            
        except Exception as e:
            print(f"⚠️ 환경 변수 인증 실패: {e}")
            print("기존 token.json 파일을 사용합니다...")
            creds = None
    
    # 환경 변수 인증 실패 시 기존 token.json 사용
    if not creds or not creds.valid:
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                
                # 토큰이 만료된 경우 갱신
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                
                if creds and creds.valid:
                    print("✅ token.json 파일에서 인증 완료")
            except Exception as e:
                print(f"⚠️ token.json 인증 실패: {e}")
                creds = None
    
    # 모든 인증 방법 실패 시 - OAuth2 flow 실행
    if not creds or not creds.valid:
        # client_secrets.json이 없으면 환경 변수로 생성 시도
        if not os.path.exists('client_secrets.json'):
            if config.YOUTUBE_CLIENT_ID and config.YOUTUBE_CLIENT_SECRET:
                print("📝 client_secrets.json 파일을 생성합니다...")
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
                print("✅ client_secrets.json 파일 생성 완료")
            else:
                raise FileNotFoundError(
                    "인증 정보가 필요합니다. 다음 중 하나를 설정하세요:\n"
                    "1. .env 파일에 YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET 설정\n"
                    "2. client_secrets.json 파일을 프로젝트 루트에 배치"
                )
        
        print("\n🌐 브라우저에서 인증을 진행하세요...")
        print("   (브라우저가 자동으로 열립니다)\n")
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', SCOPES)
        
        try:
            creds = flow.run_local_server(port=8080, prompt='consent', open_browser=True)
        except Exception as e1:
            print(f"⚠️ 포트 8080 실패: {e1}")
            try:
                print("랜덤 포트로 재시도 중...")
                creds = flow.run_local_server(port=0, prompt='consent', open_browser=True)
            except Exception as e2:
                print(f"⚠️ 랜덤 포트 실패: {e2}")
                print("\n📋 수동 인증 코드 입력 방식으로 전환합니다...")
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"\n다음 URL을 브라우저에서 열어주세요:\n{auth_url}\n")
                print("인증 후 표시되는 코드를 복사하여 아래에 붙여넣으세요:")
                code = input("인증 코드: ").strip()
                flow.fetch_token(code=code)
                creds = flow.credentials
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        
        print("✅ 인증 완료! token.json 파일이 저장되었습니다.")
    
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)
