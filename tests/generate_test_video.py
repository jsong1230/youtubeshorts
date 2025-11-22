#!/usr/bin/env python3
"""
GPT API로 테스트 영상 생성
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from generators.video_generator import AIVideoGenerator
from generators.script_generator import ContentType

def generate_test_video():
    """GPT API로 테스트 영상 생성"""
    print("=" * 60)
    print("GPT API 테스트 영상 생성")
    print("=" * 60)
    
    generator = AIVideoGenerator()
    
    # 테스트 주제
    test_topic = "Smart Money Moves for 2025"
    
    print(f"\n주제: {test_topic}")
    print(f"언어: English")
    print(f"콘텐츠 타입: Hook")
    print(f"타겟 오디언스: Young Professionals")
    print("\n영상 생성 시작...\n")
    
    try:
        video_path, thumbnail_path, selected_topic, script = generator.generate_video(
            topic=test_topic,
            content_type=ContentType.HOOK,
            language='en',
            target_audience="Young Professionals aged 25-35"
        )
        
        print("\n" + "=" * 60)
        print("✅ 영상 생성 완료!")
        print("=" * 60)
        print(f"\n영상 경로: {video_path}")
        print(f"선택된 주제: {selected_topic}")
        print(f"\n생성된 스크립트 ({len(script)}개 문장):")
        print("-" * 60)
        
        for i, sentence in enumerate(script, 1):
            print(f"{i:2d}. {sentence}")
        
        # 반복 패턴 검사
        print("\n" + "=" * 60)
        print("반복 패턴 검사")
        print("=" * 60)
        
        endings = []
        for sent in script:
            words = sent.split()
            if len(words) >= 5:
                ending = " ".join(words[-5:]).lower()
                endings.append(ending)
        
        from collections import Counter
        ending_counts = Counter(endings)
        
        print(f"\n문장 끝 구절 분석:")
        for ending, count in ending_counts.most_common(5):
            status = "⚠️ 반복!" if count >= 3 else "✅"
            print(f"  {status} '{ending[:50]}...' - {count}회")
        
        repetitive = [phrase for phrase, count in ending_counts.items() if count >= 3]
        
        if repetitive:
            print(f"\n❌ 경고: {len(repetitive)}개의 반복 패턴 발견!")
            print("다음 구절들이 3회 이상 반복됨:")
            for phrase in repetitive:
                print(f"  - {phrase}")
        else:
            print(f"\n✅ 반복 패턴 없음 - 모든 문장 끝이 유니크합니다!")
        
        return video_path, script
        
    except Exception as e:
        print(f"\n❌ 영상 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    video_path, script = generate_test_video()
    
    if video_path:
        print("\n" + "=" * 60)
        print("테스트 완료")
        print("=" * 60)
        print(f"\n생성된 영상을 확인하세요: {video_path}")
        print("\n반복 문제가 해결되었는지 영상을 재생하여 확인해주세요.")
    else:
        sys.exit(1)

