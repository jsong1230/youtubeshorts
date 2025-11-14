"""
YouTube Shorts 자동 업로드 봇 메인 실행 파일
하루 1개 업로드 → 3개월 후 수익화 → 월 $100~500 목표
"""
import os
import schedule
import time
from datetime import datetime
import pytz
from ai_video_generator import AIVideoGenerator
from youtube_uploader import YouTubeUploader
from monetization import MonetizationTracker
import config


class ShortsBot:
    """YouTube Shorts 자동 업로드 봇"""
    
    def __init__(self):
        self.video_generator = AIVideoGenerator()
        self.uploader = YouTubeUploader()
        self.monetization = MonetizationTracker()
        self.timezone = pytz.timezone(config.UPLOAD_TIMEZONE)
    
    def create_video_only(self, topic: str = None):
        """영상 생성만 (업로드 없음)"""
        try:
            print(f"\n{'='*50}")
            print(f"📹 영상 생성 테스트 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}\n")
            
            # AI로 영상 생성 (길이 자동 조정)
            print("📹 영상 생성 중...")
            video_path = self.video_generator.generate_video(topic=topic, duration=None)  # None이면 자동 계산
            
            print(f"\n✅ 영상 생성 완료!")
            print(f"📁 파일 위치: {video_path}")
            print(f"🔍 확인 방법: open {video_path}")
            
            return video_path
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_and_upload(self, topic: str = None):
        """영상 생성 및 업로드"""
        try:
            print(f"\n{'='*50}")
            print(f"🚀 영상 생성 및 업로드 시작 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}\n")
            
            # 1. AI로 영상 생성 (길이 자동 조정)
            print("📹 1단계: AI 영상 생성 중...")
            video_path = self.video_generator.generate_video(topic=topic, duration=None)  # None이면 자동 계산
            
            # 2. 제목 및 설명 생성
            if topic:
                title = topic  # 주제만 사용
            else:
                title = datetime.now().strftime('%Y년 %m월 %d일')
            
            description = f"{config.DEFAULT_DESCRIPTION}\n\n"
            description += f"📅 업로드 날짜: {datetime.now().strftime('%Y-%m-%d')}\n"
            description += f"#shorts #ai #자동생성"
            
            # 3. YouTube에 업로드
            print("\n📤 2단계: YouTube 업로드 중...")
            video_id = self.uploader.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=config.DEFAULT_TAGS,
                privacy_status='public'
            )
            
            # 4. 수익화 추적에 추가
            print("\n📊 3단계: 수익화 추적에 추가 중...")
            self.monetization.add_video(
                video_id=video_id,
                title=title,
                upload_date=datetime.now().isoformat()
            )
            
            # 5. 통계 업데이트
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
    
    def schedule_daily_upload(self):
        """하루 1개 자동 업로드 스케줄 설정"""
        upload_time = config.UPLOAD_SCHEDULE_TIME
        
        print(f"⏰ 자동 업로드 스케줄 설정 완료")
        print(f"   업로드 시간: 매일 {upload_time} ({config.UPLOAD_TIMEZONE})")
        print(f"   목표: 하루 1개 → 3개월 후 수익화 → 월 $100~500\n")
        
        schedule.every().day.at(upload_time).do(self.create_and_upload)
    
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
        self.monetization.print_report()


def main():
    """메인 함수"""
    bot = ShortsBot()
    
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'test' or command == 'generate':
            # 영상 생성만 (업로드 없음)
            topic = sys.argv[2] if len(sys.argv) > 2 else None
            bot.create_video_only(topic=topic)
        
        elif command == 'upload':
            # 즉시 업로드
            topic = sys.argv[2] if len(sys.argv) > 2 else None
            bot.create_and_upload(topic=topic)
        
        elif command == 'stats':
            # 통계 업데이트 및 리포트
            bot.update_all_stats()
        
        elif command == 'report':
            # 리포트만 출력
            bot.monetization.print_report()
        
        elif command == 'schedule':
            # 스케줄러 시작
            bot.schedule_daily_upload()
            bot.run_scheduler()
        
        else:
            print("사용법:")
            print("  python main.py test [주제]     - 영상 생성만 (업로드 없음)")
            print("  python main.py upload [주제]  - 즉시 영상 생성 및 업로드")
            print("  python main.py stats          - 모든 영상 통계 업데이트")
            print("  python main.py report         - 수익화 리포트 출력")
            print("  python main.py schedule       - 자동 업로드 스케줄러 시작")
    else:
        # 기본: 즉시 업로드
        bot.create_and_upload()


if __name__ == '__main__':
    main()

