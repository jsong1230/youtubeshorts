"""
주제를 랜덤하게 3개 선택하는 스크립트
"""

import sys
import random
import signal
import time
import re
from pathlib import Path
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


def get_existing_topics_from_history(language="en"):
    """
    HISTORY.md에서 기존 주제 추출
    
    Args:
        language: 'ko' 또는 'en'
        
    Returns:
        기존 주제 Set (중복 체크용)
    """
    history_file = Path(__file__).parent / "HISTORY.md"
    if not history_file.exists():
        return set()
    
    try:
        history_content = history_file.read_text(encoding="utf-8")
        topics = set()
        
        # 주제 패턴 찾기
        # 패턴 1: "**한국어 영상 N**: 주제" 또는 "**영어 영상 N**: 주제"
        # 패턴 2: "주제: ..." 형식
        # 패턴 3: "- **한국어 영상 N**: 주제"
        
        if language == "ko":
            # 한국어 주제 패턴
            patterns = [
                r"-\s+\*\*한국어 영상\s+\d+\*\*:\s*(.+?)(?:\n|$)",
                r"주제[:\s]*[:：]?\s*(.+?)(?:\n|Video ID|URL|길이|상태)",
            ]
        else:
            # 영어 주제 패턴
            patterns = [
                r"-\s+\*\*영어 영상\s+\d+\*\*:\s*(.+?)(?:\n|$)",
                r"Topic[:\s]*[:：]?\s*(.+?)(?:\n|Video ID|URL|Length|Status)",
            ]
        
        for pattern in patterns:
            matches = re.findall(pattern, history_content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                topic = match.strip()
                # #Shorts 태그 제거
                topic = topic.replace(" #Shorts", "").replace("#Shorts", "").strip()
                if topic and len(topic) > 5:  # 너무 짧은 것은 제외
                    topics.add(topic.lower())
        
        print(f"📚 HISTORY.md에서 {len(topics)}개 기존 주제 발견 ({language})")
        return topics
    except Exception as e:
        print(f"⚠️ HISTORY.md 읽기 실패: {e}")
        return set()


def filter_existing_topics(topics, existing_topics):
    """
    기존 주제와 유사한 주제 필터링
    
    Args:
        topics: 새 주제 리스트
        existing_topics: 기존 주제 Set
        
    Returns:
        필터링된 주제 리스트
    """
    if not existing_topics:
        return topics
    
    filtered = []
    for topic in topics:
        topic_lower = topic.lower().strip()
        
        # 정확히 일치하는 경우 제외
        if topic_lower in existing_topics:
            continue
        
        # 부분 일치 체크 (너무 유사한 주제 제외)
        is_similar = False
        for existing in existing_topics:
            # 한쪽이 다른 쪽에 포함되어 있고, 길이가 비슷하면 유사한 것으로 간주
            if (topic_lower in existing or existing in topic_lower) and abs(len(topic_lower) - len(existing)) < 20:
                is_similar = True
                break
        
        if not is_similar:
            filtered.append(topic)
    
    return filtered


def filter_by_language(topics, language="en"):
    """
    주제를 언어별로 필터링 (한글과 영어만 허용)
    
    Args:
        topics: 주제 리스트
        language: 'ko' 또는 'en'
        
    Returns:
        해당 언어로만 작성된 주제 리스트
    """
    if not topics:
        return []
    
    filtered = []
    excluded_count = 0
    excluded_reasons = {}
    
    for topic in topics:
        # 한글 문자 개수
        korean_chars = len(re.findall(r"[가-힣]", topic))
        # 영어 문자 개수 (ASCII 영문자만)
        english_chars = len(re.findall(r"[a-zA-Z]", topic))
        
        # 특수 문자, 숫자, 이모지 제거 후 실제 문자만 계산
        clean_topic = re.sub(r"[^\w\s가-힣]", "", topic)
        clean_korean = len(re.findall(r"[가-힣]", clean_topic))
        clean_english = len(re.findall(r"[a-zA-Z]", clean_topic))
        clean_total = clean_korean + clean_english
        
        if clean_total == 0:
            continue  # 한글/영어 문자가 없으면 제외
        
        # 다른 언어 문자 체크 (ASCII 영문자와 한글만 허용)
        # 1. 라틴어 확장 문자 (스페인어, 독일어, 프랑스어 등)
        latin_extended = len(re.findall(r"[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]", topic, re.IGNORECASE))
        # 2. 키릴 문자 (러시아어 등)
        cyrillic = len(re.findall(r"[А-Яа-яЁё]", topic))
        # 3. 아랍어 문자
        arabic = len(re.findall(r"[\u0600-\u06FF]", topic))
        # 4. 힌디어/텔루구어 등 인도 언어 (데바나가리, 텔루구 문자 등)
        # 텔루구: \u0C00-\u0C7F, 데바나가리: \u0900-\u097F, 타밀어: \u0B80-\u0BFF
        indic_scripts = len(re.findall(r"[\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF\u0980-\u09FF]", topic))
        # 5. 중국어/일본어 문자
        cjk = len(re.findall(r"[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]", topic))
        # 6. 태국어
        thai = len(re.findall(r"[\u0E00-\u0E7F]", topic))
        # 7. 그리스어
        greek = len(re.findall(r"[\u0370-\u03FF]", topic))
        # 8. 히브리어
        hebrew = len(re.findall(r"[\u0590-\u05FF]", topic))
        
        # 다른 언어 문자가 하나라도 있으면 제외
        if latin_extended > 0:
            excluded_count += 1
            excluded_reasons['latin_extended'] = excluded_reasons.get('latin_extended', 0) + 1
            continue
        if cyrillic > 0:
            excluded_count += 1
            excluded_reasons['cyrillic'] = excluded_reasons.get('cyrillic', 0) + 1
            continue
        if arabic > 0:
            excluded_count += 1
            excluded_reasons['arabic'] = excluded_reasons.get('arabic', 0) + 1
            continue
        if indic_scripts > 0:
            excluded_count += 1
            excluded_reasons['indic_scripts'] = excluded_reasons.get('indic_scripts', 0) + 1
            # 디버깅: 텔루구어 등 인도 언어 발견 시 로그
            if indic_scripts > 0:
                print(f"  ⚠️ 인도 언어 문자 발견 (제외): {topic[:50]}... (인도 언어 문자 {indic_scripts}개)")
            continue
        if cjk > 0:
            excluded_count += 1
            excluded_reasons['cjk'] = excluded_reasons.get('cjk', 0) + 1
            continue
        if thai > 0:
            excluded_count += 1
            excluded_reasons['thai'] = excluded_reasons.get('thai', 0) + 1
            continue
        if greek > 0:
            excluded_count += 1
            excluded_reasons['greek'] = excluded_reasons.get('greek', 0) + 1
            continue
        if hebrew > 0:
            excluded_count += 1
            excluded_reasons['hebrew'] = excluded_reasons.get('hebrew', 0) + 1
            continue
        
        # 추가 체크: ASCII 영문자와 한글 외의 유니코드 문자 확인
        # 허용 문자: ASCII 영문자(a-zA-Z), 한글(가-힣), 공백, 숫자, 기본 구두점
        allowed_chars = re.findall(r"[a-zA-Z가-힣\s0-9.,!?;:'\"()\-]", topic)
        allowed_ratio = len("".join(allowed_chars)) / len(topic) if len(topic) > 0 else 0
        
        # 허용된 문자 비율이 80% 미만이면 제외 (너무 많은 특수문자나 다른 문자)
        if allowed_ratio < 0.8:
            excluded_count += 1
            excluded_reasons['low_allowed_ratio'] = excluded_reasons.get('low_allowed_ratio', 0) + 1
            continue
        
        if language == "ko":
            # 한국어 주제: 한글이 70% 이상이어야 함 (엄격하게)
            korean_ratio = clean_korean / clean_total if clean_total > 0 else 0
            # 영어 비율이 30% 이하여야 함
            english_ratio = clean_english / clean_total if clean_total > 0 else 0
            if korean_ratio >= 0.7 and english_ratio <= 0.3:
                filtered.append(topic)
        else:
            # 영어 주제: 영어가 95% 이상이어야 함 (매우 엄격하게)
            english_ratio = clean_english / clean_total if clean_total > 0 else 0
            korean_ratio = clean_korean / clean_total if clean_total > 0 else 0
            # 영어 비율이 매우 높고 한글 비율이 거의 없어야 함
            # 최소 10자 이상의 영어 문자가 있어야 함
            if english_ratio >= 0.95 and korean_ratio < 0.05 and clean_english >= 10:
                filtered.append(topic)
            else:
                excluded_count += 1
                excluded_reasons['english_ratio'] = excluded_reasons.get('english_ratio', 0) + 1
    
    # 디버깅 정보 출력
    if excluded_count > 0 and excluded_reasons:
        reason_str = ", ".join([f"{k}: {v}" for k, v in excluded_reasons.items()])
        print(f"  📊 언어 필터링 상세: 총 {excluded_count}개 제외 ({reason_str})")
    
    return filtered


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

    # 언어별 필터링 (한국어는 한글만, 영어는 영어만)
    original_count = len(all_topics)
    all_topics = filter_by_language(all_topics, language=language)
    lang_filtered_count = original_count - len(all_topics)
    if lang_filtered_count > 0:
        print(f"🌐 언어 필터링: {lang_filtered_count}개 제외됨 ({language})")

    # HISTORY.md에서 기존 주제 가져오기 및 필터링
    existing_topics = get_existing_topics_from_history(language=language)
    if existing_topics:
        original_count = len(all_topics)
        all_topics = filter_existing_topics(all_topics, existing_topics)
        filtered_count = original_count - len(all_topics)
        if filtered_count > 0:
            print(f"🚫 HISTORY.md 중복 주제 {filtered_count}개 제외됨")

    print("=" * 60)
    print(f"📊 총 {len(all_topics)}개 주제 수집 완료 (언어 필터링 + HISTORY.md 필터링 후)")

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
