"""
YouTube Shorts 자동 업로드 봇 클래스
"""
import os
import schedule
import time
from datetime import datetime
import pytz
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.generators.video_generator import AIVideoGenerator
from src.generators.content_type import ContentType
from src.uploaders.youtube_uploader import YouTubeUploader
from src.uploaders.multi_platform_uploader import MultiPlatformUploader
from src.analytics.monetization import MonetizationTracker
from src.pipeline.database import VideoDatabase
from src.pipeline.sync_manager import SyncManager
from src.analytics.ab_testing import ABTestDatabase, VideoStyle
from src.pipeline.topic_database import TopicDatabase, TopicSource
from src.analytics.thumbnail_optimizer import ThumbnailOptimizer
from src.analytics.advanced_analytics import PerformancePredictor, AutoOptimizer, CompetitorAnalyzer, AudienceSegmentAnalyzer
from src.web.notifications import NotificationService
from src.generators.series_generator import SeriesGenerator, SeriesType
from src.generators.user_request_handler import UserRequestHandler
from src.analytics.comment_analyzer import CommentAnalyzer
import config
import json


class ShortsBot:
    """YouTube Shorts 자동 업로드 봇"""
    
    def __init__(self):
        self.video_generator = AIVideoGenerator()
        # YouTube만 사용 (기본값)
        # 멀티 플랫폼 업로드를 사용하려면 .env에서 ENABLE_TIKTOK_UPLOAD 또는 ENABLE_INSTAGRAM_UPLOAD를 true로 설정
        use_multi_platform = (config.ENABLE_TIKTOK_UPLOAD or config.ENABLE_INSTAGRAM_UPLOAD)
        if use_multi_platform:
            self.uploader = MultiPlatformUploader()
            self.use_multi_platform = True
            print("📱 멀티 플랫폼 업로드 모드 활성화")
        else:
            self.uploader = YouTubeUploader()
            self.use_multi_platform = False
        self.monetization = MonetizationTracker()
        self.database = VideoDatabase(db_path=config.DATABASE_PATH)
        self.sync_manager = SyncManager()
        self.timezone = pytz.timezone(config.UPLOAD_TIMEZONE)
        self.ab_test_db = ABTestDatabase()
        self.topic_database = TopicDatabase()
        self.thumbnail_optimizer = ThumbnailOptimizer()
        self.performance_predictor = PerformancePredictor()
        self.auto_optimizer = AutoOptimizer()
        self.competitor_analyzer = CompetitorAnalyzer()
        self.audience_segment_analyzer = AudienceSegmentAnalyzer()
        self.notification_service = NotificationService()
        self.series_generator = SeriesGenerator()
        self.user_request_handler = UserRequestHandler()
        self.comment_analyzer = CommentAnalyzer()
    
    def _get_performance_based_prompt(self) -> str:
        """
        성과가 좋은 주제/스타일을 기반으로 시스템 프롬프트 생성
        
        Returns:
            성과 기반 프롬프트 추가 문구
        """
        try:
            # 최근 30일간 성과 좋은 영상 조회
            top_videos = self.database.get_top_performing_videos(limit=3, days=30, min_views=50)
            top_topics = self.database.get_top_topics(limit=3, days=30)
            
            prompt_additions = []
            
            # 성과 좋은 주제 추가
            if top_topics:
                topics_text = ", ".join([t['topic'] for t in top_topics if t.get('topic')])
                if topics_text:
                    prompt_additions.append(
                        f"최근 성과가 좋았던 주제들: {topics_text}. "
                        f"이러한 주제의 스타일과 톤을 참고하되, 완전히 동일하지는 않게 새로운 관점을 제공하세요."
                    )
            
            # 성과 좋은 영상의 특징 추가
            if top_videos:
                avg_engagement = sum(v.get('engagement_rate', 0) for v in top_videos) / len(top_videos)
                if avg_engagement > 2.0:  # 참여율 2% 이상
                    prompt_additions.append(
                        f"최근 참여율이 높았던 영상들의 특징: "
                        f"명확하고 실용적인 정보 제공, 시청자의 호기심을 자극하는 구성, "
                        f"쉽게 따라할 수 있는 팁과 조언 포함."
                    )
            
            if prompt_additions:
                return "\n\n" + "\n".join(prompt_additions)
            else:
                return ""
        except Exception as e:
            print(f"⚠️ 성과 기반 프롬프트 생성 실패: {e}")
            return ""
    
    def create_video_only(self, topic: str = None):
        """영상 생성만 (업로드 없음)"""
        try:
            print(f"\n{'='*50}")
            print(f"📹 영상 생성 테스트 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}\n")
            
            # 언어 자동 감지 (기본값: 영어, 주제가 한글이면 한글로 설정)
            language = 'en'  # 기본값을 영어로 변경
            if topic:
                import re
                korean_chars = len(re.findall(r'[가-힣]', topic))
                total_chars = len(re.findall(r'[a-zA-Z가-힣]', topic))
                if total_chars > 0 and korean_chars / total_chars > 0.5:
                    language = 'ko'
                    print(f"🌐 언어 자동 감지: 한국어 (주제: {topic})")
                else:
                    print(f"🌐 언어 자동 감지: 영어 (주제: {topic})")
            
            # AI로 영상 생성 (매번 새로운 아이디어로)
            print("📹 영상 생성 중...")
            video_path, thumbnail_path, generated_topic, script = self.video_generator.generate_video(
                topic=topic, 
                duration=None,
                performance_prompt=None,
                language=language,
                target_audience="General Audience"  # 기본값
            )
            
            print(f"\n✅ 영상 생성 완료!")
            print(f"📁 파일 위치: {video_path}")
            if thumbnail_path:
                print(f"🖼️ 썸네일 위치: {thumbnail_path}")
            print(f"🔍 확인 방법: open {video_path}")
            
            return video_path
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_and_upload(self, topic: str = None, content_type: ContentType = None, force: bool = False, language: str = None):
        """
        영상 생성 및 업로드 (Refactored)
        
        Args:
            topic: 영상 주제 (None이면 자동 생성)
            content_type: 콘텐츠 타입 (None이면 자동 선택)
            force: True이면 중복 체크를 건너뛰고 강제 업로드
            language: 언어 코드 ('ko' 또는 'en', None이면 주제로 자동 감지)
        """
        try:
            content_type_name = content_type.value if content_type else "자동"
            print(f"\n{'='*50}")
            print(f"🚀 영상 생성 및 업로드 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📌 콘텐츠 타입: {content_type_name}")
            if force:
                print(f"⚠️ 강제 업로드 모드: 중복 체크를 건너뜁니다")
            print(f"{'='*50}\n")
            
            # 1. 업로드 제약 확인
            if not self._check_upload_constraints(force):
                return None
            
            # 2. 주제 및 언어 결정
            topic, language, request_id = self._determine_video_parameters(topic, language)
            
            # 3. 성과 기반 프롬프트 가져오기
            performance_prompt = self._get_performance_based_prompt()
            if performance_prompt:
                print("📊 성과 기반 프롬프트 적용 중...")
                print(f"   {performance_prompt[:100]}...")
            
            # 4. 영상 콘텐츠 생성
            video_assets = self._generate_video_content(topic, content_type, language, performance_prompt)
            
            # 5. 플랫폼 업로드
            upload_results = self._upload_to_platforms(video_assets)
            
            # 6. 데이터베이스 및 상태 업데이트
            self._update_databases(video_assets, upload_results, request_id, content_type, performance_prompt)
            
            video_id = upload_results.get('youtube')
            if video_id:
                print(f"\n✅ 완료! 영상 ID: {video_id}")
                print(f"🔗 https://www.youtube.com/watch?v={video_id}\n")
                
                # 7. 알림 전송
                self._send_notifications(video_assets, video_id)
            
            # 리포트 출력
            self.monetization.print_report()
            
            return video_id
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _check_upload_constraints(self, force: bool) -> bool:
        """
        업로드 제약 조건 확인 (동기화 상태, 일일 업로드 제한 등)
        
        Args:
            force: 강제 업로드 여부
            
        Returns:
            업로드 진행 가능 여부
        """
        # 동기화 상태 확인
        self.sync_manager.print_sync_status()
        
        if force:
            print(f"⚠️ 강제 업로드 모드: 중복 체크를 건너뜁니다")
            return True
            
        # 오늘 이미 업로드했는지 확인 (로컬 상태)
        if self.sync_manager.check_today_uploaded():
            today_info = self.sync_manager.get_today_upload_info()
            print(f"\n⚠️ 경고: 로컬 상태 파일에 따르면 오늘 이미 업로드했습니다.")
            print(f"   영상 ID: {today_info.get('video_id', 'N/A')}")
            print(f"   제목: {today_info.get('title', 'N/A')}")
            print(f"   컴퓨터: {today_info.get('computer_id', 'N/A')}")
            print(f"\n계속하시겠습니까? (y/n): ", end='')
            try:
                response = input().strip().lower()
                if response != 'y':
                    print("❌ 업로드를 취소했습니다.")
                    return False
            except EOFError:
                # 비대화형 환경에서는 자동으로 진행
                print("y (자동 진행)")
        
        # YouTube API로 오늘 업로드 확인 (실제 서버 상태)
        if not self.use_multi_platform:
            if hasattr(self.uploader, 'check_today_uploaded'):
                if self.uploader.check_today_uploaded():
                    print(f"\n⚠️ YouTube API 확인 결과, 오늘 이미 업로드된 영상이 있습니다.")
                    print(f"   중복 업로드를 방지하기 위해 업로드를 건너뜁니다.")
                    print(f"   강제로 업로드하려면 force=True 옵션을 사용하세요.")
                    return False
                    
        return True

    def _determine_video_parameters(self, topic: str, language: str) -> Tuple[str, str, Optional[str]]:
        """
        영상 주제 및 언어 결정
        
        Args:
            topic: 입력된 주제
            language: 입력된 언어
            
        Returns:
            (결정된 주제, 결정된 언어, 사용자 요청 ID)
        """
        request_id = None
        
        # 언어 자동 감지 (기본값: 영어, 주제가 한글이면 한글로 설정)
        if language is None and topic:
            # 주제에 한글이 많으면 한글로 감지, 그 외는 모두 영어
            import re
            korean_chars = len(re.findall(r'[가-힣]', topic))
            total_chars = len(re.findall(r'[a-zA-Z가-힣]', topic))
            if total_chars > 0 and korean_chars / total_chars > 0.5:
                language = 'ko'
                print(f"🌐 언어 자동 감지: 한국어 (주제: {topic})")
            else:
                language = 'en'
                print(f"🌐 언어 자동 감지: 영어 (주제: {topic})")
        elif language is None:
            language = 'en'  # 기본값을 영어로 변경
            print(f"🌐 언어 기본값: 영어")
        
        # 사용자 요청 주제 확인 (우선순위)
        if not topic:
            user_request = self.user_request_handler.get_next_request()
            if user_request:
                topic = user_request['topic']
                request_id = user_request['id']
                print(f"📝 사용자 요청 주제 사용: {topic} (요청 ID: {request_id})")
                # 요청을 진행 중으로 표시
                self.user_request_handler.mark_in_progress(request_id)
                
        return topic, language, request_id

    def _generate_video_content(self, topic: str, content_type: ContentType, language: str, performance_prompt: str) -> Dict[str, Any]:
        """
        영상 콘텐츠 생성 (영상, 썸네일, 메타데이터)
        
        Returns:
            영상 자산 딕셔너리 (video_path, thumbnail_path, title, description, tags, etc.)
        """
        # 1. AI로 영상 생성
        print("📹 1단계: AI 영상 생성 중...")
        result = self.video_generator.generate_video(
            topic=topic, 
            duration=None,
            performance_prompt=performance_prompt,
            content_type=content_type,
            language=language
        )
        
        # 반환값 처리
        if len(result) == 4:
            video_path, script, generated_topic, topic_source = result
        else:
            video_path, script, generated_topic = result
            topic_source = None
        
        if not video_path:
            raise Exception("영상 생성 실패")
            
        # 실제 사용된 주제
        actual_topic = generated_topic if generated_topic else topic
        
        # 주제 출처 저장
        self._last_topic_source = self._map_topic_source(topic_source)
        
        # 2. 제목 생성
        if actual_topic:
            title = actual_topic
        else:
            title = datetime.now().strftime('%Y년 %m월 %d일')
        
        # 제목에 #Shorts 추가
        if '#Shorts' not in title and '#shorts' not in title:
            title = f"{title} #Shorts"
        
        # 썸네일 임베딩 (이미 generate_video에서 생성됨)
        if thumbnail_path:
            print("\n🎞️ 썸네일 이미지를 영상 첫 프레임에 삽입합니다...")
            self.video_generator.embed_thumbnail_frame(video_path, thumbnail_path)
            print(f"✅ 썸네일 생성 완료: {thumbnail_path}")
        else:
            print("   ⚠️ 경고: 썸네일 생성 실패 (None 반환)")
            
        # 4. 설명 및 태그 생성
        description = self._generate_description(language, topic, actual_topic)
        
        return {
            'video_path': video_path,
            'thumbnail_path': thumbnail_path,
            'title': title,
            'description': description,
            'tags': config.DEFAULT_TAGS,
            'actual_topic': actual_topic,
            'script': script,
            'topic_source': topic_source
        }

    def _generate_description(self, language: str, original_topic: str, actual_topic: str) -> str:
        """설명란 텍스트 생성"""
        # 채널 정보 및 최근 영상 가져오기
        channel_info = None
        recent_videos = []
        
        try:
            if hasattr(self.uploader, 'get_channel_info'):
                channel_info = self.uploader.get_channel_info()
            if hasattr(self.uploader, 'get_recent_videos'):
                recent_videos = self.uploader.get_recent_videos(max_results=3)
        except Exception as e:
            print(f"⚠️ 채널 정보/최근 영상 가져오기 실패: {e}")

        if language == 'en':
            description = f"{config.DEFAULT_DESCRIPTION}\n\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "📺 Video Information\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += f"📅 Upload Date: {datetime.now().strftime('%B %d, %Y')}\n"
            if original_topic:
                description += f"📌 Topic: {original_topic}\n"
            description += f"⏱️ Duration: ~55 seconds (YouTube Shorts optimized)\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "💡 About This Video\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "This video was automatically generated using the latest AI technology.\n"
            description += "We provide useful information and practical tips on new topics every day.\n"
            description += "We will continue to upload diverse content that helps improve your daily life.\n\n"
            
            # 구독 유도 섹션
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🔔 SUBSCRIBE NOW - Don't Miss Daily Content!\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            if channel_info and channel_info.get('channel_url'):
                description += f"👉 Subscribe here: {channel_info['channel_url']}\n\n"
            description += "Why subscribe?\n"
            description += "✅ Daily new videos with practical tips\n"
            description += "✅ Finance, productivity, and lifestyle content\n"
            description += "✅ Short, actionable advice (under 1 minute)\n"
            description += "✅ AI-powered insights you can use today\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🙏 Your Engagement Matters\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "👍 LIKE: If this video helped you, please hit the like button!\n"
            description += "🔔 SUBSCRIBE: Get notified when we upload new videos daily!\n"
            description += "💬 COMMENT: Share your thoughts or suggest topics you'd like to see!\n"
            description += "📤 SHARE: Help others discover this content by sharing!\n\n"
            
            # 관련 영상 링크
            if recent_videos:
                description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                description += "📚 More Videos You Might Like\n"
                description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                for i, video in enumerate(recent_videos[:3], 1):
                    description += f"{i}. {video['title']}\n"
                    description += f"   👉 {video['url']}\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🏷️ Tags\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "#shorts #finance #productivity #lifestyle #tips #money #investing #selfimprovement #ai #automation"
        else:
            description = f"{config.DEFAULT_DESCRIPTION}\n\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "📺 영상 정보\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += f"📅 업로드 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}\n"
            if original_topic:
                description += f"📌 영상 주제: {original_topic}\n"
            description += f"⏱️ 영상 길이: 약 55초 (YouTube Shorts 최적화)\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "💡 이 영상에 대해\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "이 영상은 최신 AI 기술을 활용하여 자동으로 생성되었습니다.\n"
            description += "매일 새로운 주제로 유용한 정보와 실용적인 팁을 제공합니다.\n"
            description += "생활에 도움이 되는 다양한 콘텐츠를 지속적으로 업로드할 예정입니다.\n\n"
            
            # 구독 유도 섹션
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🔔 지금 구독하세요 - 매일 새로운 콘텐츠를 놓치지 마세요!\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            if channel_info and channel_info.get('channel_url'):
                description += f"👉 구독하기: {channel_info['channel_url']}\n\n"
            description += "구독하면 좋은 이유:\n"
            description += "✅ 매일 새로운 실용적인 팁 영상\n"
            description += "✅ 재태크, 생산성, 라이프스타일 콘텐츠\n"
            description += "✅ 짧고 실행 가능한 조언 (1분 이내)\n"
            description += "✅ 오늘 바로 써먹을 수 있는 AI 인사이트\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🙏 여러분의 참여를 기다립니다\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "👍 좋아요: 영상이 도움이 되셨다면 좋아요를 눌러주세요!\n"
            description += "🔔 구독: 매일 새로운 영상을 받아보시려면 구독해주세요!\n"
            description += "💬 댓글: 궁금한 점이나 원하시는 주제가 있으시면 댓글로 알려주세요!\n"
            description += "📤 공유: 친구들과 함께 보시면 더욱 좋습니다!\n\n"
            
            # 관련 영상 링크
            if recent_videos:
                description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                description += "📚 더 많은 영상 보기\n"
                description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                for i, video in enumerate(recent_videos[:3], 1):
                    description += f"{i}. {video['title']}\n"
                    description += f"   👉 {video['url']}\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🏷️ 태그\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "#shorts #쇼츠 #ai #인공지능 #자동생성 #유용한정보 #팁 #라이프스타일 #일상 #정보 #꿀팁 #생활정보"
            
        return description

    def _upload_to_platforms(self, video_assets: Dict[str, Any]) -> Dict[str, str]:
        """플랫폼에 영상 업로드"""
        print("\n📤 2단계: 플랫폼 업로드 중...")
        
        if self.use_multi_platform:
            # 멀티 플랫폼 업로드
            upload_results = self.uploader.upload_to_all(
                video_path=video_assets['video_path'],
                title=video_assets['title'],
                description=video_assets['description'],
                tags=video_assets['tags'],
                thumbnail_path=video_assets['thumbnail_path']
            )
        else:
            # YouTube만 업로드
            video_id = self.uploader.upload_video(
                video_path=video_assets['video_path'],
                title=video_assets['title'],
                description=video_assets['description'],
                tags=video_assets['tags'],
                privacy_status='public',
                thumbnail_path=video_assets['thumbnail_path']
            )
            upload_results = {'youtube': video_id}
            
        return upload_results

    def _save_upload_log(self, video_assets: Dict[str, Any], upload_results: Dict[str, str], 
                        content_type: ContentType, video_path: str = None):
        """업로드 기록을 파일로 저장 (다른 IDE/머신에서도 확인 가능)"""
        try:
            video_id = upload_results.get('youtube')
            if not video_id:
                return
            
            # data 폴더 확인 및 생성
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            
            # 업로드 로그 파일 경로
            log_file = data_dir / "upload_log.json"
            
            # 기존 로그 읽기
            upload_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        upload_logs = json.load(f)
                except:
                    upload_logs = []
            
            # 새 로그 항목 추가
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'video_id': video_id,
                'title': video_assets.get('title'),
                'topic': video_assets.get('actual_topic'),
                'content_type': content_type.value if content_type else 'auto',
                'video_path': video_path or video_assets.get('video_path'),
                'thumbnail_path': video_assets.get('thumbnail_path'),
                'upload_results': upload_results,
                'url': f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            }
            
            upload_logs.append(log_entry)
            
            # 최근 1000개만 유지 (파일 크기 관리)
            if len(upload_logs) > 1000:
                upload_logs = upload_logs[-1000:]
            
            # 로그 파일 저장
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(upload_logs, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 업로드 로그 저장 완료: {log_file}")
            
            # HISTORY.md에 기록 추가
            self._append_to_history(log_entry)
            
        except Exception as e:
            print(f"⚠️ 업로드 로그 저장 실패: {e}")
            import traceback
            traceback.print_exc()
    
    def _append_to_history(self, log_entry: Dict[str, Any]):
        """HISTORY.md에 업로드 기록 추가"""
        try:
            history_file = Path("HISTORY.md")
            if not history_file.exists():
                return
            
            # HISTORY.md 읽기
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 날짜 추출
            upload_date = datetime.fromisoformat(log_entry['timestamp']).strftime('%Y-%m-%d')
            
            # 기록 항목 생성
            history_entry = f"""
- **{upload_date} - 영상 업로드 완료**
  - **제목**: {log_entry.get('title', 'N/A')}
  - **주제**: {log_entry.get('topic', 'N/A')}
  - **콘텐츠 타입**: {log_entry.get('content_type', 'auto')}
  - **Video ID**: {log_entry.get('video_id', 'N/A')}
  - **URL**: {log_entry.get('url', 'N/A')}
  - **영상 파일**: {log_entry.get('video_path', 'N/A')}
  - **썸네일**: {log_entry.get('thumbnail_path', 'N/A')}
  - **업로드 시간**: {log_entry.get('timestamp', 'N/A')}
"""
            
            # "최근 업데이트" 섹션 찾기
            import re
            
            # "**최근 업데이트**" 패턴 찾기 (프로젝트 개요 섹션 내)
            if "**최근 업데이트**" in content:
                # 프로젝트 개요 섹션의 최근 업데이트 부분 뒤에 추가
                pattern = r'(\*\*최근 업데이트\*\*:.*?\n)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    insert_pos = match.end()
                    # 다음 섹션(##) 전까지 찾기
                    next_section = content.find('\n##', insert_pos)
                    if next_section > 0:
                        content = content[:next_section] + history_entry + content[next_section:]
                    else:
                        content = content[:insert_pos] + history_entry + content[insert_pos:]
                else:
                    # 프로젝트 개요 섹션 끝에 추가
                    pattern = r'(## 프로젝트 개요.*?\n)'
                    match = re.search(pattern, content, re.DOTALL)
                    if match:
                        insert_pos = match.end()
                        content = content[:insert_pos] + history_entry + content[insert_pos:]
                    else:
                        # 파일 시작 부분에 추가
                        content = "## 최근 업데이트" + history_entry + "\n\n" + content
            elif "## 최근 업데이트" in content:
                # "## 최근 업데이트" 섹션 뒤에 추가
                pattern = r'(## 최근 업데이트.*?\n)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    insert_pos = match.end()
                    content = content[:insert_pos] + history_entry + content[insert_pos:]
                else:
                    # 파일 시작 부분에 추가
                    content = "## 최근 업데이트" + history_entry + "\n\n" + content
            else:
                # 프로젝트 개요 섹션 뒤에 추가
                pattern = r'(## 프로젝트 개요.*?\n)'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    insert_pos = match.end()
                    content = content[:insert_pos] + history_entry + content[insert_pos:]
                else:
                    # 파일 시작 부분에 추가
                    content = "## 최근 업데이트" + history_entry + "\n\n" + content
            
            # HISTORY.md 저장
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ HISTORY.md에 기록 추가 완료")
            
        except Exception as e:
            print(f"⚠️ HISTORY.md 기록 추가 실패: {e}")
            import traceback
            traceback.print_exc()

    def _update_databases(self, video_assets: Dict[str, Any], upload_results: Dict[str, str], 
                         request_id: Optional[str], content_type: ContentType, performance_prompt: str):
        """데이터베이스 및 상태 업데이트"""
        print("\n💾 3단계: 데이터베이스에 저장 중...")
        
        video_id = upload_results.get('youtube')
        if not video_id:
            print("⚠️ YouTube Video ID가 없어 데이터베이스 업데이트 일부를 건너뜁니다.")
            return

        # 1. 메인 비디오 DB 저장
        self.database.add_video(
            video_id=video_id,
            title=video_assets['title'],
            topic=video_assets.get('actual_topic'),
            prompt=performance_prompt if performance_prompt else None,
            script=None  # 향후 추가 가능
        )
        
        # 2. 사용자 요청 완료 처리
        if request_id:
            self.user_request_handler.mark_completed(request_id, video_id)
            print(f"✅ 사용자 요청 완료 처리: 요청 ID {request_id} -> 영상 ID {video_id}")
            
        # 3. A/B 테스트 DB 저장
        try:
            style_info = {
                'background_music': getattr(config, 'USE_BACKGROUND_MUSIC', True),
                'subtitle_mode': getattr(config, 'SUBTITLE_MODE', 'full_sentence'),
                'content_type': content_type.value if content_type else 'auto'
            }
            
            style = VideoStyle.DEFAULT.value
            if style_info.get('background_music'):
                style = VideoStyle.MUSIC.value
            else:
                style = VideoStyle.NO_MUSIC.value
            
            self.ab_test_db.add_test(
                video_id=video_id,
                style=style,
                style_config=json.dumps(style_info),
                topic=video_assets.get('actual_topic'),
                content_type=content_type.value if content_type else 'auto'
            )
            print(f"✅ A/B 테스트 데이터베이스에 저장 완료: {style}")
        except Exception as e:
            print(f"⚠️ A/B 테스트 데이터베이스 저장 실패: {e}")
            
        # 4. 주제 DB 저장
        try:
            from src.pipeline.topic_database import TopicDatabase, TopicSource
            topic_db = TopicDatabase()
            
            source = TopicSource.MANUAL.value
            if hasattr(self, '_last_topic_source'):
                source = self._last_topic_source
            
            topic_id = topic_db.add_topic(
                topic=video_assets.get('actual_topic'),
                content_type=content_type.value if content_type else 'auto',
                source=source,
                season=self.video_generator._get_season() if hasattr(self.video_generator, '_get_season') else None
            )
            
            if topic_id:
                topic_db.link_topic_to_video(
                    topic=video_assets.get('actual_topic'),
                    video_id=video_id,
                    views=0, likes=0, comments=0
                )
                print(f"✅ 주제 데이터베이스에 저장 완료: {video_assets.get('actual_topic')[:50]}...")
        except Exception as e:
            print(f"⚠️ 주제 데이터베이스 저장 실패: {e}")
        
        # 5. 업로드 로그 파일 저장 (다른 IDE/머신에서도 확인 가능)
        self._save_upload_log(
            video_assets=video_assets,
            upload_results=upload_results,
            content_type=content_type,
            video_path=video_assets.get('video_path')
        )
            
        # 5. 동기화 상태 업데이트
        print("\n🔄 동기화 상태 업데이트 중...")
        self.sync_manager.record_upload(
            video_id=video_id,
            title=video_assets['title'],
            topic=video_assets.get('actual_topic')
        )
        print("✅ 동기화 상태 업데이트 완료")
        
        # 6. 수익화 추적 추가
        print("\n📊 4단계: 수익화 추적에 추가 중...")
        self.monetization.add_video(
            video_id=video_id,
            title=video_assets['title'],
            upload_date=datetime.now().isoformat()
        )

    def _send_notifications(self, video_assets: Dict[str, Any], video_id: str):
        """알림 전송"""
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            self.notification_service.notify_video_uploaded(
                video_id=video_id,
                title=video_assets['title'],
                video_url=video_url
            )
        except Exception as e:
            print(f"⚠️ 알림 전송 실패: {e}")
    
    def _map_topic_source(self, source: str) -> str:
        """
        주제 출처 문자열을 TopicSource enum 값으로 매핑
        
        Args:
            source: 주제 출처 문자열 ('seasonal', 'performance', 'exploration', 'ai_generated', 'ai_seasonal', 'youtube_trend', 'global_trend' 등)
        
        Returns:
            TopicSource enum 값
        """
        from src.pipeline.topic_database import TopicSource
        
        mapping = {
            'seasonal': TopicSource.SEASONAL.value,
            'ai_seasonal': TopicSource.SEASONAL_AI.value,
            'ai_generated': TopicSource.AI_GENERATED.value,
            'youtube_trend': TopicSource.TREND.value,
            'global_trend': TopicSource.TREND.value,
            'performance': TopicSource.PERFORMANCE.value,
            'exploration': TopicSource.MANUAL.value,  # 탐색은 수동으로 간주
        }
        
        return mapping.get(source, TopicSource.MANUAL.value)
    
    def create_and_upload_all_types(self):
        """모든 콘텐츠 타입에 대해 영상 생성 및 업로드 (6개)"""
        content_types = [
            ContentType.HOOK,
            ContentType.QUOTE,
            ContentType.STORY,
            ContentType.FACT,
            ContentType.SHORT_STORY,
            ContentType.AUTO
        ]
        
        print(f"\n{'='*60}")
        print(f"🎬 모든 콘텐츠 타입 영상 생성 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 총 {len(content_types)}개 타입 생성 예정")
        print(f"{'='*60}\n")
        
        results = []
        for i, content_type in enumerate(content_types, 1):
            try:
                print(f"\n{'─'*60}")
                print(f"📹 [{i}/{len(content_types)}] {content_type.value.upper()} 타입 영상 생성 중...")
                print(f"{'─'*60}\n")
                
                video_id = self.create_and_upload(topic=None, content_type=content_type)
                if video_id:
                    results.append({
                        'content_type': content_type.value,
                        'video_id': video_id,
                        'status': 'success'
                    })
                    print(f"✅ [{i}/{len(content_types)}] {content_type.value} 타입 완료: {video_id}")
                else:
                    results.append({
                        'content_type': content_type.value,
                        'video_id': None,
                        'status': 'failed'
                    })
                    print(f"❌ [{i}/{len(content_types)}] {content_type.value} 타입 실패")
                    
            except Exception as e:
                print(f"❌ [{i}/{len(content_types)}] {content_type.value} 타입 오류: {str(e)}")
                results.append({
                    'content_type': content_type.value,
                    'video_id': None,
                    'status': 'error',
                    'error': str(e)
                })
                import traceback
                traceback.print_exc()
        
        # 최종 결과 요약
        print(f"\n{'='*60}")
        print(f"📊 모든 타입 생성 완료 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = len(results) - success_count
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {failed_count}개")
        print(f"\n상세 결과:")
        for r in results:
            status_icon = "✅" if r['status'] == 'success' else "❌"
            print(f"  {status_icon} {r['content_type']}: {r.get('video_id', 'N/A')}")
        print(f"{'='*60}\n")
        
        return results
    
    def schedule_daily_upload(self):
        """하루 6개 자동 업로드 스케줄 설정 (모든 콘텐츠 타입)"""
        upload_time = config.UPLOAD_SCHEDULE_TIME
        
        print(f"⏰ 자동 업로드 스케줄 설정 완료")
        print(f"   업로드 시간: 매일 {upload_time} ({config.UPLOAD_TIMEZONE})")
        print(f"   목표: 하루 6개 (모든 콘텐츠 타입) → 3개월 후 수익화 → 월 $100~500\n")
        
        schedule.every().day.at(upload_time).do(self.create_and_upload_all_types)
    
    def run_scheduler(self):
        """스케줄러 실행"""
        print("🤖 YouTube Shorts 자동 업로드 봇 시작")
        print("   종료하려면 Ctrl+C를 누르세요\n")
        
        # 첫 업로드 즉시 실행 (테스트용)
        # self.create_and_upload()
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
    
    def update_all_stats(self):
        """모든 영상 통계 업데이트"""
        print("📊 모든 영상 통계 업데이트 중...")
        self.monetization.update_all_videos()
        
        # 주제 데이터베이스 초기화
        from src.pipeline.topic_database import TopicDatabase
        topic_db = TopicDatabase()
        
        # 데이터베이스 통계도 업데이트
        for video in self.monetization.data.get('videos', []):
            video_id = video['video_id']
            stats = self.uploader.get_video_stats(video_id)
            if stats:
                self.database.update_video_stats(
                    video_id=video_id,
                    views=stats.get('views', 0),
                    likes=stats.get('likes', 0),
                    comments=stats.get('comments', 0)
                )
                
                # 주제 데이터베이스 통계도 업데이트
                topic = video.get('title')  # 제목을 주제로 사용 (실제로는 topic 필드가 있으면 그것을 사용)
                # videos 테이블에서 topic 가져오기
                video_data = self.database.get_video_by_id(video_id)
                if video_data and video_data.get('topic'):
                    topic = video_data['topic']
                    try:
                        topic_db.link_topic_to_video(
                            topic=topic,
                            video_id=video_id,
                            views=stats.get('views', 0),
                            likes=stats.get('likes', 0),
                            comments=stats.get('comments', 0)
                        )
                    except Exception as e:
                        print(f"⚠️ 주제 데이터베이스 통계 업데이트 실패 ({video_id}): {e}")
        
        # 성과가 낮은 주제 자동 필터링
        print("\n🔽 성과가 낮은 주제 자동 필터링 중...")
        filtered_count = topic_db.filter_low_performing_topics(
            days=30,
            max_engagement_rate=0.5,
            min_use_count=1
        )
        
        # A/B 테스트 통계 업데이트
        print("\n📊 A/B 테스트 통계 업데이트 중...")
        for video in self.monetization.data.get('videos', []):
            video_id = video['video_id']
            stats = self.uploader.get_video_stats(video_id)
            if stats:
                try:
                    watch_time = stats.get('watch_time', 0)
                    self.ab_test_db.update_test_stats(
                        video_id=video_id,
                        views=stats.get('views', 0),
                        likes=stats.get('likes', 0),
                        comments=stats.get('comments', 0),
                        watch_time=watch_time
                    )
                except Exception as e:
                    print(f"⚠️ A/B 테스트 통계 업데이트 실패 ({video_id}): {e}")
        
        # 최적 스타일 분석 및 출력
        print("\n📈 최적 스타일 분석 중...")
        try:
            best_styles = self.ab_test_db.get_best_styles_by_engagement(
                days=30,
                min_tests=3
            )
            if best_styles:
                print("\n🏆 최고 성과 스타일 (참여율 기준):")
                for style, engagement_rate, avg_views in best_styles[:5]:
                    print(f"   {style}: 참여율 {engagement_rate:.2%}, 평균 조회수 {avg_views:.0f}")
        except Exception as e:
            print(f"⚠️ 최적 스타일 분석 실패: {e}")
        if filtered_count > 0:
            print(f"✅ {filtered_count}개 주제 필터링 완료")
        
        self.monetization.print_report()

