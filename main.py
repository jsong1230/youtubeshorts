"""
YouTube Shorts 자동 업로드 봇 메인 실행 파일
하루 1개 업로드 → 3개월 후 수익화 → 월 $100~500 목표
"""
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.pipeline.bot import ShortsBot


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

