"""
YouTube Shorts 자동 업로드 봇 메인 실행 파일
하루 1개 업로드 → 3개월 후 수익화 → 월 $100~500 목표
"""

import sys
import os
import json
from pathlib import Path
from src.utils.logger import get_logger

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logger = get_logger(__name__)


def main():
    """메인 함수"""
    import sys
    from typing import cast, List
    from src.core.config import settings

    if len(sys.argv) > 1 and sys.argv[1] == "instagram-test":
        from src.uploaders.instagram_uploader import InstagramUploader

        logger.info("🔄 Instagram Graph API 연결 테스트를 시작합니다...")
        uploader = InstagramUploader()
        success = uploader.test_connection(verbose=True)
        if success:
            logger.info("✅ Instagram 연결 테스트가 완료되었습니다.")
            sys.exit(0)
        else:
            logger.error(
                "❌ Instagram 연결 테스트에 실패했습니다. 위 로그를 참고해 설정을 점검하세요."
            )
            sys.exit(1)

    from src.pipeline.bot import ShortsBot

    bot = ShortsBot()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "topics" or command == "get-topics":
            # 주제 선정 명령어
            from get_topics import collect_topics, get_existing_topics_from_history, filter_existing_topics
            import random

            # 한국어 4개, 영어 4개 선정
            logger.info("🎯 주제 선정 중... (한국어 4개, 영어 4개)")
            logger.info("📚 HISTORY.md에서 기존 주제 확인 중...")
            
            # 한국어 주제 수집
            logger.info("")
            logger.info("=" * 60)
            logger.info("🇰🇷 한국어 주제 수집 중...")
            logger.info("=" * 60)
            korean_topics = collect_topics(language="ko")
            
            if not korean_topics:
                logger.warning("⚠️ 한국어 주제 수집 실패")
                korean_topics = []
            
            # 영어 주제 수집
            logger.info("")
            logger.info("=" * 60)
            logger.info("🇺🇸 영어 주제 수집 중...")
            logger.info("=" * 60)
            english_topics = collect_topics(language="en")
            
            if not english_topics:
                logger.warning("⚠️ 영어 주제 수집 실패")
                english_topics = []
            
            # 최종 언어 필터링 재검증 (안전장치)
            from get_topics import filter_by_language
            korean_topics = filter_by_language(korean_topics, language="ko")
            english_topics = filter_by_language(english_topics, language="en")
            
            # 각각 4개씩 선택
            korean_selected = random.sample(korean_topics, min(4, len(korean_topics))) if korean_topics else []
            english_selected = random.sample(english_topics, min(4, len(english_topics))) if english_topics else []
            
            # 선택된 주제 최종 검증
            korean_selected = filter_by_language(korean_selected, language="ko")
            english_selected = filter_by_language(english_selected, language="en")
            
            logger.info("")
            logger.info("=" * 80)
            logger.info("📋 최종 선정된 주제")
            logger.info("=" * 80)
            
            if korean_selected:
                logger.info("")
                logger.info("🇰🇷 한국어 주제 (4개):")
                logger.info("-" * 80)
                for i, topic in enumerate(korean_selected, 1):
                    logger.info(f"  {i}. {topic}")
            else:
                logger.warning("⚠️ 한국어 주제가 없습니다.")
            
            if english_selected:
                logger.info("")
                logger.info("🇺🇸 영어 주제 (4개):")
                logger.info("-" * 80)
                for i, topic in enumerate(english_selected, 1):
                    logger.info(f"  {i}. {topic}")
            else:
                logger.warning("⚠️ 영어 주제가 없습니다.")
            
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ 총 {len(korean_selected) + len(english_selected)}개 주제 선정 완료")
            logger.info("=" * 80)
            return

        if command == "test" or command == "generate":
            # 영상 생성만 (업로드 없음)
            topic = sys.argv[2] if len(sys.argv) > 2 else None
            bot.create_video_only(topic=topic)

        elif command == "upload":
            # 즉시 업로드
            # --force, -f, --public 플래그 제외하고 주제 추출
            args = [arg for arg in sys.argv[2:] if arg not in ["--force", "-f", "--public", "--private"]]
            force = "--force" in sys.argv or "-f" in sys.argv
            # 기본값: 비공개 (--public 플래그가 있으면 예약 업로드)
            is_private = "--public" not in sys.argv  # --public이 없으면 비공개가 기본값

            # 첫 번째 인자가 파일 경로인지 확인
            if args and (args[0].endswith(".mp4") or os.path.exists(args[0])):
                # 파일 경로로 업로드 (메타데이터에서 제목 읽기)
                video_path = args[0]
                metadata = bot._load_video_metadata(video_path)
                if metadata:
                    # 메타데이터에서 정보 가져오기
                    topic = metadata.get("topic")
                    title = metadata.get("title")
                    thumbnail_path = metadata.get("thumbnail_path")
                    description = bot.pipeline.metadata_manager.generate_description(
                        metadata.get("language", "en"), topic, topic
                    )

                    # 영상 자산 딕셔너리 생성
                    # video_assets = {
                    #     "video_path": video_path,
                    #     "thumbnail_path": thumbnail_path,
                    #     "title": title,
                    #     "description": description,
                    #     "tags": settings.DEFAULT_TAGS,
                    #     "actual_topic": topic,
                    #     "script": metadata.get("script", []),
                    #     "language": metadata.get("language", "en"),
                    # }

                    # 다음날 0시에 공개되도록 예약 업로드
                    from src.core.config import settings
                    from src.uploaders.youtube_uploader import (
                        calculate_hours_until_midnight,
                    )

                    # 다음날 0시까지의 시간 계산
                    hours_until_midnight = calculate_hours_until_midnight(
                        settings.UPLOAD_TIMEZONE
                    )

                    # 기본값: 비공개 즉시 업로드 (--public 플래그가 있으면 예약 업로드)
                    if is_private:
                        privacy_status = "private"
                        schedule_delay_hours = 0  # 즉시 업로드
                        logger.info("🔒 비공개 모드로 업로드합니다.")
                    else:
                        privacy_status = "unlisted"  # 예약 업로드는 unlisted로 설정
                        schedule_delay_hours = hours_until_midnight  # 다음날 0시에 공개
                        logger.info("📅 예약 업로드 모드로 설정합니다.")
                    
                    video_id = bot.uploader.upload_video(
                        video_path=video_path,
                        title=title,
                        description=description,
                        tags=cast(List[str], settings.DEFAULT_TAGS),
                        privacy_status=privacy_status,
                        thumbnail_path=thumbnail_path,
                        schedule_delay_hours=schedule_delay_hours,
                    )

                    if video_id:
                        # 데이터베이스 업데이트
                        script_str = (
                            json.dumps(metadata.get("script", []), ensure_ascii=False)
                            if metadata.get("script")
                            else None
                        )
                        bot.database.add_video(
                            video_id=video_id,
                            title=title,
                            topic=topic,
                            script=script_str,
                        )
                        # Sync manager 업데이트는 선택사항
                        try:
                            if hasattr(bot.sync_manager, "update_last_upload"):
                                bot.sync_manager.update_last_upload(video_id, title)
                        except Exception as e:
                            logger.debug(f"Sync manager 업데이트 생략: {e}")
                        upload_type = "비공개 업로드" if is_private else "예약 업로드"
                        logger.info(
                            f"\n✅ 업로드 완료! 영상 ID: {video_id} ({upload_type})"
                        )
                        logger.info(f"🔗 https://www.youtube.com/watch?v={video_id}\n")
                        logger.info(f"📁 원본 영상 파일: {video_path}")
                        logger.info(
                            f"📄 메타데이터 파일: {video_path.replace('.mp4', '_metadata.json')}"
                        )
                else:
                    logger.error(
                        "❌ 메타데이터 파일을 찾을 수 없습니다. 영상을 다시 생성하거나 주제를 직접 입력하세요."
                    )
            else:
                # 주제로 새로 생성 및 업로드
                topic = args[0] if args else None
                # upload 명령어도 업로드 전 사용자 확인 받기 (규칙: 항상 확인 후 업로드)
                bot.create_and_upload(topic=topic, force=force, auto_upload=False)

        elif command == "stats":
            # 통계 업데이트 및 리포트
            bot.update_all_stats()

        elif command == "report":
            # 리포트만 출력
            bot.monetization.print_report()

        elif command == "schedule":
            # 스케줄러 시작 (자동 업로드 모드)
            bot.run_scheduler()

        elif command == "sync-status":
            # 동기화 상태 확인
            bot.sync_manager.print_sync_status()

        elif command == "social-upload":
            # 생성된 영상 소셜 미디어 업로드 (테스트용)
            # python main.py social-upload [video_path] [title]
            if len(sys.argv) < 4:
                logger.error(
                    "사용법: python main.py social-upload [video_path] [title]"
                )
                sys.exit(1)

            video_path = sys.argv[2]
            title = sys.argv[3]

            from src.uploaders.social_manager import SocialManager

            social_manager = SocialManager()
            results = social_manager.upload_all(video_path, title, description=title)
            logger.info(f"📊 소셜 업로드 결과: {results}")

        elif command == "analyze":
            # 성과 분석 리포트
            from src.analytics.analytics_manager import AnalyticsManager

            analytics_manager = AnalyticsManager()
            analytics_manager.generate_performance_report()

        elif command == "batch":
            # 여러 영상 순차 생성 (2개 이상만 허용)
            # ⚠️ 현재 디버깅 중: 문제가 있을 수 있음
            logger.warning("⚠️  배치 기능은 현재 디버깅 중입니다.")
            logger.warning(
                "⚠️  문제가 발생할 수 있으니, 단일 영상 생성은 'python main.py test'를 사용하세요."
            )
            logger.info("")

            if len(sys.argv) < 3:
                logger.error("사용법: python main.py batch [개수] [--upload]")
                logger.error("  주의: 배치는 2개 이상의 영상을 생성할 때만 사용하세요.")
                logger.error(
                    "  단일 영상 생성은 'python main.py test' 또는 'python main.py generate'를 사용하세요."
                )
                sys.exit(1)

            count = int(sys.argv[2])

            # 단일 영상 생성은 일반 명령 사용 안내
            if count == 1:
                logger.warning("⚠️  단일 영상 생성은 배치 명령이 필요하지 않습니다.")
                logger.info("💡 다음 명령을 사용하세요:")
                logger.info("   python main.py test [주제]     - 영상 생성만")
                logger.info("   python main.py upload [주제]  - 영상 생성 및 업로드")
                sys.exit(1)

            # 옵션 파싱
            upload = False
            if "--upload" in sys.argv:
                upload = True

            try:
                from src.pipeline.batch_generator import BatchVideoGenerator

                batch_gen = BatchVideoGenerator(max_workers=1)  # 순차 처리
                results = batch_gen.generate_batch(count=count, upload=upload)

                logger.info(
                    f"\n✅ 배치 생성 완료: {results['success']}/{results['total']} 성공"
                )
            except Exception as e:
                logger.error(f"\n❌ 배치 생성 중 오류 발생: {e}", exc_info=True)
                logger.info(
                    "\n💡 문제가 지속되면 단일 영상 생성('python main.py test')을 사용하세요."
                )
                sys.exit(1)

        elif command == "quota-status":
            # API 할당량 상태 확인
            from src.utils.quota_manager import get_quota_manager

            quota_mgr = get_quota_manager()
            quota_mgr.print_usage_stats()

        elif command == "compare-history" or command == "sync-history":
            # 채널의 영상 목록과 HISTORY.md 비교 및 자동 업데이트
            from src.analytics.channel_history_collector import ChannelHistoryCollector
            from datetime import datetime
            import re
            from pathlib import Path
            from collections import defaultdict

            logger.info("📊 채널 영상 목록과 HISTORY.md 비교 및 동기화 중...")
            
            # 1. 채널에서 영상 목록 가져오기
            collector = ChannelHistoryCollector()
            channel_videos = collector.get_channel_videos(max_results=200, days=None)
            
            if not channel_videos:
                logger.error("❌ 채널에서 영상 목록을 가져올 수 없습니다.")
                return
            
            logger.info(f"✅ 채널에서 {len(channel_videos)}개 영상 수집 완료")
            
            # 2. HISTORY.md에서 영상 정보 추출
            history_file = Path(__file__).parent / "HISTORY.md"
            if not history_file.exists():
                logger.error("❌ HISTORY.md 파일을 찾을 수 없습니다.")
                return
            
            history_content = history_file.read_text(encoding="utf-8")
            original_history_content = history_content  # 백업용 원본 저장
            
            # Video ID 패턴 찾기
            # 주석 처리된 Video ID는 제외하기 위해 두 단계로 처리
            video_id_pattern = r"Video ID[:\s]*`([A-Za-z0-9_-]+)`"
            all_video_ids = re.findall(video_id_pattern, history_content, re.IGNORECASE)
            
            # 주석 처리된 Video ID 찾기
            commented_video_id_pattern = r"<!--\s*Video ID[:\s]*`([A-Za-z0-9_-]+)`"
            commented_video_ids = set(re.findall(commented_video_id_pattern, history_content, re.IGNORECASE))
            
            # 주석 처리되지 않은 Video ID만 사용
            history_video_ids = set(all_video_ids) - commented_video_ids
            
            logger.info(f"✅ HISTORY.md에서 {len(history_video_ids)}개 Video ID 추출 완료")
            
            # 3. 비교 분석
            channel_video_ids = {v["video_id"] for v in channel_videos}
            channel_video_map = {v["video_id"]: v for v in channel_videos}
            
            # 채널에는 있지만 HISTORY에 없는 영상
            missing_in_history = channel_video_ids - history_video_ids
            
            # HISTORY에는 있지만 채널에 없는 영상 (삭제되었거나 잘못 기록된 경우)
            missing_in_channel = history_video_ids - channel_video_ids
            
            # 4. 결과 출력
            logger.info("")
            logger.info("=" * 80)
            logger.info("📊 비교 결과")
            logger.info("=" * 80)
            logger.info(f"채널 영상 수: {len(channel_videos)}개")
            logger.info(f"HISTORY.md 기록 수: {len(history_video_ids)}개 (Video ID 기준)")
            logger.info("")
            
            updated = False
            
            # 5. 누락된 영상들을 HISTORY.md에 추가
            if missing_in_history:
                logger.info(f"📝 HISTORY.md에 누락된 영상 {len(missing_in_history)}개 추가 중...")
                
                # 날짜별로 그룹화
                videos_by_date = defaultdict(list)
                for video_id in missing_in_history:
                    video = channel_video_map.get(video_id)
                    if video:
                        published_at = video.get("published_at")
                        if isinstance(published_at, datetime):
                            date_key = published_at.strftime("%Y-%m-%d")
                        else:
                            date_key = datetime.now().strftime("%Y-%m-%d")
                        videos_by_date[date_key].append(video)
                
                # 날짜순으로 정렬 (최신순)
                sorted_dates = sorted(videos_by_date.keys(), reverse=True)
                
                # HISTORY.md에 추가할 내용 생성
                new_entries = []
                for date in sorted_dates:
                    videos = videos_by_date[date]
                    # 날짜별로 그룹화하여 추가
                    entry_lines = [f"- **{date} - Video Upload (채널 동기화로 추가됨) - {len(videos)}개 영상**"]
                    
                    for i, video in enumerate(videos, 1):
                        title = video.get("title", "").replace(" #Shorts", "").strip()
                        topic = video.get("topic", title)
                        video_id = video.get("video_id", "")
                        published_at = video.get("published_at", "")
                        
                        # 언어 판단 (제목에 한글이 있으면 한국어)
                        is_korean = any(ord(char) >= 0xAC00 and ord(char) <= 0xD7A3 for char in title)
                        lang_label = "한국어" if is_korean else "영어"
                        
                        entry_lines.append(f"  - **{lang_label} 영상 {i}**: {topic}")
                        entry_lines.append(f"    - Video ID: `{video_id}`")
                        entry_lines.append(f"    - URL: <https://www.youtube.com/watch?v={video_id}>")
                        if published_at:
                            if isinstance(published_at, datetime):
                                entry_lines.append(f"    - 업로드일: {published_at.strftime('%Y-%m-%d %H:%M:%S')}")
                            else:
                                entry_lines.append(f"    - 업로드일: {published_at}")
                        entry_lines.append("")
                    
                    new_entries.extend(entry_lines)
                
                # Recent Updates 섹션 바로 아래에 추가
                # "## Recent Updates" 다음 줄에 삽입 (빈 줄 제거)
                insert_pattern = r"(## Recent Updates\n)"
                if re.search(insert_pattern, history_content):
                    # 기존 Recent Updates 다음에 빈 줄이 있으면 그대로, 없으면 추가
                    insert_text = "\n".join(new_entries) + "\n"
                    history_content = re.sub(
                        insert_pattern,
                        r"\1\n" + insert_text,
                        history_content,
                        count=1
                    )
                    updated = True
                    logger.info(f"✅ {len(missing_in_history)}개 영상을 HISTORY.md에 추가했습니다.")
                else:
                    logger.warning("⚠️  '## Recent Updates' 섹션을 찾을 수 없습니다. 파일 끝에 추가합니다.")
                    # 파일 끝에 추가
                    history_content = history_content.rstrip() + "\n\n" + "\n".join(new_entries) + "\n"
                    updated = True
                    logger.info(f"✅ {len(missing_in_history)}개 영상을 HISTORY.md 끝에 추가했습니다.")
            else:
                logger.info("✅ HISTORY.md에 모든 채널 영상이 기록되어 있습니다.")
            
            # 6. 채널에 없는 영상들을 HISTORY.md에서 주석 처리
            if missing_in_channel:
                logger.info(f"🗑️  채널에 없는 영상 {len(missing_in_channel)}개 주석 처리 중...")
                
                for video_id in missing_in_channel:
                    # Video ID가 포함된 영상 블록 전체 찾기
                    # 패턴: "영상 N:" 부터 다음 "영상" 또는 "Video Upload" 항목까지
                    # 또는 Video ID부터 다음 항목(- **로 시작하는 항목)까지
                    pattern = rf"(\s+-\s+\*\*[^\*]+\*\*[^\n]*\n(?:(?!\s+-\s+\*\*)[^\n]*\n)*\s+Video ID[:\s]*`{re.escape(video_id)}`[^\n]*\n(?:(?!\s+-\s+\*\*)[^\n]*\n)*)"
                    
                    def replace_missing(match):
                        # 주석 처리 (<!-- -->)
                        block = match.group(1)
                        lines = block.split('\n')
                        commented_lines = []
                        for line in lines:
                            if line.strip():
                                # 이미 주석 처리되어 있지 않으면 주석 처리
                                if not line.strip().startswith('<!--'):
                                    commented_lines.append(f"<!-- {line} -->")
                                else:
                                    commented_lines.append(line)
                            else:
                                commented_lines.append(line)
                        return '\n'.join(commented_lines)
                    
                    new_content = re.sub(pattern, replace_missing, history_content, flags=re.MULTILINE)
                    if new_content != history_content:
                        history_content = new_content
                        updated = True
                        logger.info(f"  - Video ID {video_id} 주석 처리됨")
                
                if updated:
                    logger.info(f"✅ {len(missing_in_channel)}개 영상을 HISTORY.md에서 주석 처리했습니다.")
            else:
                logger.info("✅ 채널에 모든 HISTORY.md 기록이 존재합니다.")
            
            # 6-1. 주석 처리된 영상 중 채널에 다시 나타난 영상 주석 해제
            uncomment_video_ids = set()
            commented_video_pattern = r"<!--\s*Video ID[:\s]*`([A-Za-z0-9_-]+)`"
            commented_video_ids = set(re.findall(commented_video_pattern, history_content, re.IGNORECASE))
            
            if commented_video_ids:
                # 주석 처리된 영상 중 채널에 있는 영상 찾기
                uncomment_video_ids = commented_video_ids & channel_video_ids
                
                if uncomment_video_ids:
                    logger.info(f"🔄 주석 처리된 영상 중 {len(uncomment_video_ids)}개가 채널에 다시 나타나 주석 해제 중...")
                    
                    for video_id in uncomment_video_ids:
                        # 주석 처리된 블록 찾기 및 해제
                        # Video ID가 포함된 주석 처리된 블록 전체 찾기
                        # 각 줄에서 <!-- 와 --> 제거
                        pattern = rf"((?:<!--\s+[^\n]*\n)*<!--\s+-\s+\*\*[^\*]+\*\*[^\n]*\n(?:(?:<!--\s+[^\n]*\n)*)*<!--\s+Video ID[:\s]*`{re.escape(video_id)}`[^\n]*\n(?:(?:<!--\s+[^\n]*\n)*)*)"
                        
                        def uncomment_block(match):
                            block = match.group(1)
                            # 각 줄에서 <!-- 와 --> 제거
                            lines = block.split('\n')
                            uncommented_lines = []
                            for line in lines:
                                stripped = line.strip()
                                if stripped.startswith('<!--') and stripped.endswith('-->'):
                                    # <!-- 내용 --> 형식
                                    content = stripped[4:-3].strip()
                                    indent = len(line) - len(line.lstrip())
                                    uncommented_lines.append(' ' * indent + content)
                                elif stripped.startswith('<!--'):
                                    # <!-- 내용 (다음 줄에 -->)
                                    content = stripped[4:].strip()
                                    indent = len(line) - len(line.lstrip())
                                    uncommented_lines.append(' ' * indent + content)
                                elif stripped == '-->':
                                    # --> 만 있는 줄은 건너뛰기
                                    continue
                                else:
                                    uncommented_lines.append(line)
                            return '\n'.join(uncommented_lines)
                        
                        new_content = re.sub(pattern, uncomment_block, history_content, flags=re.MULTILINE)
                        if new_content != history_content:
                            history_content = new_content
                            updated = True
                            logger.info(f"  - Video ID {video_id} 주석 해제됨")
                    
                    if updated:
                        logger.info(f"✅ {len(uncomment_video_ids)}개 영상의 주석을 해제했습니다.")
            
            logger.info("=" * 80)
            
            # 7. HISTORY.md 파일 업데이트
            if updated:
                # 백업 생성 (원본 내용 사용)
                backup_file = history_file.with_suffix('.md.bak')
                backup_file.write_text(original_history_content, encoding="utf-8")
                logger.info(f"📄 백업 파일 생성: {backup_file}")
                
                # 업데이트된 내용 저장
                history_file.write_text(history_content, encoding="utf-8")
                logger.info(f"✅ HISTORY.md 파일이 업데이트되었습니다.")
                logger.info("")
                logger.info("📋 변경 사항 요약:")
                if missing_in_history:
                    logger.info(f"  - 추가된 영상: {len(missing_in_history)}개")
                if missing_in_channel:
                    logger.info(f"  - 주석 처리된 영상: {len(missing_in_channel)}개")
                if uncomment_video_ids:
                    logger.info(f"  - 주석 해제된 영상: {len(uncomment_video_ids)}개")
            else:
                logger.info("ℹ️  업데이트할 내용이 없습니다.")

        else:
            logger.info("사용법:")
            logger.info("  python main.py topics [개수]   - 주제 선정 (기본값: 3개)")
            logger.info("  python main.py test [주제]     - 영상 생성만 (업로드 없음)")
            logger.info(
                "  python main.py upload [주제/파일] [--force] [--public]  - 즉시 영상 생성 및 업로드"
            )
            logger.info(
                "    --force: 중복 체크 건너뛰기"
            )
            logger.info(
                "    --public: 예약 업로드 모드 (기본값: 비공개 즉시 업로드)"
            )
            logger.info(
                "  python main.py batch [개수] [--upload] - 여러 영상 순차 생성 (2개 이상)"
            )
            logger.info(
                "  python main.py social-upload [path] [title] - 소셜 미디어 업로드 테스트"
            )
            logger.info("  python main.py stats          - 모든 영상 통계 업데이트")
            logger.info("  python main.py report         - 수익화 리포트 출력")
            logger.info("  python main.py schedule       - 자동 업로드 스케줄러 시작")
            logger.info("  python main.py sync-status    - 동기화 상태 확인")
            logger.info(
                "  python main.py instagram-test - Instagram Graph API 연결 테스트"
            )
            logger.info(
                "  python main.py analyze        - YouTube Shorts 성과 분석 리포트 출력"
            )
            logger.info("  python main.py quota-status   - API 할당량 사용 현황 확인")
            logger.info("  python main.py compare-history - 채널 영상과 HISTORY.md 비교")
    else:
        # 기본: 영상 생성 후 업로드 전 확인 요청
        bot.create_and_upload(auto_upload=False)


if __name__ == "__main__":
    main()
