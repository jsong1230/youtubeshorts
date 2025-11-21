"""
YouTube Shorts 자동 업로드 봇 메인 실행 파일
하루 1개 업로드 → 3개월 후 수익화 → 월 $100~500 목표
"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """메인 함수"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'instagram-test':
        from src.uploaders.instagram_uploader import InstagramUploader

        print("🔄 Instagram Graph API 연결 테스트를 시작합니다...")
        uploader = InstagramUploader()
        success = uploader.test_connection(verbose=True)
        if success:
            print("✅ Instagram 연결 테스트가 완료되었습니다.")
            sys.exit(0)
        else:
            print("❌ Instagram 연결 테스트에 실패했습니다. 위 로그를 참고해 설정을 점검하세요.")
            sys.exit(1)

    from src.pipeline.bot import ShortsBot

    bot = ShortsBot()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'test' or command == 'generate':
            # 영상 생성만 (업로드 없음)
            topic = sys.argv[2] if len(sys.argv) > 2 else None
            bot.create_video_only(topic=topic)

        elif command == 'upload':
            # 즉시 업로드
            # --force 또는 -f 플래그 제외하고 주제 추출
            args = [arg for arg in sys.argv[2:] if arg not in ['--force', '-f']]
            topic = args[0] if args else None
            force = '--force' in sys.argv or '-f' in sys.argv
            bot.create_and_upload(topic=topic, force=force)

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

        elif command == 'sync-status':
            # 동기화 상태 확인
            bot.sync_manager.print_sync_status()

        elif command == 'social-upload':
            # 생성된 영상 소셜 미디어 업로드 (테스트용)
            # python main.py social-upload [video_path] [title]
            if len(sys.argv) < 4:
                print("사용법: python main.py social-upload [video_path] [title]")
                sys.exit(1)
            
            video_path = sys.argv[2]
            title = sys.argv[3]
            
            from src.uploaders.social_manager import SocialManager
            manager = SocialManager()
            results = manager.upload_all(video_path, title, description=title)
            print(f"📊 소셜 업로드 결과: {results}")

        elif command == 'analyze':
            # 성과 분석 리포트
            from src.analytics.analytics_manager import AnalyticsManager
            manager = AnalyticsManager()
            manager.generate_performance_report()

        elif command == 'quota-status':
            # API 할당량 상태 확인
            from src.utils.quota_manager import get_quota_manager
            quota_mgr = get_quota_manager()
            quota_mgr.print_usage_stats()

        else:
            print("사용법:")
            print("  python main.py test [주제]     - 영상 생성만 (업로드 없음)")
            print("  python main.py upload [주제] [--force]  - 즉시 영상 생성 및 업로드 (--force: 중복 체크 건너뛰기)")
            print("  python main.py social-upload [path] [title] - 소셜 미디어 업로드 테스트")
            print("  python main.py stats          - 모든 영상 통계 업데이트")
            print("  python main.py report         - 수익화 리포트 출력")
            print("  python main.py schedule       - 자동 업로드 스케줄러 시작")
            print("  python main.py sync-status    - 동기화 상태 확인")
            print(f"  python main.py instagram-test - Instagram Graph API 연결 테스트")
            print(f"  python main.py analyze        - YouTube Shorts 성과 분석 리포트 출력")
            print(f"  python main.py quota-status   - API 할당량 사용 현황 확인")
    else:
        # 기본: 즉시 업로드
        bot.create_and_upload()


if __name__ == '__main__':
    main()

