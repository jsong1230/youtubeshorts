"""
최근 생성된 영상에 섬네일과 메타데이터 생성
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.pipeline.bot import ShortsBot  # noqa: E402
from src.core.config import settings  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def generate_metadata_for_video(
    video_path: str, topic: str, language: str, script: list
):
    """영상에 섬네일과 메타데이터 생성"""
    bot = ShortsBot()

    # 섬네일 생성
    logger.info(f"🖼️ 섬네일 생성 중: {video_path}")
    thumbnail_path = None
    try:
        thumbnail_path = bot.video_generator.image_generator.generate_thumbnail(
            video_path=video_path,
            title=topic,
            topic=topic,
            script=script,
            language=language,
        )
        if thumbnail_path:
            logger.info(f"✅ 섬네일 생성 완료: {thumbnail_path}")
        else:
            logger.warning("⚠️ 섬네일 생성 실패")
    except Exception as e:
        logger.warning(f"⚠️ 섬네일 생성 중 오류: {e}")

    # 제목 생성
    title = bot.pipeline.metadata_manager.generate_title(topic, topic)
    if "#Shorts" not in title and "#shorts" not in title:
        title = f"{title} #Shorts"

    # Description 생성
    description = bot.pipeline.metadata_manager.generate_description(
        language, topic, topic
    )

    # 메타데이터 저장
    video_basename = os.path.basename(video_path)
    video_name_without_ext = os.path.splitext(video_basename)[0]
    metadata_file = os.path.join(
        settings.VIDEO_OUTPUT_DIR, f"{video_name_without_ext}_metadata.json"
    )

    metadata = {
        "video_path": video_path,
        "thumbnail_path": thumbnail_path,
        "title": title,
        "topic": topic,
        "description": description,
        "tags": settings.DEFAULT_TAGS,
        "script": script,
        "language": language,
        "created_at": datetime.now().isoformat(),
    }

    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ 메타데이터 저장 완료: {metadata_file}")
    logger.info(f"📝 제목: {title}")
    logger.info(f"📌 주제: {topic}")

    return metadata_file


def main():
    # 최근 생성된 영상 파일 찾기
    video_dir = Path(settings.VIDEO_OUTPUT_DIR)
    video_files = sorted(
        video_dir.glob("shorts_*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True
    )

    if len(video_files) < 2:
        logger.error("❌ 최근 생성된 영상 2개를 찾을 수 없습니다.")
        return

    # 최근 2개 영상 (영문, 한글)
    en_video = video_files[0]  # 가장 최근
    ko_video = video_files[1]  # 두 번째

    # 스크립트 파일 읽기
    script_file = Path("test_script.txt")
    if not script_file.exists():
        logger.error(f"❌ 스크립트 파일을 찾을 수 없습니다: {script_file}")
        return

    with open(script_file, "r", encoding="utf-8") as f:
        content = f.read()

    if "|||SPLIT|||" in content:
        parts = content.split("|||SPLIT|||")
        english_text = parts[0].strip()
        korean_text = parts[1].strip() if len(parts) > 1 else ""
    else:
        logger.error("❌ 스크립트 파일에 |||SPLIT||| 구분자가 없습니다.")
        return

    # 제목 추출
    def extract_title(text, lang):
        lines = text.strip().split("\n")
        if lang == "en":
            markers = ["[Title]"]
        else:
            markers = ["[제목]"]

        for i, line in enumerate(lines):
            for marker in markers:
                if line.strip().startswith(marker):
                    if i + 1 < len(lines):
                        title = lines[i + 1].strip()
                        return title
        return None

    # 스크립트 파싱
    def parse_script(text):
        import re

        lines = text.strip().split("\n")
        sentences = []
        in_body = False

        for line in lines:
            line = line.strip()
            if line.startswith("[Script Body]") or line.startswith("[대본 본문]"):
                in_body = True
                continue
            elif line.startswith("[") and line.endswith("]"):
                in_body = False
                continue

            if in_body and line:
                text = re.sub(r"\([^)]*\)", "", line)
                text = re.sub(r"\[[^\]]*\]", "", text)
                text = re.sub(r"\s+", " ", text).strip()
                if text and len(text) > 3:
                    sentences.append(text)

        return sentences

    en_topic = (
        extract_title(english_text, "en")
        or "Entering Your Soft Life Era: Stop The Grind"
    )
    ko_topic = (
        extract_title(korean_text, "ko")
        or "갓생 살려면 칼퇴부터 해야지? AI 활용법 꿀팁"
    )

    en_script = parse_script(english_text)
    ko_script = parse_script(korean_text)

    # 영문 영상 메타데이터 생성
    logger.info("=" * 60)
    logger.info("🇺🇸 영문 영상 메타데이터 생성")
    logger.info("=" * 60)
    generate_metadata_for_video(str(en_video), en_topic, "en", en_script)

    # 한국어 영상 메타데이터 생성
    logger.info("")
    logger.info("=" * 60)
    logger.info("🇰🇷 한국어 영상 메타데이터 생성")
    logger.info("=" * 60)
    generate_metadata_for_video(str(ko_video), ko_topic, "ko", ko_script)

    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ 모든 메타데이터 생성 완료!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
