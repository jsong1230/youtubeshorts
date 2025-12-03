"""
YouTube Shorts 자동 업로드 모듈
"""
import os
import json
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeUploader:
    """YouTube API를 사용한 영상 업로드 클래스"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.readonly'  # 통계 정보 조회용
    ]
    API_SERVICE_NAME = 'youtube'
    API_VERSION = 'v3'
    
    def __init__(self):
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """YouTube API 인증"""
        from src.utils.youtube_auth import get_authenticated_service
        self.youtube = get_authenticated_service()
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        category_id: str = '22',  # People & Blogs
        privacy_status: str = 'public',
        thumbnail_path: str = None,
        schedule_delay_hours: float = None
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
            thumbnail_path: 썸네일 파일 경로
            schedule_delay_hours: 예약 업로드 지연 시간 (시간 단위, None이면 config에서 읽음, 0이면 즉시 업로드)
        
        Returns:
            업로드된 영상의 ID
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")
        
        # 예약 업로드 지연 시간 설정 (파라미터가 없으면 config에서 읽음)
        if schedule_delay_hours is None:
            schedule_delay_hours = settings.UPLOAD_DELAY_HOURS
        
        # 예약 업로드 시간 계산
        scheduled_start_time = None
        if schedule_delay_hours and schedule_delay_hours > 0:
            # 현재 시간에 지연 시간 추가
            scheduled_time = datetime.utcnow() + timedelta(hours=schedule_delay_hours)
            # YouTube API는 최소 15분 이후의 시간이어야 함
            min_scheduled_time = datetime.utcnow() + timedelta(minutes=15)
            if scheduled_time < min_scheduled_time:
                scheduled_time = min_scheduled_time
                logger.info(f"⚠️ 예약 시간이 최소 15분 요구사항보다 짧아서 15분 후로 조정되었습니다.")
            
            # ISO 8601 형식으로 변환 (UTC)
            scheduled_start_time = scheduled_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            logger.info(f"📅 예약 업로드 설정: {schedule_delay_hours}시간 후 ({scheduled_start_time})")
            
            # 예약 업로드는 private 또는 unlisted 상태여야 함
            if privacy_status == 'public':
                privacy_status = 'unlisted'
                logger.info(f"⚠️ 예약 업로드는 공개 상태로 설정할 수 없어 'unlisted'로 변경되었습니다.")
        
        # YouTube Shorts는 세로형 영상이어야 함
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or settings.DEFAULT_TAGS,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # 예약 업로드 시간 설정
        if scheduled_start_time:
            body['status']['scheduledStartTime'] = scheduled_start_time
        
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
            if scheduled_start_time:
                logger.info(f"✅ 영상 예약 업로드 완료! 영상 ID: {video_id}")
                logger.info(f"📅 예약 공개 시간: {scheduled_start_time} (UTC)")
                logger.info(f"🔗 URL: https://www.youtube.com/watch?v={video_id}")
            else:
                logger.info(f"✅ 영상 업로드 완료! 영상 ID: {video_id}")
                logger.info(f"🔗 URL: https://www.youtube.com/watch?v={video_id}")
            
            # 썸네일 업로드 (있는 경우)
            # 썸네일 업로드 (있는 경우)
            if thumbnail_path:
                logger.info(f"🖼️ 썸네일 경로 확인: {thumbnail_path}")
                if os.path.exists(thumbnail_path):
                    logger.info(f"   ✅ 썸네일 파일 존재 확인됨 (크기: {os.path.getsize(thumbnail_path)} bytes)")
                    try:
                        logger.info("   📤 썸네일 업로드 중...")
                        self.upload_thumbnail(video_id, thumbnail_path)
                        logger.info("   ✅ 썸네일 업로드 완료!")
                    except Exception as e:
                        logger.warning(f"   ⚠️ 썸네일 업로드 실패: {e}", exc_info=True)
                        logger.info("   영상은 정상적으로 업로드되었습니다.")
                else:
                    logger.warning(f"   ⚠️ 썸네일 파일을 찾을 수 없습니다: {thumbnail_path}")
                    logger.info("   영상은 정상적으로 업로드되었습니다.")
            else:
                logger.warning("⚠️ 썸네일 경로가 제공되지 않았습니다.")
            
            return video_id
            
        except Exception as e:
            logger.error(f"❌ 업로드 실패: {str(e)}", exc_info=True)
            raise
    
    def check_today_uploaded(self) -> bool:
        """
        오늘 업로드한 영상이 있는지 확인
        
        Returns:
            오늘 업로드한 영상이 있으면 True, 없으면 False
        """
        try:
            if not self.youtube:
                return False
            
            # 오늘 날짜
            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())
            today_start_iso = today_start.isoformat() + 'Z'
            
            # 채널의 최근 업로드 영상 조회
            request = self.youtube.search().list(
                part='snippet',
                forMine=True,
                type='video',
                maxResults=10,
                order='date'
            )
            
            response = request.execute()
            
            if 'items' in response:
                for item in response['items']:
                    published_at = item['snippet'].get('publishedAt', '')
                    if published_at:
                        # ISO 형식의 날짜를 파싱
                        published_date = date_parser.parse(published_at).date()
                        if published_date == today:
                            logger.info(f"✅ 오늘 이미 업로드된 영상 발견: {item['snippet']['title']}")
                            return True
            
            return False
        except Exception as e:
            logger.warning(f"⚠️ 오늘 업로드 확인 실패: {e}")
            return False
    
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
                retry += 1
                logger.info(f"재시도 중... ({retry}/3)")
        
        if error:
            raise error
        return response
    
    def upload_thumbnail(self, video_id: str, thumbnail_path: str):
        """썸네일 업로드"""
        if not os.path.exists(thumbnail_path):
            raise FileNotFoundError(f"썸네일 파일을 찾을 수 없습니다: {thumbnail_path}")
        
        # 절대 경로로 변환 (상대 경로 문제 방지)
        thumbnail_path = os.path.abspath(thumbnail_path)
        
        logger.debug(f"   📁 썸네일 절대 경로: {thumbnail_path}")
        logger.debug(f"   📏 파일 크기: {os.path.getsize(thumbnail_path)} bytes")
        
        # 썸네일 파일 업로드
        media = MediaFileUpload(
            thumbnail_path,
            mimetype='image/jpeg',
            resumable=True
        )
        
        # 썸네일 업로드 요청
        try:
            response = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()
            logger.debug(f"   ✅ 썸네일 업로드 API 응답: {response}")
        except Exception as e:
            logger.error(f"   ❌ 썸네일 업로드 API 오류: {e}")
            raise
    
    def update_video_description(self, video_id: str, description: str):
        """영상 설명(description) 업데이트"""
        try:
            # 현재 영상 정보 가져오기
            request = self.youtube.videos().list(
                part='snippet',
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                raise ValueError(f"영상을 찾을 수 없습니다: {video_id}")
            
            video = response['items'][0]
            snippet = video['snippet']
            
            # Description 업데이트
            snippet['description'] = description
            
            # 업데이트 요청
            update_request = self.youtube.videos().update(
                part='snippet',
                body={
                    'id': video_id,
                    'snippet': snippet
                }
            )
            update_response = update_request.execute()
            
            logger.info(f"✅ 영상 description 업데이트 완료: {video_id}")
            return update_response
        except Exception as e:
            logger.error(f"❌ description 업데이트 실패: {e}")
            raise
    
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
            logger.warning(f"통계 정보 가져오기 실패: {str(e)}")
            return None
    
    def get_channel_info(self):
        """채널 정보 가져오기 (채널 ID, 채널 URL 등)"""
        try:
            if not self.youtube:
                return None
            
            # 현재 인증된 사용자의 채널 정보 가져오기
            request = self.youtube.channels().list(
                part='snippet,contentDetails,statistics',
                mine=True
            )
            response = request.execute()
            
            if response.get('items') and len(response['items']) > 0:
                channel = response['items'][0]
                channel_id = channel['id']
                snippet = channel['snippet']
                custom_url = snippet.get('customUrl', '')
                
                # 채널 URL 생성
                if custom_url:
                    # custom_url에서 @ 기호 제거 (이미 @가 포함되어 있을 수 있음)
                    clean_custom_url = custom_url.lstrip('@')
                    channel_url = f"https://www.youtube.com/@{clean_custom_url}"
                else:
                    channel_url = f"https://www.youtube.com/channel/{channel_id}"
                
                return {
                    'channel_id': channel_id,
                    'channel_url': channel_url,
                    'channel_name': snippet.get('title', ''),
                    'subscriber_count': int(channel.get('statistics', {}).get('subscriberCount', 0))
                }
            return None
        except Exception as e:
            logger.warning(f"⚠️ 채널 정보 가져오기 실패: {e}")
            return None
    
    def get_recent_videos(self, max_results: int = 5):
        """최근 업로드된 영상 목록 가져오기"""
        try:
            if not self.youtube:
                return []
            
            request = self.youtube.search().list(
                part='snippet',
                forMine=True,
                type='video',
                maxResults=max_results,
                order='date'
            )
            response = request.execute()
            
            videos = []
            if 'items' in response:
                for item in response['items']:
                    video_id = item['id']['videoId']
                    title = item['snippet']['title']
                    videos.append({
                        'video_id': video_id,
                        'title': title,
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    })
            return videos
        except Exception as e:
            logger.warning(f"⚠️ 최근 영상 목록 가져오기 실패: {e}")
            return []

