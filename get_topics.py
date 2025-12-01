"""
주제를 랜덤하게 3개 선택하는 스크립트
"""
import sys
import random
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import config
from src.generators.script_generator import ScriptGenerator
from src.generators.content_type import ContentType

def collect_topics():
    """여러 소스에서 주제를 수집"""
    script_generator = ScriptGenerator(
        openai_client=None,  # 주제 수집만 하므로 None
        claude_client=None,
        ai_provider='openai'
    )
    
    # OpenAI 클라이언트가 있으면 초기화
    if config.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            script_generator.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        except:
            pass
    
    # Claude 클라이언트가 있으면 초기화
    if config.CLAUDE_API_KEY:
        try:
            from anthropic import Anthropic
            script_generator.claude_client = Anthropic(api_key=config.CLAUDE_API_KEY)
        except:
            pass
    
    all_topics = []
    
    # 콘텐츠 타입 랜덤 선택
    content_type = random.choice([
        ContentType.HOOK, ContentType.QUOTE, ContentType.STORY,
        ContentType.FACT, ContentType.SHORT_STORY
    ])
    
    print(f"📌 콘텐츠 타입: {content_type.value}")
    print("=" * 60)
    
    # 1. Reddit 트렌드 주제
    try:
        from src.analytics.reddit_collector import RedditCollector
        reddit_collector = RedditCollector()
        reddit_topics = reddit_collector.get_trending_topics(
            content_type=content_type.value,
            num_topics=10,
            categories=['finance', 'productivity', 'lifestyle'],
            language='en'
        )
        if reddit_topics:
            all_topics.extend(reddit_topics)
            print(f"✅ Reddit에서 {len(reddit_topics)}개 주제 수집")
    except Exception as e:
        print(f"⚠️ Reddit 주제 수집 실패: {e}")
    
    # 2. Google Trends 주제
    try:
        from src.analytics.google_trends_collector import GoogleTrendsCollector
        trends_collector = GoogleTrendsCollector()
        trends_topics = trends_collector.get_trending_topics(
            content_type=content_type.value,
            num_topics=10,
            categories=['finance', 'productivity', 'lifestyle'],
            language='en'
        )
        if trends_topics:
            all_topics.extend(trends_topics)
            print(f"✅ Google Trends에서 {len(trends_topics)}개 주제 수집")
    except Exception as e:
        print(f"⚠️ Google Trends 주제 수집 실패: {e}")
    
    # 3. YouTube 트렌드 주제
    try:
        youtube_topics = script_generator.get_youtube_trending_topics()
        if youtube_topics:
            all_topics.extend(youtube_topics)
            print(f"✅ YouTube 트렌드에서 {len(youtube_topics)}개 주제 수집")
    except Exception as e:
        print(f"⚠️ YouTube 트렌드 주제 수집 실패: {e}")
    
    # 4. 계절별 AI 생성 주제
    try:
        current_season = script_generator._get_season()
        ai_seasonal_topics = script_generator.generate_seasonal_topics_from_trends(
            current_season, content_type, language='en'
        )
        if ai_seasonal_topics:
            all_topics.extend(ai_seasonal_topics)
            print(f"✅ 계절별 AI 주제 {len(ai_seasonal_topics)}개 생성 ({current_season})")
    except Exception as e:
        print(f"⚠️ 계절별 AI 주제 생성 실패: {e}")
    
    # 5. 일반 AI 생성 주제
    try:
        ai_trend_topics = script_generator.generate_ai_topics_from_trends(
            content_type, language='en'
        )
        if ai_trend_topics:
            all_topics.extend(ai_trend_topics)
            print(f"✅ AI 생성 주제 {len(ai_trend_topics)}개 생성")
    except Exception as e:
        print(f"⚠️ AI 주제 생성 실패: {e}")
    
    # 6. 성과 기반 주제
    try:
        performance_topics = script_generator._get_high_performing_topics(content_type)
        if performance_topics:
            all_topics.extend(performance_topics)
            print(f"✅ 성과 기반 주제 {len(performance_topics)}개 수집")
    except Exception as e:
        print(f"⚠️ 성과 기반 주제 수집 실패: {e}")
    
    # 중복 제거
    all_topics = list(dict.fromkeys(all_topics))  # 순서 유지하면서 중복 제거
    
    print("=" * 60)
    print(f"📊 총 {len(all_topics)}개 주제 수집 완료")
    
    return all_topics

def main():
    import sys
    
    # 명령줄 인자에서 주제 개수 읽기 (기본값: 3)
    num_topics = 3
    if len(sys.argv) > 1:
        try:
            num_topics = int(sys.argv[1])
            if num_topics < 1:
                print("⚠️ 주제 개수는 1 이상이어야 합니다. 기본값 3을 사용합니다.")
                num_topics = 3
        except ValueError:
            print(f"⚠️ '{sys.argv[1]}'는 유효한 숫자가 아닙니다. 기본값 3을 사용합니다.")
            num_topics = 3
    
    print(f"🎯 주제 {num_topics}개 수집 중...")
    print()
    
    all_topics = collect_topics()
    
    if not all_topics:
        print("❌ 수집된 주제가 없습니다.")
        return
    
    # 랜덤으로 지정된 개수만큼 선택
    selected_count = min(num_topics, len(all_topics))
    selected_topics = random.sample(all_topics, selected_count)
    
    print()
    print("=" * 60)
    print(f"🎲 랜덤 선택된 주제 {selected_count}개:")
    print("=" * 60)
    for i, topic in enumerate(selected_topics, 1):
        print(f"{i}. {topic}")
    print("=" * 60)

if __name__ == '__main__':
    main()

