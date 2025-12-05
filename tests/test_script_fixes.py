#!/usr/bin/env python3
"""
스크립트 중복 및 반복 문제 해결 테스트
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from generators.script_generator import ScriptGenerator, ContentType


def test_repetition_removal():
    """반복 구절 제거 테스트"""
    print("=" * 60)
    print("Test 1: Repetitive Phrase Removal")
    print("=" * 60)

    generator = ScriptGenerator()

    # 반복 구절이 있는 테스트 문장들
    test_sentences = [
        "This is important why contributing before december 31st changes everything",
        "You need to know why contributing before december 31st changes everything",
        "Here's the secret why contributing before december 31st changes everything",
        "Don't forget why contributing before december 31st changes everything",
        "Remember this key point for your future",
        "Take action now for your future",
    ]

    print("\n원본 문장:")
    for i, sent in enumerate(test_sentences, 1):
        print(f"  {i}. {sent}")

    cleaned = generator.script_parser.remove_repetitive_phrases(test_sentences)

    print("\n정리된 문장:")
    for i, sent in enumerate(cleaned, 1):
        print(f"  {i}. {sent}")

    # 검증: 반복 구절이 제거되었는지 확인
    ending_phrase = "why contributing before december 31st changes everything"
    count_before = sum(1 for s in test_sentences if ending_phrase in s.lower())
    count_after = sum(1 for s in cleaned if ending_phrase in s.lower())

    print(f"\n반복 구절 '{ending_phrase[:30]}...':")
    print(f"  제거 전: {count_before}회")
    print(f"  제거 후: {count_after}회")

    if count_after < count_before:
        print("✅ 반복 구절 제거 테스트 통과\n")
    else:
        print("❌ 반복 구절 제거 실패\n")


def test_script_generation():
    """실제 스크립트 생성 테스트"""
    print("=" * 60)
    print("Test 2: Script Generation with Anti-Repetition")
    print("=" * 60)

    generator = ScriptGenerator()

    topics = [
        "401k Deadline Alert",
        "January Financial Reset",
        "Year-End Bonus Strategy",
    ]

    for topic in topics:
        print(f"\n주제: {topic}")
        print("-" * 40)

        try:
            script = generator.generate_script(
                topic=topic, content_type=ContentType.HOOK, language="en"
            )

            if script:
                print(f"생성된 문장 수: {len(script)}")
                print("처음 3문장:")
                for i, sent in enumerate(script[:3], 1):
                    print(f"  {i}. {sent}")

                # 반복 패턴 검사
                endings = []
                for sent in script:
                    words = sent.split()
                    if len(words) >= 5:
                        endings.append(" ".join(words[-5:]).lower())

                from collections import Counter

                ending_counts = Counter(endings)
                repetitive = [
                    phrase for phrase, count in ending_counts.items() if count >= 3
                ]

                if repetitive:
                    print(f"⚠️ 반복 패턴 발견: {repetitive}")
                else:
                    print("✅ 반복 패턴 없음")
            else:
                print("❌ 스크립트 생성 실패")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")

    print("\n" + "=" * 60)


def test_uniqueness_check():
    """스크립트 유니크성 검사 테스트"""
    print("=" * 60)
    print("Test 3: Script Uniqueness Check")
    print("=" * 60)

    generator = ScriptGenerator()

    # 동일한 스크립트
    # script1 = ["This is a test", "Another sentence", "Final thought"]
    script2 = ["This is a test", "Another sentence", "Final thought"]

    # 다른 스크립트
    script3 = ["Completely different", "Unique content", "New ideas"]

    print("\n동일한 스크립트 비교:")
    is_unique = generator.script_validator.is_script_unique(script2)
    print(f"  결과: {'유니크함' if is_unique else '중복됨'}")

    print("\n다른 스크립트 비교:")
    is_unique = generator.script_validator.is_script_unique(script3)
    print(f"  결과: {'유니크함' if is_unique else '중복됨'}")

    print("\n✅ 유니크성 검사 테스트 완료\n")


if __name__ == "__main__":
    try:
        test_repetition_removal()
        # test_script_generation()  # API 키 필요, 비용 발생 가능
        test_uniqueness_check()

        print("=" * 60)
        print("🎉 모든 테스트 완료!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
