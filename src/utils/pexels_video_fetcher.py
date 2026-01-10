"""
Pexels Video API를 사용하여 중복 없는 최신 비디오를 가져오는 유틸리티 모듈

이 모듈은 Pexels API를 사용하여:
- 최신 비디오를 우선적으로 가져옵니다 (sort='newest')
- 사용된 비디오 ID를 추적하여 중복을 방지합니다
- 포트레이트 오리엔테이션을 기본값으로 사용합니다 (Shorts용)

사용 방법:
    from src.utils.pexels_video_fetcher import get_unique_pexels_videos

    videos = get_unique_pexels_videos("Luxury car", count=3)
    for video in videos:
        print(f"Video URL: {video['url']}, ID: {video['id']}")

Pexels API 키 설정:
    1. https://www.pexels.com/api/ 에서 계정 생성
    2. API 키 발급
    3. .env 파일에 PEXELS_API_KEY=your_api_key_here 추가
"""

import json
import requests
from typing import List, Dict, Set, Any
from pathlib import Path
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 사용된 비디오 ID를 저장할 JSON 파일 경로
USED_VIDEOS_FILE = Path(__file__).parent.parent.parent / "data" / "used_video_ids.json"


def _load_used_video_ids() -> Set[int]:
    """
    사용된 비디오 ID 목록을 JSON 파일에서 로드

    Returns:
        사용된 비디오 ID의 집합
    """
    if not USED_VIDEOS_FILE.exists():
        return set()

    try:
        with open(USED_VIDEOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 리스트나 딕셔너리 형태일 수 있으므로 처리
            if isinstance(data, list):
                return set(data)
            elif isinstance(data, dict) and "video_ids" in data:
                return set(data["video_ids"])
            else:
                return set()
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"⚠️ 사용된 비디오 ID 파일 읽기 실패: {e}. 새로 시작합니다.")
        return set()


def _save_used_video_ids(video_ids: Set[int]) -> None:
    """
    사용된 비디오 ID 목록을 JSON 파일에 저장

    Args:
        video_ids: 저장할 비디오 ID 집합
    """
    # data 디렉토리가 없으면 생성
    USED_VIDEOS_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 기존 데이터와 병합
        existing_ids = _load_used_video_ids()
        all_ids = existing_ids | video_ids

        # JSON 파일에 저장 (리스트 형태로 저장)
        with open(USED_VIDEOS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"video_ids": list(all_ids), "total_count": len(all_ids)}, f, indent=2
            )

        logger.debug(
            f"✅ 사용된 비디오 ID {len(video_ids)}개 저장 완료 (총 {len(all_ids)}개)"
        )
    except IOError as e:
        logger.error(f"❌ 사용된 비디오 ID 파일 저장 실패: {e}")


def _add_video_id(video_id: int) -> None:
    """
    단일 비디오 ID를 사용된 목록에 추가

    Args:
        video_id: 추가할 비디오 ID
    """
    existing_ids = _load_used_video_ids()
    if video_id not in existing_ids:
        existing_ids.add(video_id)
        _save_used_video_ids({video_id})  # 새로 추가된 ID만 저장 (기존과 병합됨)


def get_unique_pexels_videos(
    query: str,
    count: int = 1,
    orientation: str = "portrait",
    max_pages: int = 10,
) -> List[Dict[str, Any]]:
    """
    Pexels API에서 중복 없는 최신 비디오를 가져옵니다.

    Args:
        query: 검색 키워드 (예: "Luxury car", "Morning study", "Rainy window")
        count: 가져올 비디오 개수 (기본값: 1)
        orientation: 비디오 방향 ('portrait', 'landscape', 'square', 기본값: 'portrait')
        max_pages: 최대 검색할 페이지 수 (기본값: 10, 각 페이지당 최대 80개)

    Returns:
        비디오 정보 딕셔너리 리스트. 각 딕셔너리는 다음 키를 포함:
        - 'id': 비디오 ID
        - 'url': 비디오 URL (다운로드용)
        - 'thumbnail': 썸네일 URL
        - 'duration': 비디오 길이 (초)
        - 'width': 비디오 너비
        - 'height': 비디오 높이
        - 'photographer': 제작자 이름

    Raises:
        ValueError: API 키가 설정되지 않은 경우
        requests.RequestException: API 요청 실패 시

    Example:
        >>> videos = get_unique_pexels_videos("Luxury car", count=3)
        >>> for video in videos:
        ...     print(f"Video ID: {video['id']}, URL: {video['url']}")
    """
    # API 키 확인
    api_key = settings.PEXELS_API_KEY
    if not api_key:
        raise ValueError(
            "PEXELS_API_KEY가 설정되지 않았습니다. "
            ".env 파일에 PEXELS_API_KEY=your_api_key_here를 추가하세요. "
            "API 키는 https://www.pexels.com/api/ 에서 발급받을 수 있습니다."
        )

    # 사용된 비디오 ID 로드
    used_video_ids = _load_used_video_ids()
    logger.info(f"📋 이미 사용된 비디오 ID: {len(used_video_ids)}개")

    # 결과 리스트
    unique_videos: List[Dict[str, Any]] = []

    # 페이지네이션을 위한 변수
    page = 1
    per_page = 80  # Pexels API 최대값

    # API 엔드포인트
    base_url = "https://api.pexels.com/v1/videos/search"

    # 헤더 설정
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    logger.info(f"🔍 Pexels에서 '{query}' 검색 중... (최신순 정렬)")

    while len(unique_videos) < count and page <= max_pages:
        # API 파라미터 설정
        params: Dict[str, Any] = {
            "query": query,
            "per_page": per_page,
            "page": page,
            "orientation": orientation,
            "sort": "newest",  # 중요: 최신순 정렬
        }

        try:
            # API 요청
            response = requests.get(
                base_url, params=params, headers=headers, timeout=10  # type: ignore[arg-type]
            )
            response.raise_for_status()

            data = response.json()
            videos = data.get("videos", [])

            if not videos:
                logger.warning(
                    f"⚠️ 페이지 {page}에서 더 이상 비디오를 찾을 수 없습니다."
                )
                break

            logger.info(f"📄 페이지 {page}: {len(videos)}개 비디오 발견")

            # 각 비디오 확인
            for video in videos:
                video_id = video.get("id")

                # 비디오 ID가 없으면 건너뛰기
                if not video_id:
                    continue

                # 이미 사용된 비디오인지 확인
                if video_id in used_video_ids:
                    logger.debug(f"   ⏭️ 비디오 ID {video_id}는 이미 사용됨 (건너뜀)")
                    continue

                # 비디오 파일 정보 추출
                video_files = video.get("video_files", [])
                if not video_files:
                    continue

                # 포트레이트 오리엔테이션에 맞는 비디오 파일 찾기
                # quality가 높은 순서로 정렬하여 최고 품질 선택
                video_files_sorted = sorted(
                    video_files,
                    key=lambda x: (
                        x.get("width", 0) * x.get("height", 0),  # 해상도
                        x.get("fps", 0),  # FPS
                    ),
                    reverse=True,
                )

                # 포트레이트 비디오 우선 선택
                selected_file = None
                for vf in video_files_sorted:
                    if orientation == "portrait":
                        # 세로가 가로보다 긴 비디오
                        if vf.get("height", 0) > vf.get("width", 0):
                            selected_file = vf
                            break
                    elif orientation == "landscape":
                        # 가로가 세로보다 긴 비디오
                        if vf.get("width", 0) > vf.get("height", 0):
                            selected_file = vf
                            break
                    else:
                        # square 또는 기타: 첫 번째 파일 사용
                        selected_file = vf
                        break

                # 적합한 파일이 없으면 첫 번째 파일 사용
                if not selected_file:
                    selected_file = video_files_sorted[0]

                # 비디오 정보 구성
                video_info = {
                    "id": video_id,
                    "url": selected_file.get("link"),
                    "thumbnail": video.get("image"),
                    "duration": video.get("duration", 0),
                    "width": selected_file.get("width", 0),
                    "height": selected_file.get("height", 0),
                    "photographer": video.get("user", {}).get("name", "Unknown"),
                    "photographer_url": video.get("user", {}).get("url", ""),
                }

                # 사용된 비디오 ID에 추가
                _add_video_id(video_id)
                used_video_ids.add(video_id)

                # 결과에 추가
                unique_videos.append(video_info)
                logger.info(
                    f"   ✅ 비디오 ID {video_id} 추가됨 "
                    f"({video_info['width']}x{video_info['height']}, "
                    f"{video_info['duration']}초)"
                )

                # 필요한 개수만큼 찾았으면 종료
                if len(unique_videos) >= count:
                    break

            # 다음 페이지로
            page += 1

            # API 응답에 다음 페이지가 있는지 확인
            if page > data.get("page", 1) and len(videos) < per_page:
                logger.info("📄 마지막 페이지에 도달했습니다.")
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Pexels API 요청 실패 (페이지 {page}): {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"   응답 코드: {e.response.status_code}")
                logger.error(f"   응답 내용: {e.response.text[:200]}")
            break
        except Exception as e:
            logger.error(
                f"❌ 예상치 못한 오류 발생 (페이지 {page}): {e}", exc_info=True
            )
            break

    # 결과 요약
    if unique_videos:
        logger.info(
            f"✅ 총 {len(unique_videos)}개의 고유 비디오를 찾았습니다. "
            f"(검색어: '{query}', {page-1}페이지 검색)"
        )
    else:
        logger.warning(
            f"⚠️ '{query}'에 대한 고유 비디오를 찾을 수 없습니다. "
            f"다른 키워드를 시도하거나 used_video_ids.json을 초기화하세요."
        )

    return unique_videos


def reset_used_video_ids() -> None:
    """
    사용된 비디오 ID 목록을 초기화합니다.
    주의: 이 함수를 호출하면 모든 사용 기록이 삭제됩니다.
    """
    if USED_VIDEOS_FILE.exists():
        USED_VIDEOS_FILE.unlink()
        logger.info("🗑️ 사용된 비디오 ID 목록이 초기화되었습니다.")
    else:
        logger.info("ℹ️ 초기화할 사용 기록이 없습니다.")


def get_used_video_count() -> int:
    """
    현재 사용된 비디오 ID 개수를 반환합니다.

    Returns:
        사용된 비디오 ID 개수
    """
    return len(_load_used_video_ids())


if __name__ == "__main__":
    # 테스트 코드
    import sys

    if len(sys.argv) < 2:
        print("사용법: python pexels_video_fetcher.py <검색어> [개수]")
        print("예: python pexels_video_fetcher.py 'Luxury car' 3")
        sys.exit(1)

    query = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    try:
        videos = get_unique_pexels_videos(query, count=count)
        print(f"\n{'='*60}")
        print(f"검색 결과: {len(videos)}개 비디오")
        print(f"{'='*60}\n")

        for i, video in enumerate(videos, 1):
            print(f"{i}. 비디오 ID: {video['id']}")
            print(f"   URL: {video['url']}")
            print(f"   해상도: {video['width']}x{video['height']}")
            print(f"   길이: {video['duration']}초")
            print(f"   제작자: {video['photographer']}")
            print()

        print(f"총 사용된 비디오 ID: {get_used_video_count()}개")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)
