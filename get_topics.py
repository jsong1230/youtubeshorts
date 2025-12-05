"""
주제를 랜덤하게 3개 선택하는 스크립트
"""

import sys
import random
import signal
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from functools import wraps

from src.core.config import settings
from src.generators.script_generator import ScriptGenerator
from src.generators.content_type import ContentType

# 전역 변수: 중단 플래그
interrupted = False


def timeout_handler(signum, frame):
    """타임아웃 핸들러"""
    global interrupted
    interrupted = True
    print("\n⚠️ 작업이 중단되었습니다. (Ctrl+C 또는 타임아웃)")
    sys.exit(1)


def with_timeout(timeout_seconds=30):
    """함수 실행에 타임아웃을 추가하는 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global interrupted
            if interrupted:
                return None

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    result = future.result(timeout=timeout_seconds)
                    return result
                except FutureTimeoutError:
                    print(f"⏱️ {func.__name__} 타임아웃 ({timeout_seconds}초 초과)")
                    future.cancel()
                    return None
                except Exception as e:
                    raise e

        return wrapper

    return decorator


def collect_topics(language="en"):
    """여러 소스에서 주제를 수집 (타임아웃 및 진행 상황 표시 포함)"""
    global interrupted

    script_generator = ScriptGenerator(
        openai_client=None,  # 주제 수집만 하므로 None
        claude_client=None,
        ai_provider="openai",
    )

    # OpenAI 클라이언트가 있으면 초기화
    if settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI

            script_generator.openai_client = OpenAI(
                api_key=settings.OPENAI_API_KEY, timeout=30.0
            )
        except Exception:
            pass

    # Claude 클라이언트가 있으면 초기화
    if settings.CLAUDE_API_KEY:
        try:
            from anthropic import Anthropic

            script_generator.claude_client = Anthropic(
                api_key=settings.CLAUDE_API_KEY, timeout=30.0
            )
        except Exception:
            pass

    all_topics = []

    # 콘텐츠 타입 랜덤 선택
    content_type = random.choice(
        [
            ContentType.HOOK,
            ContentType.QUOTE,
            ContentType.STORY,
            ContentType.FACT,
            ContentType.SHORT_STORY,
        ]
    )

    print(f"📌 콘텐츠 타입: {content_type.value}")
    print("=" * 60)

    # 각 단계별 타임아웃 설정 (초)
    timeouts = {
        "reddit": 20,
        "google_trends": 30,
        "youtube": 30,
        "ai_seasonal": 60,
        "ai_general": 60,
        "performance": 10,
    }

    # 1. Reddit 트렌드 주제
    if not interrupted:
        print("📡 [1/6] Reddit 트렌드 주제 수집 중...", end=" ", flush=True)
        start_time = time.time()
        try:
            from src.analytics.reddit_collector import RedditCollector

            reddit_collector = RedditCollector()

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    reddit_collector.get_trending_topics,
                    content_type=content_type.value,
                    num_topics=10,
                    categories=["finance", "productivity", "lifestyle"],
                    language="en",
                )
                reddit_topics = future.result(timeout=timeouts["reddit"])

            if reddit_topics:
                all_topics.extend(reddit_topics)
                elapsed = time.time() - start_time
                print(f"✅ 완료 ({len(reddit_topics)}개, {elapsed:.1f}초)")
            else:
                elapsed = time.time() - start_time
                print(f"⚠️ 주제 없음 ({elapsed:.1f}초)")
        except FutureTimeoutError:
            print(f"⏱️ 타임아웃 ({timeouts['reddit']}초 초과)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 실패: {str(e)[:50]} ({elapsed:.1f}초)")

    # 2. Google Trends 주제
    if not interrupted:
        print("📡 [2/6] Google Trends 주제 수집 중...", end=" ", flush=True)
        start_time = time.time()
        try:
            from src.analytics.google_trends_collector import GoogleTrendsCollector

            trends_collector = GoogleTrendsCollector()

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    trends_collector.get_trending_topics,
                    content_type=content_type.value,
                    num_topics=10,
                    categories=["finance", "productivity", "lifestyle"],
                    language="en",
                )
                trends_topics = future.result(timeout=timeouts["google_trends"])

            if trends_topics:
                all_topics.extend(trends_topics)
                elapsed = time.time() - start_time
                print(f"✅ 완료 ({len(trends_topics)}개, {elapsed:.1f}초)")
            else:
                elapsed = time.time() - start_time
                print(f"⚠️ 주제 없음 ({elapsed:.1f}초)")
        except FutureTimeoutError:
            print(f"⏱️ 타임아웃 ({timeouts['google_trends']}초 초과)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 실패: {str(e)[:50]} ({elapsed:.1f}초)")

    # 3. YouTube 트렌드 주제
    if not interrupted:
        print("📡 [3/6] YouTube 트렌드 주제 수집 중...", end=" ", flush=True)
        start_time = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(script_generator.get_youtube_trending_topics)
                youtube_topics = future.result(timeout=timeouts["youtube"])

            if youtube_topics:
                all_topics.extend(youtube_topics)
                elapsed = time.time() - start_time
                print(f"✅ 완료 ({len(youtube_topics)}개, {elapsed:.1f}초)")
            else:
                elapsed = time.time() - start_time
                print(f"⚠️ 주제 없음 ({elapsed:.1f}초)")
        except FutureTimeoutError:
            print(f"⏱️ 타임아웃 ({timeouts['youtube']}초 초과)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 실패: {str(e)[:50]} ({elapsed:.1f}초)")

    # 4. 계절별 AI 생성 주제
    if not interrupted:
        print("📡 [4/6] 계절별 AI 주제 생성 중...", end=" ", flush=True)
        start_time = time.time()
        try:
            current_season = script_generator._get_season()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    script_generator.generate_seasonal_topics_from_trends,
                    current_season,
                    content_type,
                    language,
                )
                ai_seasonal_topics = future.result(timeout=timeouts["ai_seasonal"])

            if ai_seasonal_topics:
                all_topics.extend(ai_seasonal_topics)
                elapsed = time.time() - start_time
                print(f"✅ 완료 ({len(ai_seasonal_topics)}개, {elapsed:.1f}초)")
            else:
                elapsed = time.time() - start_time
                print(f"⚠️ 주제 없음 ({elapsed:.1f}초)")
        except FutureTimeoutError:
            print(f"⏱️ 타임아웃 ({timeouts['ai_seasonal']}초 초과)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 실패: {str(e)[:50]} ({elapsed:.1f}초)")

    # 5. 일반 AI 생성 주제
    if not interrupted:
        print("📡 [5/6] 일반 AI 주제 생성 중...", end=" ", flush=True)
        start_time = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    script_generator.generate_ai_topics_from_trends,
                    content_type,
                    language,
                )
                ai_trend_topics = future.result(timeout=timeouts["ai_general"])

            if ai_trend_topics:
                all_topics.extend(ai_trend_topics)
                elapsed = time.time() - start_time
                print(f"✅ 완료 ({len(ai_trend_topics)}개, {elapsed:.1f}초)")
            else:
                elapsed = time.time() - start_time
                print(f"⚠️ 주제 없음 ({elapsed:.1f}초)")
        except FutureTimeoutError:
            print(f"⏱️ 타임아웃 ({timeouts['ai_general']}초 초과)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 실패: {str(e)[:50]} ({elapsed:.1f}초)")

    # 6. 성과 기반 주제
    if not interrupted:
        print("📡 [6/6] 성과 기반 주제 수집 중...", end=" ", flush=True)
        start_time = time.time()
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    script_generator._get_high_performing_topics, content_type
                )
                performance_topics = future.result(timeout=timeouts["performance"])

            if performance_topics:
                all_topics.extend(performance_topics)
                elapsed = time.time() - start_time
                print(f"✅ 완료 ({len(performance_topics)}개, {elapsed:.1f}초)")
            else:
                elapsed = time.time() - start_time
                print(f"⚠️ 주제 없음 ({elapsed:.1f}초)")
        except FutureTimeoutError:
            print(f"⏱️ 타임아웃 ({timeouts['performance']}초 초과)")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 실패: {str(e)[:50]} ({elapsed:.1f}초)")

    # 중복 제거
    all_topics = list(dict.fromkeys(all_topics))  # 순서 유지하면서 중복 제거

    print("=" * 60)
    print(f"📊 총 {len(all_topics)}개 주제 수집 완료")

    return all_topics


def main():
    import sys

    global interrupted

    # Ctrl+C 핸들러 설정
    signal.signal(signal.SIGINT, timeout_handler)

    # 명령줄 인자 파싱
    num_topics = 3
    language = "en"  # 기본값: 영어

    # 인자 파싱
    for arg in sys.argv[1:]:
        if arg.isdigit():
            num_topics = int(arg)
            if num_topics < 1:
                print("⚠️ 주제 개수는 1 이상이어야 합니다. 기본값 3을 사용합니다.")
                num_topics = 3
        elif arg in ["--ko", "--korean", "-k"]:
            language = "ko"
        elif arg in ["--en", "--english", "-e"]:
            language = "en"

    lang_name = "한국어" if language == "ko" else "영어"
    print(f"🎯 주제 {num_topics}개 수집 중... ({lang_name})")
    print("💡 Ctrl+C를 누르면 안전하게 중단할 수 있습니다.")
    print()

    try:
        total_start_time = time.time()
        all_topics = collect_topics(language=language)
        total_elapsed = time.time() - total_start_time

        if interrupted:
            print("\n⚠️ 작업이 중단되었습니다.")
            return

        if not all_topics:
            print("❌ 수집된 주제가 없습니다.")
            return

        # 랜덤으로 지정된 개수만큼 선택
        selected_count = min(num_topics, len(all_topics))
        selected_topics = random.sample(all_topics, selected_count)

        print()
        print("=" * 60)
        print(
            f"🎲 랜덤 선택된 주제 {selected_count}개 (총 소요 시간: {total_elapsed:.1f}초):"
        )
        print("=" * 60)
        for i, topic in enumerate(selected_topics, 1):
            print(f"{i}. {topic}")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        interrupted = True
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
