"""
YouTube Shorts 자동 업로드 모듈
"""
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config


class YouTubeUploader:
    """YouTube API를 사용한 영상 업로드 클래스"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.readonly'  # 통계 정보 조회용
    ]
    API_SERVICE_NAME = 'youtube'
    API_VERSION = 'v3'
    
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """YouTube API 인증"""
        creds = None
        
        # 환경 변수에서 refresh token 확인
        if config.YOUTUBE_REFRESH_TOKEN and config.YOUTUBE_CLIENT_ID and config.YOUTUBE_CLIENT_SECRET:
            try:
                # Refresh token을 사용하여 인증
                from google.oauth2.credentials import Credentials as RefreshCredentials
                
                # Refresh token으로 Credentials 생성 (access token은 None으로 시작)
                creds = RefreshCredentials(
                    token=None,  # access token은 자동으로 갱신됨
                    refresh_token=config.YOUTUBE_REFRESH_TOKEN,
                    token_uri='https://oauth2.googleapis.com/token',
                    client_id=config.YOUTUBE_CLIENT_ID,
                    client_secret=config.YOUTUBE_CLIENT_SECRET,
                    scopes=self.SCOPES
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
                    creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
                    
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
                'client_secrets.json', self.SCOPES)
            
            # 리디렉션 URI 문제 해결을 위해 여러 방법 시도
            try:
                # 방법 1: 로컬 서버 사용 (포트 8080)
                creds = flow.run_local_server(port=8080, prompt='consent', open_browser=True)
            except Exception as e1:
                print(f"⚠️ 포트 8080 실패: {e1}")
                try:
                    # 방법 2: 랜덤 포트 사용
                    print("랜덤 포트로 재시도 중...")
                    creds = flow.run_local_server(port=0, prompt='consent', open_browser=True)
                except Exception as e2:
                    print(f"⚠️ 랜덤 포트 실패: {e2}")
                    # 방법 3: 수동 인증 코드 입력 방식
                    print("\n📋 수동 인증 코드 입력 방식으로 전환합니다...")
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    print(f"\n다음 URL을 브라우저에서 열어주세요:\n{auth_url}\n")
                    print("인증 후 표시되는 코드를 복사하여 아래에 붙여넣으세요:")
                    code = input("인증 코드: ").strip()
                    flow.fetch_token(code=code)
                    creds = flow.credentials
            
            # 토큰 저장
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            
            print("✅ 인증 완료! token.json 파일이 저장되었습니다.")
        
        self.credentials = creds
        self.youtube = build(
            self.API_SERVICE_NAME,
            self.API_VERSION,
            credentials=creds
        )
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        category_id: str = '22',  # People & Blogs
        privacy_status: str = 'public',
        thumbnail_path: str = None
    ):
        """
        영상 업로드
        
        Args:
            video_path: 업로드할 영상 파일 경로
            title: 영상 제목
            description: 영상 설명
            tags: 태그 리스트
            category_id: 카테고리 ID (기본값: 22 - People & Blogs)
            privacy_status: 공개 설정 ('public', 'private', 'unlisted')
        
        Returns:
            업로드된 영상의 ID
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")
        
        # YouTube Shorts는 세로형 영상이어야 함
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or config.DEFAULT_TAGS,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Shorts로 표시하기 위한 설정
        body['snippet']['defaultLanguage'] = 'ko'
        body['snippet']['defaultAudioLanguage'] = 'ko'
        
        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/*'
        )
        
        try:
            # 영상 업로드 요청
            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # 업로드 실행
            response = self._resumable_upload(insert_request)
            
            video_id = response['id']
            print(f"✅ 영상 업로드 완료! 영상 ID: {video_id}")
            print(f"🔗 URL: https://www.youtube.com/watch?v={video_id}")
            
            # 썸네일 업로드 (있는 경우)
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    print("\n🖼️ 썸네일 업로드 중...")
                    self.upload_thumbnail(video_id, thumbnail_path)
                    print("✅ 썸네일 업로드 완료!")
                except Exception as e:
                    print(f"⚠️ 썸네일 업로드 실패: {e}")
                    print("   영상은 정상적으로 업로드되었습니다.")
            
            return video_id
            
        except Exception as e:
            print(f"❌ 업로드 실패: {str(e)}")
            raise
    
    def _resumable_upload(self, insert_request):
        """재개 가능한 업로드 처리"""
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        return response
                    else:
                        raise Exception(f"업로드 실패: {response}")
            except Exception as e:
                if retry > 3:
                    raise
                error = e
                retry += 1
                print(f"재시도 중... ({retry}/3)")
        
        if error:
            raise error
        return response
    
    def upload_thumbnail(self, video_id: str, thumbnail_path: str):
        """썸네일 업로드"""
        if not os.path.exists(thumbnail_path):
            raise FileNotFoundError(f"썸네일 파일을 찾을 수 없습니다: {thumbnail_path}")
        
        # 썸네일 파일 업로드
        media = MediaFileUpload(
            thumbnail_path,
            mimetype='image/jpeg',
            resumable=True
        )
        
        # 썸네일 업로드 요청
        self.youtube.thumbnails().set(
            videoId=video_id,
            media_body=media
        ).execute()
    
    def get_video_stats(self, video_id: str):
        """영상 통계 정보 가져오기"""
        try:
            request = self.youtube.videos().list(
                part='statistics,snippet',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                video = response['items'][0]
                stats = video['statistics']
                snippet = video['snippet']
                
                return {
                    'title': snippet['title'],
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                    'published_at': snippet['publishedAt']
                }
            return None
        except Exception as e:
            print(f"통계 정보 가져오기 실패: {str(e)}")
            return None

