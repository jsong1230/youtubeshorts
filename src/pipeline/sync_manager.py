"""
멀티 컴퓨터 동기화 관리 모듈
두 컴퓨터 간 일관성을 유지하기 위한 동기화 및 상태 관리
"""

import os
import json
import socket
from datetime import datetime
from typing import Optional, Dict

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SyncManager:
    """멀티 컴퓨터 동기화 관리 클래스"""

    def __init__(self, state_file: str = "data/sync_state.json"):
        """
        동기화 관리자 초기화

        Args:
            state_file: 상태 파일 경로
        """
        self.state_file = state_file
        self.data_dir = os.path.dirname(state_file)
        if self.data_dir and not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        self._load_state()

    def _load_state(self):
        """상태 파일 로드"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 상태 파일 로드 실패: {e}")
                self.state = {}
        else:
            self.state = {}

    def _save_state(self):
        """상태 파일 저장"""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"⚠️ 상태 파일 저장 실패: {e}")

    def get_computer_id(self) -> str:
        """
        현재 컴퓨터 고유 ID 생성

        Returns:
            컴퓨터 ID (호스트명 기반)
        """
        try:
            hostname = socket.gethostname()
            return hostname
        except:
            return "unknown"

    def get_last_upload_info(self) -> Optional[Dict]:
        """
        마지막 업로드 정보 조회

        Returns:
            마지막 업로드 정보 또는 None
        """
        return self.state.get("last_upload")

    def record_upload(self, video_id: str, title: str, topic: str = None):
        """
        업로드 기록

        Args:
            video_id: YouTube 영상 ID
            title: 영상 제목
            topic: 영상 주제
        """
        computer_id = self.get_computer_id()
        now = datetime.now().isoformat()

        self.state["last_upload"] = {
            "video_id": video_id,
            "title": title,
            "topic": topic,
            "computer_id": computer_id,
            "upload_time": now,
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

        # 업로드 히스토리 추가 (최근 10개만 유지)
        if "upload_history" not in self.state:
            self.state["upload_history"] = []

        self.state["upload_history"].append(
            {
                "video_id": video_id,
                "title": title,
                "topic": topic,
                "computer_id": computer_id,
                "upload_time": now,
                "date": datetime.now().strftime("%Y-%m-%d"),
            }
        )

        # 최근 10개만 유지
        if len(self.state["upload_history"]) > 10:
            self.state["upload_history"] = self.state["upload_history"][-10:]

        self._save_state()

    def check_today_uploaded(self) -> bool:
        """
        오늘 업로드했는지 확인

        Returns:
            오늘 업로드했으면 True, 아니면 False
        """
        last_upload = self.get_last_upload_info()
        if not last_upload:
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        return last_upload.get("date") == today

    def get_today_upload_info(self) -> Optional[Dict]:
        """
        오늘 업로드한 영상 정보 조회

        Returns:
            오늘 업로드한 영상 정보 또는 None
        """
        if self.check_today_uploaded():
            return self.get_last_upload_info()
        return None

    def get_sync_status(self) -> Dict:
        """
        동기화 상태 조회

        Returns:
            동기화 상태 정보
        """
        last_upload = self.get_last_upload_info()
        computer_id = self.get_computer_id()

        status = {
            "current_computer": computer_id,
            "last_upload": last_upload,
            "today_uploaded": self.check_today_uploaded(),
            "upload_history_count": len(self.state.get("upload_history", [])),
        }

        return status

    def print_sync_status(self):
        """동기화 상태 출력"""
        status = self.get_sync_status()
        logger.info(f"\n{'='*60}")
        logger.info("🔄 동기화 상태")
        logger.info(f"{'='*60}")
        logger.info(f"현재 컴퓨터: {status['current_computer']}")
        logger.info(
            f"오늘 업로드 여부: {'✅ 예' if status['today_uploaded'] else '❌ 아니오'}"
        )

        if status["last_upload"]:
            last = status["last_upload"]
            logger.info("\n마지막 업로드:")
            logger.info(f"  - 영상 ID: {last.get('video_id', 'N/A')}")
            logger.info(f"  - 제목: {last.get('title', 'N/A')}")
            logger.info(f"  - 주제: {last.get('topic', 'N/A')}")
            logger.info(f"  - 컴퓨터: {last.get('computer_id', 'N/A')}")
            logger.info(f"  - 시간: {last.get('upload_time', 'N/A')}")
        else:
            logger.info("\n마지막 업로드: 없음")

        logger.info(f"{'='*60}\n")
