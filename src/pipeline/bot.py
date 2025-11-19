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

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.generators.video_generator import AIVideoGenerator, ContentType
from src.uploaders.youtube_uploader import YouTubeUploader
from src.uploaders.multi_platform_uploader import MultiPlatformUploader
from src.analytics.monetization import MonetizationTracker
from src.pipeline.database import VideoDatabase
from src.pipeline.sync_manager import SyncManager
import config


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
            video_path, script, generated_topic = self.video_generator.generate_video(
                topic=topic, 
                duration=None,
                performance_prompt=None,
                language=language
            )
            
            # 실제 사용된 주제
            actual_topic = generated_topic if generated_topic else topic
            
            # 제목 생성
            if actual_topic:
                title = actual_topic
            else:
                title = datetime.now().strftime('%Y년 %m월 %d일')
            
            # 썸네일 생성
            print("\n🖼️ 썸네일 생성 중...")
            thumbnail_path = self.video_generator.generate_thumbnail(
                video_path, 
                title,
                topic=actual_topic,
                script=script,
                language=language
            )
            if thumbnail_path:
                print("🎞️ 썸네일 이미지를 영상 첫 프레임에 삽입합니다...")
                self.video_generator.embed_thumbnail_frame(video_path, thumbnail_path)
            
            print(f"\n✅ 영상 생성 완료!")
            print(f"📁 파일 위치: {video_path}")
            print(f"🖼️ 썸네일 위치: {thumbnail_path}")
            print(f"🔍 확인 방법: open {video_path}")
            print(f"🔍 썸네일 확인: open {thumbnail_path}")
            
            return video_path
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_and_upload(self, topic: str = None, content_type: ContentType = None, force: bool = False, language: str = None):
        """
        영상 생성 및 업로드
        
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
            
            # 동기화 상태 확인
            self.sync_manager.print_sync_status()
            
            # 오늘 이미 업로드했는지 확인 (로컬 상태) - force 모드가 아닐 때만
            if not force and self.sync_manager.check_today_uploaded():
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
                        return None
                except EOFError:
                    # 비대화형 환경에서는 자동으로 진행
                    print("y (자동 진행)")
            
            # YouTube API로 오늘 업로드 확인 (실제 서버 상태) - force 모드가 아닐 때만
            if not force and not self.use_multi_platform:
                if hasattr(self.uploader, 'check_today_uploaded'):
                    if self.uploader.check_today_uploaded():
                        print(f"\n⚠️ YouTube API 확인 결과, 오늘 이미 업로드된 영상이 있습니다.")
                        print(f"   중복 업로드를 방지하기 위해 업로드를 건너뜁니다.")
                        print(f"   강제로 업로드하려면 force=True 옵션을 사용하세요.")
                        return None
            
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
            
            # 성과 기반 프롬프트 가져오기 (하루 1개 생성 전)
            performance_prompt = self._get_performance_based_prompt()
            if performance_prompt:
                print("📊 성과 기반 프롬프트 적용 중...")
                print(f"   {performance_prompt[:100]}...")
            
            # 1. AI로 영상 생성 (길이 자동 조정, 성과 기반 프롬프트 포함, 템플릿 사용)
            print("📹 1단계: AI 영상 생성 중...")
            video_path, script, generated_topic = self.video_generator.generate_video(
                topic=topic, 
                duration=None,
                performance_prompt=performance_prompt,
                content_type=content_type,
                language=language
            )
            
            # 실제 사용된 주제 (생성된 경우 generated_topic 사용)
            actual_topic = generated_topic if generated_topic else topic
            
            # 2. 제목 및 설명 생성
            if actual_topic:
                title = actual_topic
            else:
                title = datetime.now().strftime('%Y년 %m월 %d일')
            
            # 제목에 #Shorts 추가 (YouTube Shorts로 인식되도록)
            if '#Shorts' not in title and '#shorts' not in title:
                title = f"{title} #Shorts"
            
            # 3. 매력적인 썸네일 생성
            print("\n🖼️ 썸네일 생성 중...")
            thumbnail_path = self.video_generator.generate_thumbnail(
                video_path, 
                title, 
                topic=actual_topic,
                script=script,
                language=language
            )
            if thumbnail_path:
                print("🎞️ 썸네일 이미지를 영상 첫 프레임에 삽입합니다...")
                self.video_generator.embed_thumbnail_frame(video_path, thumbnail_path)
            
            # 썸네일 생성 확인
            if thumbnail_path:
                print(f"✅ 썸네일 생성 완료: {thumbnail_path}")
                if os.path.exists(thumbnail_path):
                    print(f"   파일 크기: {os.path.getsize(thumbnail_path)} bytes")
                else:
                    print(f"   ⚠️ 경고: 썸네일 파일이 생성되었지만 찾을 수 없습니다!")
            else:
                print("   ⚠️ 경고: 썸네일 생성 실패 (None 반환)")
            
            description = f"{config.DEFAULT_DESCRIPTION}\n\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "📺 영상 정보\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += f"📅 업로드 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}\n"
            if topic:
                description += f"📌 영상 주제: {topic}\n"
            description += f"⏱️ 영상 길이: 약 55초 (YouTube Shorts 최적화)\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "💡 이 영상에 대해\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "이 영상은 최신 AI 기술을 활용하여 자동으로 생성되었습니다.\n"
            description += "매일 새로운 주제로 유용한 정보와 실용적인 팁을 제공합니다.\n"
            description += "생활에 도움이 되는 다양한 콘텐츠를 지속적으로 업로드할 예정입니다.\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🙏 여러분의 참여를 기다립니다\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "👍 좋아요: 영상이 도움이 되셨다면 좋아요를 눌러주세요!\n"
            description += "🔔 구독: 매일 새로운 영상을 받아보시려면 구독해주세요!\n"
            description += "💬 댓글: 궁금한 점이나 원하시는 주제가 있으시면 댓글로 알려주세요!\n"
            description += "📤 공유: 친구들과 함께 보시면 더욱 좋습니다!\n\n"
            
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "🏷️ 태그\n"
            description += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            description += "#shorts #쇼츠 #ai #인공지능 #자동생성 #유용한정보 #팁 #라이프스타일 #일상 #정보 #꿀팁 #생활정보"
            
            # 4. 멀티 플랫폼 업로드 또는 YouTube 업로드
            print("\n📤 2단계: 플랫폼 업로드 중...")
            if self.use_multi_platform:
                # 멀티 플랫폼 업로드
                upload_results = self.uploader.upload_to_all(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=config.DEFAULT_TAGS,
                    thumbnail_path=thumbnail_path
                )
                # YouTube ID는 필수 (데이터베이스 저장용)
                video_id = upload_results.get('youtube')
            else:
                # YouTube만 업로드
                video_id = self.uploader.upload_video(
                    video_path=video_path,
                    title=title,
                    description=description,
                    tags=config.DEFAULT_TAGS,
                    privacy_status='public',
                    thumbnail_path=thumbnail_path
                )
                upload_results = {'youtube': video_id}
            
            # 5. 데이터베이스에 저장
            print("\n💾 3단계: 데이터베이스에 저장 중...")
            # 스크립트는 video_generator에서 가져올 수 없으므로 None으로 설정
            # 향후 video_generator에서 스크립트를 반환하도록 수정 가능
            self.database.add_video(
                video_id=video_id,
                title=title,
                topic=topic,
                prompt=performance_prompt if performance_prompt else None,
                script=None  # 향후 추가 가능
            )
            
            # 6. 동기화 상태 업데이트
            print("\n🔄 동기화 상태 업데이트 중...")
            self.sync_manager.record_upload(
                video_id=video_id,
                title=title,
                topic=topic
            )
            print("✅ 동기화 상태 업데이트 완료")
            
            # 멀티 플랫폼 업로드 결과 출력
            if self.use_multi_platform:
                print("\n📊 업로드 결과:")
                for platform, platform_id in upload_results.items():
                    if platform_id:
                        print(f"   ✅ {platform.capitalize()}: {platform_id}")
                    else:
                        print(f"   ⚠️ {platform.capitalize()}: 업로드 실패 또는 건너뜀")
            
            # 7. 수익화 추적에 추가
            print("\n📊 4단계: 수익화 추적에 추가 중...")
            self.monetization.add_video(
                video_id=video_id,
                title=title,
                upload_date=datetime.now().isoformat()
            )
            
            # 7. 통계 업데이트
            stats = self.uploader.get_video_stats(video_id)
            if stats:
                self.database.update_video_stats(
                    video_id=video_id,
                    views=stats.get('views', 0),
                    likes=stats.get('likes', 0),
                    comments=stats.get('comments', 0)
                )
                self.monetization.update_video_stats(video_id)
            
            print(f"\n✅ 완료! 영상 ID: {video_id}")
            print(f"🔗 https://www.youtube.com/watch?v={video_id}\n")
            
            # 리포트 출력
            self.monetization.print_report()
            
            return video_id
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
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
        
        # 데이터베이스 통계도 업데이트
        for video in self.monetization.data.get('videos', []):
            stats = self.uploader.get_video_stats(video['video_id'])
            if stats:
                self.database.update_video_stats(
                    video_id=video['video_id'],
                    views=stats.get('views', 0),
                    likes=stats.get('likes', 0),
                    comments=stats.get('comments', 0)
                )
        
        self.monetization.print_report()

