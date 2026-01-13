"""
사용자 제공 스크립트로 영상 생성
사용법:
    python create_from_custom_script.py <스크립트_파일_경로>

스크립트 파일 형식:
    영어와 한국어 스크립트를 |||SPLIT|||로 구분
    각 언어별로 **[Title]**, **[Hook]**, **[Body]**, **[Outro]** 또는 **[제목]**, **[후킹]**, **[본문]**, **[결론]** 섹션 포함
"""

import sys
import os
import argparse
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.generators.video_generator import AIVideoGenerator  # noqa: E402
from src.generators.content_type import ContentType  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def parse_script(script_text: str) -> list:
    """스크립트 텍스트를 파싱하여 문장 리스트로 변환"""
    import re

    lines = script_text.strip().split("\n")
    sentences = []
    in_body_section = False

    for line in lines:
        line = line.strip()

        # 섹션 마커 확인
        if line.startswith("[Script Body]") or line.startswith("[대본 본문]"):
            in_body_section = True
            continue
        elif line.startswith("[") and line.endswith("]"):
            # 다른 섹션 시작 시 본문 섹션 종료
            in_body_section = False
            continue

        # 기존 형식: VO: 또는 나레이션: 으로 시작하는 줄
        if line.startswith("**VO:**") or line.startswith("**나레이션:**"):
            # VO: 또는 나레이션: 제거
            text = line.replace("**VO:**", "").replace("**나레이션:**", "").strip()

            # 괄호 안의 지시사항 제거 (예: (윙크), (Visual: ...), (화면 연출: ...))
            text = re.sub(r"\([^)]*\)", "", text)

            # 대괄호 안의 지시사항도 제거 (예: [Visual: ...])
            text = re.sub(r"\[[^\]]*\]", "", text)

            # 공백 정리
            text = re.sub(r"\s+", " ", text).strip()

            if text:
                sentences.append(text)

        # 새로운 형식: [Script Body] 또는 [대본 본문] 섹션 안의 문장들
        elif in_body_section and line:
            # 괄호 안의 지시사항 제거
            text = re.sub(r"\([^)]*\)", "", line)

            # 대괄호 안의 지시사항도 제거
            text = re.sub(r"\[[^\]]*\]", "", text)

            # 공백 정리
            text = re.sub(r"\s+", " ", text).strip()

            # 빈 줄이 아니고 의미있는 문장인 경우만 추가
            if text and len(text) > 3:
                sentences.append(text)

    return sentences


def extract_title(script_text: str, language: str) -> str:
    """스크립트에서 제목 추출"""
    lines = script_text.strip().split("\n")

    if language == "en":
        title_markers = ["**[Title]**", "[Title]"]
    else:
        title_markers = ["**[제목]**", "[제목]"]

    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # 기존 형식 또는 새로운 형식 확인
        for marker in title_markers:
            if line_stripped == marker or line_stripped.startswith(marker + " "):
                if line_stripped.startswith(marker + " "):
                    # 새로운 형식: [Title] 제목 내용
                    title = line_stripped.replace(marker, "").strip()
                    # ** 제거
                    title = title.replace("**", "").strip()
                    return title
                elif i + 1 < len(lines):
                    # 기존 형식: 다음 줄에 제목
                    title = lines[i + 1].strip()
                    # ** 제거
                    title = title.replace("**", "").strip()
                    return title

    return None


def read_script_file(file_path: str) -> tuple:
    """스크립트 파일을 읽어서 영어와 한국어 스크립트 분리"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"스크립트 파일을 찾을 수 없습니다: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # |||SPLIT|||로 구분
    if "|||SPLIT|||" in content:
        parts = content.split("|||SPLIT|||")
        english_text = parts[0].strip()
        korean_text = parts[1].strip() if len(parts) > 1 else ""
    else:
        # 구분자가 없으면 전체를 영어로 간주
        english_text = content.strip()
        korean_text = ""

    return english_text, korean_text


def main():
    parser = argparse.ArgumentParser(
        description="사용자 제공 스크립트로 영상 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
스크립트 파일 형식:
  - 영어와 한국어 스크립트를 |||SPLIT|||로 구분
  - 각 언어별로 **[Title]** 또는 **[제목]** 섹션에 제목 포함
  - **[Hook]** 또는 **[후킹]**, **[Body]** 또는 **[본문]**, **[Outro]** 또는 **[결론]** 섹션에 **VO:** 또는 **나레이션:** 형식으로 문장 작성

예시:
  python create_from_custom_script.py script.txt
        """,
    )
    parser.add_argument(
        "script_file",
        type=str,
        help="스크립트 파일 경로 (|||SPLIT|||로 영어/한국어 구분)",
    )

    args = parser.parse_args()

    # 스크립트 파일 읽기
    try:
        english_text, korean_text = read_script_file(args.script_file)
    except Exception as e:
        logger.error(f"❌ 스크립트 파일 읽기 실패: {e}")
        return

    video_generator = AIVideoGenerator()

    # 영어 영상 생성
    if english_text:
        logger.info("=" * 60)
        logger.info("🇺🇸 영어 영상 생성 시작")
        logger.info("=" * 60)

        english_script = parse_script(english_text)
        english_topic = extract_title(english_text, "en")

        if not english_topic:
            logger.warning(
                "⚠️ 영어 제목을 찾을 수 없습니다. 첫 번째 문장을 제목으로 사용합니다."
            )
            english_topic = (
                english_script[0][:50] + "..." if english_script else "English Video"
            )

        logger.info(f"📌 제목: {english_topic}")
        logger.info(f"📝 파싱된 스크립트 ({len(english_script)}개 문장):")
        for i, sentence in enumerate(english_script, 1):
            logger.info(f"   {i}. {sentence}")

        try:
            result = video_generator.video_compositor.create_video_from_script(
                script=english_script,
                topic=english_topic,
                duration=None,  # 자동 계산 (실제 음성 길이 사용)
                output_filename=None,
                content_type=ContentType.AUTO,
                language="en",
                preferred_keywords=None,
            )

            if result:
                logger.info(f"✅ 영어 영상 생성 완료: {result}")
            else:
                logger.error("❌ 영어 영상 생성 실패")
        except Exception as e:
            logger.error(f"❌ 영어 영상 생성 중 오류: {e}", exc_info=True)

    # 한국어 영상 생성
    if korean_text:
        logger.info("")
        logger.info("=" * 60)
        logger.info("🇰🇷 한국어 영상 생성 시작")
        logger.info("=" * 60)

        korean_script = parse_script(korean_text)
        korean_topic = extract_title(korean_text, "ko")

        if not korean_topic:
            logger.warning(
                "⚠️ 한국어 제목을 찾을 수 없습니다. 첫 번째 문장을 제목으로 사용합니다."
            )
            korean_topic = (
                korean_script[0][:50] + "..." if korean_script else "한국어 영상"
            )

        logger.info(f"📌 제목: {korean_topic}")
        logger.info(f"📝 파싱된 스크립트 ({len(korean_script)}개 문장):")
        for i, sentence in enumerate(korean_script, 1):
            logger.info(f"   {i}. {sentence}")

        try:
            result = video_generator.video_compositor.create_video_from_script(
                script=korean_script,
                topic=korean_topic,
                duration=None,  # 자동 계산 (실제 음성 길이 사용)
                output_filename=None,
                content_type=ContentType.AUTO,
                language="ko",
                preferred_keywords=None,
            )

            if result:
                logger.info(f"✅ 한국어 영상 생성 완료: {result}")
            else:
                logger.error("❌ 한국어 영상 생성 실패")
        except Exception as e:
            logger.error(f"❌ 한국어 영상 생성 중 오류: {e}", exc_info=True)


if __name__ == "__main__":
    main()
