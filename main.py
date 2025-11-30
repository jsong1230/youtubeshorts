"""
YouTube Shorts 자동 업로드 봇 메인 실행 파일
하루 1개 업로드 → 3개월 후 수익화 → 월 $100~500 목표
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """메인 함수"""
    import sys
    import config

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
            force = '--force' in sys.argv or '-f' in sys.argv
            
            # 첫 번째 인자가 파일 경로인지 확인
            if args and (args[0].endswith('.mp4') or os.path.exists(args[0])):
                # 파일 경로로 업로드 (메타데이터에서 제목 읽기)
                video_path = args[0]
                metadata = bot._load_video_metadata(video_path)
                if metadata:
                    # 메타데이터에서 정보 가져오기
                    topic = metadata.get('topic')
                    title = metadata.get('title')
                    thumbnail_path = metadata.get('thumbnail_path')
                    description = bot._generate_description(metadata.get('language', 'en'), topic, topic)
                    
                    # 영상 자산 딕셔너리 생성
                    video_assets = {
                        'video_path': video_path,
                        'thumbnail_path': thumbnail_path,
                        'title': title,
                        'description': description,
                        'tags': config.DEFAULT_TAGS,
                        'actual_topic': topic
                    }
                    
                    # 업로드
                    upload_results = bot._upload_to_platforms(video_assets)
                    video_id = upload_results.get('youtube')
                    if video_id:
                        bot._update_databases(video_assets, upload_results, None, None, None)
                        print(f"\n✅ 업로드 완료! 영상 ID: {video_id}")
                        print(f"🔗 https://www.youtube.com/watch?v={video_id}\n")
                        
                        # 업로드 성공 후 원본 파일 삭제
                        try:
                            # 영상 파일 삭제
                            if os.path.exists(video_path):
                                os.remove(video_path)
                                print(f"🗑️  원본 영상 파일 삭제: {video_path}")
                            
                            # 메타데이터 JSON 파일 삭제
                            metadata_path = video_path.replace('.mp4', '_metadata.json')
                            if os.path.exists(metadata_path):
                                os.remove(metadata_path)
                                print(f"🗑️  메타데이터 파일 삭제: {metadata_path}")
                        except Exception as e:
                            print(f"⚠️  파일 삭제 중 오류 발생: {e}")
                else:
                    print(f"❌ 메타데이터 파일을 찾을 수 없습니다. 영상을 다시 생성하거나 주제를 직접 입력하세요.")
            else:
                # 주제로 새로 생성 및 업로드
                topic = args[0] if args else None
                # upload 명령어는 자동 업로드 (사용자가 명시적으로 업로드를 요청)
                bot.create_and_upload(topic=topic, force=force, auto_upload=True)

        elif command == 'stats':
            # 통계 업데이트 및 리포트
            bot.update_all_stats()

        elif command == 'report':
            # 리포트만 출력
            bot.monetization.print_report()

        elif command == 'schedule':
            # 스케줄러 시작 (자동 업로드 모드)
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

        elif command == 'batch':
            # 여러 영상 순차 생성 (2개 이상만 허용)
            # ⚠️ 현재 디버깅 중: 문제가 있을 수 있음
            print("⚠️  배치 기능은 현재 디버깅 중입니다.")
            print("⚠️  문제가 발생할 수 있으니, 단일 영상 생성은 'python main.py test'를 사용하세요.")
            print()
            
            if len(sys.argv) < 3:
                print("사용법: python main.py batch [개수] [--upload]")
                print("  주의: 배치는 2개 이상의 영상을 생성할 때만 사용하세요.")
                print("  단일 영상 생성은 'python main.py test' 또는 'python main.py generate'를 사용하세요.")
                sys.exit(1)
            
            count = int(sys.argv[2])
            
            # 단일 영상 생성은 일반 명령 사용 안내
            if count == 1:
                print("⚠️  단일 영상 생성은 배치 명령이 필요하지 않습니다.")
                print("💡 다음 명령을 사용하세요:")
                print("   python main.py test [주제]     - 영상 생성만")
                print("   python main.py upload [주제]  - 영상 생성 및 업로드")
                sys.exit(1)
            
            # 옵션 파싱
            upload = False
            if '--upload' in sys.argv:
                upload = True
            
            try:
                from src.pipeline.batch_generator import BatchVideoGenerator
                batch_gen = BatchVideoGenerator(max_workers=1)  # 순차 처리
                results = batch_gen.generate_batch(count=count, upload=upload)
                
                print(f"\n✅ 배치 생성 완료: {results['success']}/{results['total']} 성공")
            except Exception as e:
                print(f"\n❌ 배치 생성 중 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                print("\n💡 문제가 지속되면 단일 영상 생성('python main.py test')을 사용하세요.")
                sys.exit(1)

        elif command == 'quota-status':
            # API 할당량 상태 확인
            from src.utils.quota_manager import get_quota_manager
            quota_mgr = get_quota_manager()
            quota_mgr.print_usage_stats()

        else:
            print("사용법:")
            print("  python main.py test [주제]     - 영상 생성만 (업로드 없음)")
            print("  python main.py upload [주제] [--force]  - 즉시 영상 생성 및 업로드 (--force: 중복 체크 건너뛰기)")
            print("  python main.py batch [개수] [--upload] - 여러 영상 순차 생성 (2개 이상)")
            print("  python main.py social-upload [path] [title] - 소셜 미디어 업로드 테스트")
            print("  python main.py stats          - 모든 영상 통계 업데이트")
            print("  python main.py report         - 수익화 리포트 출력")
            print("  python main.py schedule       - 자동 업로드 스케줄러 시작")
            print("  python main.py sync-status    - 동기화 상태 확인")
            print(f"  python main.py instagram-test - Instagram Graph API 연결 테스트")
            print(f"  python main.py analyze        - YouTube Shorts 성과 분석 리포트 출력")
            print(f"  python main.py quota-status   - API 할당량 사용 현황 확인")
    else:
        # 기본: 영상 생성 후 업로드 전 확인 요청
        bot.create_and_upload(auto_upload=False)


if __name__ == '__main__':
    main()

