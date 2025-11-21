"""
TikTok 업로더 (Content Posting API 사용)
"""
import os
import requests
import config

class TikTokUploader:
    """TikTok Content Posting API를 사용하여 영상 업로드"""
    
    def __init__(self):
        self.access_token = config.TIKTOK_ACCESS_TOKEN
        self.base_url = "https://open.tiktokapis.com/v2"
        
        if not self.access_token:
            print("⚠️ TikTok 설정이 누락되었습니다. (ACCESS_TOKEN)")
            self.is_configured = False
        else:
            self.is_configured = True

    def upload_video(self, video_path: str, title: str = "") -> bool:
        """
        TikTok 업로드 프로세스 (Direct Post):
        1. 게시물 초기화 (Post Info)
        2. 비디오 업로드 (Source Info)
        """
        if not self.is_configured:
            print("❌ TikTok 업로더가 설정되지 않았습니다.")
            return False
            
        if not os.path.exists(video_path):
            print(f"❌ 영상 파일을 찾을 수 없습니다: {video_path}")
            return False

        # TikTok API도 로컬 파일 직접 업로드보다는 
        # PULL_FROM_URL 방식을 권장하거나, FILE_UPLOAD 방식 사용 시 
        # 별도의 복잡한 청크 업로드 로직이 필요할 수 있습니다.
        # 여기서는 가장 일반적인 'PULL_FROM_URL' 방식을 가정하고 구조를 잡습니다.
        # (FILE_UPLOAD 방식은 구현 복잡도가 높고 대용량 처리가 필요함)
        
        print("⚠️ TikTok API (Direct Post)는 호스팅된 비디오 URL 사용을 권장합니다.")
        print("   현재 로컬 파일 직접 업로드는 지원하지 않으므로,")
        print("   실제 사용 시에는 AWS S3나 호스팅 서버에 먼저 업로드해야 합니다.")
        
        # TODO: 실제 호스팅 로직 구현 필요
        print(f"❌ [미구현] 비디오 호스팅 URL 생성 필요: {video_path}")
        return False

    def upload_video_from_url(self, video_url: str, title: str = "") -> bool:
        """공개된 URL에서 비디오를 가져와 TikTok에 게시"""
        if not self.is_configured:
            return False

        print(f"🚀 TikTok 영상 업로드 시작: {video_url}")
        
        # 게시물 생성 요청
        try:
            url = f"{self.base_url}/post/publish/video/init/"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json; charset=UTF-8"
            }
            
            payload = {
                "post_info": {
                    "title": title,
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_comment": False,
                    "disable_stitch": False,
                    "video_cover_timestamp_ms": 1000
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": video_url
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            result = response.json()
            
            if response.status_code == 200 and result.get("data"):
                publish_id = result["data"].get("publish_id")
                print(f"✅ TikTok 게시 요청 성공! Publish ID: {publish_id}")
                return True
            else:
                error = result.get("error", {})
                print(f"❌ TikTok 게시 실패: {error.get('message')} (Code: {error.get('code')})")
                return False
                
        except Exception as e:
            print(f"❌ API 요청 오류: {e}")
            return False
