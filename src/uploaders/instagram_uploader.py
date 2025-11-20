"""
Instagram Reels 자동 업로드 모듈
"""
import os
import requests
import json
import config


class InstagramUploader:
    """Instagram Graph API를 사용한 Reels 업로드 클래스"""
    
    def __init__(self):
        self.app_id = config.INSTAGRAM_APP_ID
        self.app_secret = config.INSTAGRAM_APP_SECRET
        self.access_token = config.INSTAGRAM_ACCESS_TOKEN
        self.instagram_account_id = config.INSTAGRAM_ACCOUNT_ID
        self.authenticated = False
        
        if self.app_id and self.app_secret and self.access_token:
            self._authenticate()
    
    def _authenticate(self):
        """Instagram Graph API 인증"""
        if not all([self.app_id, self.app_secret, self.access_token]):
            print("⚠️ Instagram API 키가 설정되지 않았습니다.")
            print("   Facebook for Developers에서 앱을 만들고 API 키를 발급받아 .env 파일에 설정하세요.")
            return False
        
        api_version = "v19.0"
        
        # 방법 1: Facebook 페이지를 통한 Instagram 계정 접근
        print(f"🔍 Instagram Graph API 연결 테스트 중...")
        
        try:
            # 먼저 Facebook 페이지 목록 조회
            pages_url = f"https://graph.facebook.com/{api_version}/me/accounts"
            pages_params = {
                "fields": "id,name,access_token,instagram_business_account{id,username,name,account_type}",
                "access_token": self.access_token
            }
            
            pages_response = requests.get(pages_url, params=pages_params, timeout=10)
            
            if pages_response.status_code == 200:
                pages_data = pages_response.json()
                pages = pages_data.get('data', [])
                
                if pages:
                    print(f"   ✅ Facebook 페이지 발견: {len(pages)}개")
                    
                    # 각 페이지의 Instagram 계정 확인
                    for page in pages:
                        page_name = page.get('name', 'N/A')
                        instagram_account = page.get('instagram_business_account')
                        
                        if instagram_account:
                            instagram_id = instagram_account.get('id')
                            instagram_username = instagram_account.get('username')
                            instagram_name = instagram_account.get('name')
                            account_type = instagram_account.get('account_type')
                            
                            # 설정된 Account ID와 일치하는지 확인
                            if self.instagram_account_id and instagram_id == self.instagram_account_id:
                                print(f"   ✅ Instagram 계정 확인됨!")
                                print(f"      페이지: {page_name}")
                                print(f"      사용자명: @{instagram_username}")
                                print(f"      이름: {instagram_name}")
                                print(f"      계정 타입: {account_type}")
                                
                                # 페이지 Access Token으로 다시 확인
                                page_token = page.get('access_token')
                                if page_token:
                                    instagram_url = f"https://graph.facebook.com/{api_version}/{instagram_id}"
                                    instagram_params = {
                                        "fields": "id,username,name",
                                        "access_token": page_token
                                    }
                                    
                                    instagram_response = requests.get(instagram_url, params=instagram_params, timeout=10)
                                    if instagram_response.status_code == 200:
                                        print(f"✅ Instagram 연결 성공! (페이지 토큰 사용)")
                                        self.authenticated = True
                                        # 페이지 토큰을 사용하도록 업데이트
                                        self.access_token = page_token
                                        return True
                            
                            # Account ID가 설정되지 않았거나 일치하지 않으면 첫 번째 Instagram 계정 사용
                            elif not self.instagram_account_id:
                                print(f"   ✅ Instagram 계정 발견 (Account ID 미설정 시 첫 번째 계정 사용)")
                                print(f"      페이지: {page_name}")
                                print(f"      사용자명: @{instagram_username}")
                                print(f"      ID: {instagram_id}")
                                
                                # 페이지 Access Token으로 확인
                                page_token = page.get('access_token')
                                if page_token:
                                    instagram_url = f"https://graph.facebook.com/{api_version}/{instagram_id}"
                                    instagram_params = {
                                        "fields": "id,username,name",
                                        "access_token": page_token
                                    }
                                    
                                    instagram_response = requests.get(instagram_url, params=instagram_params, timeout=10)
                                    if instagram_response.status_code == 200:
                                        print(f"✅ Instagram 연결 성공!")
                                        self.authenticated = True
                                        self.instagram_account_id = instagram_id
                                        self.access_token = page_token
                                        return True
                                break
                    
                    # 페이지는 있지만 Instagram 계정이 연결되지 않은 경우
                    if not self.authenticated:
                        print(f"   ⚠️  Facebook 페이지는 있지만 Instagram 계정이 연결되지 않았습니다.")
                        print(f"   Instagram 계정을 Facebook 페이지에 연결하세요.")
                else:
                    print(f"   ⚠️  Facebook 페이지를 찾을 수 없습니다.")
            
            # 방법 2: 직접 Account ID로 접근 시도 (설정된 경우)
            if self.instagram_account_id and not self.authenticated:
                print(f"   🔍 직접 Account ID로 접근 시도...")
                url = f"https://graph.facebook.com/{api_version}/{self.instagram_account_id}"
                # account_type 필드는 IGUser 타입에서 사용할 수 없으므로 제거
                params = {
                    "fields": "id,username,name",
                    "access_token": self.access_token
                }
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    username = data.get("username", "N/A")
                    name = data.get("name", "N/A")
                    
                    print(f"✅ Instagram 연결 성공! (직접 접근)")
                    print(f"   ID: {data.get('id', 'N/A')}")
                    print(f"   사용자명: @{username}")
                    if name != "N/A":
                        print(f"   이름: {name}")
                    self.authenticated = True
                    return True
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "알 수 없는 오류")
                    error_code = error_data.get("error", {}).get("code", response.status_code)
                    
                    print(f"   ❌ 직접 접근 실패 (코드: {error_code})")
                    print(f"   오류 메시지: {error_message}")
            
            # 모든 방법 실패
            if not self.authenticated:
                print(f"❌ Instagram 연결 실패")
                print(f"   💡 해결 방법:")
                print(f"      1. Facebook 페이지가 생성되어 있는지 확인")
                print(f"      2. Instagram 계정이 Facebook 페이지에 연결되어 있는지 확인")
                print(f"      3. Access Token에 'pages_show_list' 권한이 있는지 확인")
                print(f"      4. Facebook for Developers에서 Instagram Graph API 제품이 추가되어 있는지 확인")
                
            self.authenticated = False
            return False
                
        except requests.exceptions.Timeout:
            print("❌ Instagram 연결 실패: 요청 시간 초과")
            self.authenticated = False
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Instagram 연결 실패: 네트워크 오류 - {e}")
            self.authenticated = False
            return False
        except Exception as e:
            print(f"❌ Instagram 인증 실패: {e}")
            import traceback
            traceback.print_exc()
            self.authenticated = False
            return False
    
    def upload_reel(
        self,
        video_path: str,
        caption: str,
        thumbnail_url: str = None,
        share_to_feed: bool = True
    ):
        """
        Instagram Reels에 영상 업로드
        
        Args:
            video_path: 업로드할 영상 파일 경로
            caption: 영상 캡션 (해시태그 포함 가능)
            thumbnail_url: 썸네일 URL (선택사항)
            share_to_feed: 피드에도 공유할지 여부
        
        Returns:
            업로드된 Reels의 ID 또는 None
        """
        if not self.authenticated:
            print("⚠️ Instagram 인증이 필요합니다. 업로드를 건너뜁니다.")
            return None
        
        if not os.path.exists(video_path):
            print(f"⚠️ 영상 파일을 찾을 수 없습니다: {video_path}")
            return None
        
        try:
            api_version = "v19.0"
            
            print(f"📤 Instagram Reels 업로드 시작: {os.path.basename(video_path)}")
            
            # 영상 파일 크기 확인
            video_size = os.path.getsize(video_path)
            print(f"   영상 파일 크기: {video_size / (1024*1024):.2f} MB")
            
            # 1단계: Facebook Graph API를 통해 영상을 임시로 업로드하여 공개 URL 획득
            print(f"   1단계: Facebook에 영상 업로드 중 (임시 URL 획득용)...")
            
            # 먼저 Facebook 페이지 목록 조회
            pages_url = f"https://graph.facebook.com/{api_version}/me/accounts"
            pages_params = {
                "fields": "id,access_token",
                "access_token": self.access_token
            }
            
            pages_response = requests.get(pages_url, params=pages_params, timeout=10)
            page_token = None
            page_id = None
            
            if pages_response.status_code == 200:
                pages_data = pages_response.json()
                pages = pages_data.get('data', [])
                if pages:
                    page = pages[0]
                    page_id = page.get('id')
                    page_token = page.get('access_token')
                    print(f"   Facebook 페이지 발견: {page_id}")
            
            # Facebook 페이지가 있으면 페이지에 업로드, 없으면 /me/videos 시도
            if page_token and page_id:
                fb_upload_url = f"https://graph.facebook.com/{api_version}/{page_id}/videos"
                upload_token = page_token
            else:
                fb_upload_url = f"https://graph.facebook.com/{api_version}/me/videos"
                upload_token = self.access_token
                print(f"   Facebook 페이지가 없어 사용자 계정에 업로드 시도...")
            
            with open(video_path, 'rb') as video_file:
                files = {
                    'source': (os.path.basename(video_path), video_file, 'video/mp4')
                }
                fb_data = {
                    "title": os.path.basename(video_path),
                    "description": "Temporary upload for Instagram Reels",
                    "access_token": upload_token
                }
                
                fb_response = requests.post(fb_upload_url, data=fb_data, files=files, timeout=300)
            
            if fb_response.status_code != 200:
                try:
                    error = fb_response.json().get('error', {})
                    error_code = error.get('code')
                    error_msg = error.get('message', 'N/A')
                    print(f"   ❌ Facebook 업로드 실패 (코드: {error_code})")
                    print(f"   오류 메시지: {error_msg}")
                    
                    # Facebook 업로드 실패 시 직접 파일 업로드 시도
                    print(f"\n   🔄 Instagram Graph API에 직접 파일 업로드 시도...")
                    container_url = f"https://graph.facebook.com/{api_version}/{self.instagram_account_id}/media"
                    
                    with open(video_path, 'rb') as video_file:
                        files = {
                            'video_file': (os.path.basename(video_path), video_file, 'video/mp4')
                        }
                        data = {
                            "media_type": "REELS",
                            "caption": caption,
                            "access_token": self.access_token
                        }
                        container_response = requests.post(container_url, data=data, files=files, timeout=300)
                except:
                    print(f"   ❌ Facebook 업로드 실패")
                    print(f"   응답: {fb_response.text[:200]}")
                    return None
            else:
                # Facebook 업로드 성공 - 영상 ID 획득
                fb_data = fb_response.json()
                video_id = fb_data.get('id')
                
                if not video_id:
                    print(f"   ❌ Facebook 영상 ID를 받지 못했습니다.")
                    return None
                
                print(f"   ✅ Facebook 업로드 성공: {video_id}")
                
                # 영상 정보 조회하여 공개 URL 획득
                video_info_url = f"https://graph.facebook.com/{api_version}/{video_id}"
                video_info_params = {
                    "fields": "source,permalink_url",
                    "access_token": self.access_token
                }
                
                video_info_response = requests.get(video_info_url, params=video_info_params, timeout=30)
                if video_info_response.status_code == 200:
                    video_info = video_info_response.json()
                    # source URL 또는 permalink_url 사용
                    video_url = video_info.get('source') or video_info.get('permalink_url')
                    if not video_url:
                        # 기본 URL 형식 사용
                        video_url = f"https://graph.facebook.com/{api_version}/{video_id}/video"
                else:
                    # 기본 URL 형식 사용
                    video_url = f"https://graph.facebook.com/{api_version}/{video_id}/video"
                
                print(f"   영상 URL: {video_url}")
                
                # 2단계: Instagram Reels 컨테이너 생성 (video_url 사용)
                print(f"   2단계: Instagram Reels 컨테이너 생성 중...")
                container_url = f"https://graph.facebook.com/{api_version}/{self.instagram_account_id}/media"
                container_params = {
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption,
                    "access_token": self.access_token
                }
                
                container_response = requests.post(container_url, params=container_params, timeout=60)
            
            if container_response.status_code != 200:
                try:
                    error = container_response.json().get('error', {})
                    error_code = error.get('code')
                    error_msg = error.get('message', 'N/A')
                    print(f"   ❌ 컨테이너 생성 실패 (코드: {error_code})")
                    print(f"   오류 메시지: {error_msg}")
                    
                    # video_url이 필요한 경우 안내
                    if error_code == 100 and 'video_url' in error_msg.lower():
                        print(f"\n   💡 Instagram Graph API는 공개 URL이 필요합니다.")
                        print(f"   로컬 파일을 직접 업로드하려면 다른 방법이 필요합니다.")
                        print(f"   또는 영상을 공개 URL에 업로드한 후 그 URL을 사용하세요.")
                except:
                    print(f"   ❌ 컨테이너 생성 실패")
                    print(f"   응답: {container_response.text[:200]}")
                return None
            
            container_data = container_response.json()
            creation_id = container_data.get('id')
            
            if not creation_id:
                print(f"   ❌ 컨테이너 ID를 받지 못했습니다.")
                print(f"   응답: {container_data}")
                return None
            
            print(f"   ✅ 컨테이너 생성 성공: {creation_id}")
            
            # 2단계: 미디어 게시
            print(f"   2단계: Reels 게시 중...")
            publish_url = f"https://graph.facebook.com/{api_version}/{self.instagram_account_id}/media_publish"
            publish_params = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            publish_response = requests.post(publish_url, params=publish_params, timeout=60)
            
            if publish_response.status_code != 200:
                error = publish_response.json().get('error', {})
                error_code = error.get('code')
                error_msg = error.get('message', 'N/A')
                print(f"   ❌ Reels 게시 실패 (코드: {error_code})")
                print(f"   오류 메시지: {error_msg}")
                return None
            
            publish_data = publish_response.json()
            reel_id = publish_data.get('id')
            
            if reel_id:
                print(f"   ✅ Reels 게시 성공: {reel_id}")
                print(f"✅ Instagram 업로드 완료!")
                return reel_id
            else:
                print(f"   ⚠️  Reels ID를 받지 못했습니다.")
                print(f"   응답: {publish_data}")
                return None
            
        except FileNotFoundError:
            print(f"⚠️ 영상 파일을 찾을 수 없습니다: {video_path}")
            return None
        except requests.exceptions.Timeout:
            print(f"⚠️ Instagram 업로드 실패: 요청 시간 초과")
            return None
        except Exception as e:
            print(f"⚠️ Instagram 업로드 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def is_available(self) -> bool:
        """Instagram 업로더 사용 가능 여부"""
        return self.authenticated

