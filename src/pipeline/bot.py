"""
YouTube Shorts 자동 업로드 봇 클래스
"""

import schedule
import time
from datetime import datetime
import pytz  # type: ignore
from typing import Optional, Dict, Any, Union
import json

from src.generators.video_generator import AIVideoGenerator
from src.generators.content_type import ContentType
from src.uploaders.youtube_uploader import YouTubeUploader
from src.uploaders.multi_platform_uploader import MultiPlatformUploader
from src.analytics.monetization import MonetizationTracker
from src.pipeline.database import VideoDatabase
from src.pipeline.sync_manager import SyncManager
from src.analytics.ab_testing import ABTestDatabase
from src.pipeline.topic_database import TopicDatabase
from src.analytics.thumbnail_optimizer import ThumbnailOptimizer
from src.analytics.advanced_analytics import (
    PerformancePredictor,
    AutoOptimizer,
    CompetitorAnalyzer,
    AudienceSegmentAnalyzer,
)
from src.web.notifications import NotificationService
from src.generators.series_generator import SeriesGenerator
from src.generators.user_request_handler import UserRequestHandler
from src.analytics.comment_analyzer import CommentAnalyzer
from src.utils.logger import get_logger
from src.pipeline.video_pipeline import VideoPipeline
from src.core.config import settings

logger = get_logger(__name__)


class ShortsBot:
    """YouTube Shorts 자동 업로드 봇"""

    def __init__(self):
        self.video_generator = AIVideoGenerator()
        # YouTube만 사용 (기본값)
        # 멀티 플랫폼 업로드를 사용하려면 .env에서 ENABLE_TIKTOK_UPLOAD 또는 ENABLE_INSTAGRAM_UPLOAD를 true로 설정
        use_multi_platform = (
            settings.ENABLE_TIKTOK_UPLOAD or settings.ENABLE_INSTAGRAM_UPLOAD
        )

        # uploader 타입을 Union으로 선언
        self.uploader: Union[YouTubeUploader, MultiPlatformUploader]

        if use_multi_platform:
            self.uploader = MultiPlatformUploader()
            self.use_multi_platform = True
            logger.info("📱 멀티 플랫폼 업로드 모드 활성화")
        else:
            self.uploader = YouTubeUploader()
            self.use_multi_platform = False
        self.monetization = MonetizationTracker()
        self.database = VideoDatabase(db_path=settings.DATABASE_PATH)
        self.sync_manager = SyncManager()
        self.timezone = pytz.timezone(settings.UPLOAD_TIMEZONE)
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

        # Initialize VideoPipeline
        self.pipeline = VideoPipeline(
            video_generator=self.video_generator,
            uploader=self.uploader,
            database=self.database,
            sync_manager=self.sync_manager,
            user_request_handler=self.user_request_handler,
            notification_service=self.notification_service,
            monetization_tracker=self.monetization,
            use_multi_platform=self.use_multi_platform,
        )

    def create_video_only(self, topic: str = None):
        """영상 생성만 (업로드 없음)"""
        # This method could also be moved to VideoPipeline or refactored to use it
        # For now, keeping it here but reusing some logic if possible, or leaving as is to minimize risk
        # Since VideoPipeline._generate_content does similar things, we could expose it.
        # But create_video_only has specific logging and file saving logic.
        # Let's leave it as is for now, as the main goal was create_and_upload.
        try:
            logger.info("=" * 50)
            logger.info("📹 영상 생성 테스트 시작")
            logger.info("=" * 50)

            # 언어 자동 감지 (기본값: 영어, 주제가 한글이면 한글로 설정)
            language = "en"  # 기본값을 영어로 변경
            if topic:
                import re

                korean_chars = len(re.findall(r"[가-힣]", topic))
                total_chars = len(re.findall(r"[a-zA-Z가-힣]", topic))
                if total_chars > 0 and korean_chars / total_chars > 0.5:
                    language = "ko"
                    logger.info(f"🌐 언어 자동 감지: 한국어 (주제: {topic})")
                else:
                    logger.info(f"🌐 언어 자동 감지: 영어 (주제: {topic})")

            # AI로 영상 생성 (매번 새로운 아이디어로)
            logger.info("📹 영상 생성 중...")

            # 언어별 타겟 오디언스 설정
            from src.core.config import settings

            if language == "ko":
                target_audience = settings.TARGET_AUDIENCE_KO
            else:
                target_audience = settings.TARGET_AUDIENCE_EN

            result = self.video_generator.generate_video(
                topic=topic,
                duration=None,
                performance_prompt=None,
                language=language,
                target_audience=target_audience,
            )

            # 반환값 처리
            thumbnail_path = None
            if len(result) == 4:
                # (video_path, script, generated_topic, topic_source) 또는 (video_path, thumbnail_path, generated_topic, script)
                if isinstance(result[1], str) and result[1].endswith(
                    (".jpg", ".png", ".jpeg")
                ):
                    # 썸네일 경로인 경우
                    video_path, thumbnail_path, generated_topic, script = result
                    topic_source = None
                else:
                    # 스크립트인 경우
                    video_path, script, generated_topic, topic_source = result
            else:
                video_path, thumbnail_path, generated_topic, script = result
                # topic_source = None

            if not video_path:
                logger.error("❌ 영상 생성 실패")
                return None

            # 실제 사용된 주제
            actual_topic = generated_topic if generated_topic else topic

            # 제목 생성
            if actual_topic:
                title = actual_topic
            else:
                title = datetime.now().strftime("%Y년 %m월 %d일")

            # 제목에 #Shorts 추가
            if "#Shorts" not in title and "#shorts" not in title:
                title = f"{title} #Shorts"

            # 영상 메타데이터를 JSON 파일로 저장 (업로드 시 사용)
            import os

            video_basename = os.path.basename(video_path)
            video_name_without_ext = os.path.splitext(video_basename)[0]
            metadata_file = os.path.join(
                settings.VIDEO_OUTPUT_DIR, f"{video_name_without_ext}_metadata.json"
            )

            # description 생성 (업로드 시 필요)
            # Use MetadataManager from pipeline if possible, or just duplicate logic for now
            # To be clean, I should use self.pipeline.metadata_manager
            description = self.pipeline.metadata_manager.generate_description(
                language, topic, actual_topic
            )

            metadata = {
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
                "title": title,
                "topic": actual_topic,
                "description": description,  # description 추가
                "tags": settings.DEFAULT_TAGS,  # tags 추가
                "script": script,
                "language": language,
                "created_at": datetime.now().isoformat(),
            }

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            logger.info("✅ 영상 생성 완료!")
            logger.info(f"📁 파일 위치: {video_path}")
            if thumbnail_path:
                logger.info(f"🖼️ 썸네일 위치: {thumbnail_path}")
            logger.info(f"📝 제목: {title}")
            logger.info(f"📌 주제: {actual_topic}")
            logger.info(f"💾 메타데이터 저장: {metadata_file}")
            logger.info(f"🔍 확인 방법: open {video_path}")

            return video_path

        except Exception as e:
            logger.error(f"❌ 오류 발생: {str(e)}", exc_info=True)
            return None

    def create_and_upload(
        self,
        topic: str = None,
        content_type: ContentType = None,
        force: bool = False,
        language: str = None,
        auto_upload: bool = False,
    ):
        """
        영상 생성 및 업로드 (Delegated to VideoPipeline)
        """
        return self.pipeline.run(
            topic=topic,
            content_type=content_type,
            force=force,
            language=language,
            auto_upload=auto_upload,
        )

    def _load_video_metadata(self, video_path: str) -> Optional[Dict[str, Any]]:
        """
        영상 파일 경로에서 메타데이터 파일을 읽어옴
        """
        try:
            import os

            video_basename = os.path.basename(video_path)
            video_name_without_ext = os.path.splitext(video_basename)[0]
            metadata_file = os.path.join(
                settings.VIDEO_OUTPUT_DIR, f"{video_name_without_ext}_metadata.json"
            )

            if os.path.exists(metadata_file):
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    logger.info(f"✅ 메타데이터 파일 로드: {metadata_file}")
                    return metadata
            else:
                logger.warning(f"⚠️ 메타데이터 파일을 찾을 수 없습니다: {metadata_file}")
                return None
        except Exception as e:
            logger.error(f"⚠️ 메타데이터 파일 읽기 실패: {e}")
            return None

    def run_scheduler(self):
        """스케줄러 실행"""
        logger.info("⏰ 스케줄러가 시작되었습니다.")

        # 매일 아침 9시에 실행
        schedule.every().day.at("09:00").do(self.create_and_upload, auto_upload=True)

        # 매일 저녁 6시에 실행
        schedule.every().day.at("18:00").do(self.create_and_upload, auto_upload=True)

        while True:
            schedule.run_pending()
            time.sleep(60)

    def update_all_stats(self):
        """모든 영상 통계 업데이트"""
        logger.info("📊 모든 영상 통계 업데이트 시작...")

        # 1. 수익화 데이터 업데이트
        self.monetization.update_all_videos(self.uploader)

        # 2. 데이터베이스 및 A/B 테스트 통계 업데이트
        videos = self.database.get_all_videos()
        for video in videos:
            video_id = video.get("video_id")
            if video_id:
                stats = self.uploader.get_video_stats(video_id)
                if stats:
                    # 메인 DB 업데이트
                    self.database.update_video_stats(video_id, stats)

                    # A/B 테스트 DB 업데이트 (해당 영상이 테스트 중인 경우)
                    self.ab_test_db.update_test_stats(
                        video_id=video_id,
                        views=stats.get("views"),
                        likes=stats.get("likes"),
                        comments=stats.get("comments"),
                    )

        logger.info("✅ 모든 통계 업데이트 완료")


if __name__ == "__main__":
    bot = ShortsBot()

    # 커맨드라인 인자 처리
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Shorts Bot")
    parser.add_argument("--topic", type=str, help="영상 주제")
    parser.add_argument(
        "--type", type=str, help="콘텐츠 타입 (hook, quote, story, fact, etc.)"
    )
    parser.add_argument(
        "--force", action="store_true", help="강제 업로드 (중복 체크 무시)"
    )
    parser.add_argument(
        "--only-create", action="store_true", help="영상 생성만 하고 업로드하지 않음"
    )
    parser.add_argument("--scheduler", action="store_true", help="스케줄러 모드로 실행")
    parser.add_argument("--lang", type=str, help="언어 (ko, en)")
    parser.add_argument(
        "--auto", action="store_true", help="자동 업로드 (사용자 확인 생략)"
    )

    args = parser.parse_args()

    if args.scheduler:
        bot.run_scheduler()
    elif args.only_create:
        bot.create_video_only(topic=args.topic)
    else:
        content_type = None
        if args.type:
            try:
                content_type = ContentType(args.type)
            except ValueError:
                logger.warning(f"⚠️ 잘못된 콘텐츠 타입: {args.type}")

        bot.create_and_upload(
            topic=args.topic,
            content_type=content_type,
            force=args.force,
            language=args.lang,
            auto_upload=args.auto,
        )
