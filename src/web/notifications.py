"""
알림 시스템
이메일, 슬랙 등 다양한 채널을 통한 알림 전송
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List
import requests

from src.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationService:
    """알림 서비스 클래스"""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.notification_email = os.getenv("NOTIFICATION_EMAIL", "")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
        self.enable_email = (
            os.getenv("ENABLE_EMAIL_NOTIFICATIONS", "false").lower() == "true"
        )
        self.enable_slack = (
            os.getenv("ENABLE_SLACK_NOTIFICATIONS", "false").lower() == "true"
        )

    def send_email(self, subject: str, body: str, to_email: str = None) -> bool:
        """
        이메일 알림 전송

        Args:
            subject: 이메일 제목
            body: 이메일 본문
            to_email: 수신자 이메일 (None이면 기본 알림 이메일 사용)

        Returns:
            성공 여부
        """
        if not self.enable_email or not self.smtp_user or not self.smtp_password:
            return False

        try:
            to_email = to_email or self.notification_email
            if not to_email:
                return False

            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "html"))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            logger.warning(f"⚠️ 이메일 전송 실패: {e}")
            return False

    def send_slack(
        self, message: str, channel: str = None, attachments: List[Dict] = None
    ) -> bool:
        """
        Slack 알림 전송

        Args:
            message: 메시지 내용
            channel: 채널 이름 (선택)
            attachments: 첨부 정보 (선택)

        Returns:
            성공 여부
        """
        if not self.enable_slack or not self.slack_webhook_url:
            return False

        try:
            payload = {"text": message, "channel": channel}

            if attachments:
                payload["attachments"] = attachments  # type: ignore[assignment]

            response = requests.post(self.slack_webhook_url, json=payload)
            response.raise_for_status()

            return True
        except Exception as e:
            logger.warning(f"⚠️ Slack 전송 실패: {e}")
            return False

    def notify_video_uploaded(self, video_id: str, title: str, video_url: str) -> bool:
        """
        영상 업로드 완료 알림

        Args:
            video_id: YouTube 영상 ID
            title: 영상 제목
            video_url: 영상 URL

        Returns:
            성공 여부
        """
        subject = f"✅ 영상 업로드 완료: {title}"
        body = f"""
        <h2>영상 업로드가 완료되었습니다!</h2>
        <p><strong>제목:</strong> {title}</p>
        <p><strong>영상 ID:</strong> {video_id}</p>
        <p><strong>URL:</strong> <a href="{video_url}">{video_url}</a></p>
        <p><strong>업로드 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """

        slack_message = f"✅ 영상 업로드 완료: {title}\n{video_url}"

        email_sent = self.send_email(subject, body)
        slack_sent = self.send_slack(slack_message)

        return email_sent or slack_sent

    def notify_upload_failed(self, title: str, error: str) -> bool:
        """
        영상 업로드 실패 알림

        Args:
            title: 영상 제목
            error: 에러 메시지

        Returns:
            성공 여부
        """
        subject = f"❌ 영상 업로드 실패: {title}"
        body = f"""
        <h2>영상 업로드가 실패했습니다.</h2>
        <p><strong>제목:</strong> {title}</p>
        <p><strong>에러:</strong> {error}</p>
        <p><strong>실패 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """

        slack_message = f"❌ 영상 업로드 실패: {title}\n에러: {error}"

        email_sent = self.send_email(subject, body)
        slack_sent = self.send_slack(slack_message)

        return email_sent or slack_sent

    def notify_daily_summary(self, stats: Dict) -> bool:
        """
        일일 요약 알림

        Args:
            stats: 통계 데이터 (total_views, total_likes, total_comments, new_videos 등)

        Returns:
            성공 여부
        """
        subject = f"📊 일일 요약 - {datetime.now().strftime('%Y-%m-%d')}"
        body = f"""
        <h2>일일 요약 리포트</h2>
        <p><strong>날짜:</strong> {datetime.now().strftime('%Y년 %m월 %d일')}</p>
        <h3>통계</h3>
        <ul>
            <li>총 조회수: {stats.get('total_views', 0):,}</li>
            <li>총 좋아요: {stats.get('total_likes', 0):,}</li>
            <li>총 댓글: {stats.get('total_comments', 0):,}</li>
            <li>새 영상: {stats.get('new_videos', 0)}개</li>
        </ul>
        """

        slack_message = f"""
📊 일일 요약 - {datetime.now().strftime('%Y-%m-%d')}
총 조회수: {stats.get('total_views', 0):,}
총 좋아요: {stats.get('total_likes', 0):,}
총 댓글: {stats.get('total_comments', 0):,}
새 영상: {stats.get('new_videos', 0)}개
        """

        email_sent = self.send_email(subject, body)
        slack_sent = self.send_slack(slack_message)

        return email_sent or slack_sent

    def notify_milestone(self, milestone_type: str, value: int) -> bool:
        """
        마일스톤 달성 알림

        Args:
            milestone_type: 마일스톤 타입 ('views', 'subscribers', 'videos' 등)
            value: 달성한 값

        Returns:
            성공 여부
        """
        milestones = {
            "views": {
                1000: "1,000 조회수 달성! 🎉",
                10000: "10,000 조회수 달성! 🎉🎉",
                100000: "100,000 조회수 달성! 🎉🎉🎉",
            },
            "subscribers": {
                100: "100 구독자 달성! 🎉",
                1000: "1,000 구독자 달성! 🎉🎉",
                10000: "10,000 구독자 달성! 🎉🎉🎉",
            },
            "videos": {
                10: "10개 영상 업로드 달성! 🎉",
                50: "50개 영상 업로드 달성! 🎉🎉",
                100: "100개 영상 업로드 달성! 🎉🎉🎉",
            },
        }

        milestone_map = milestones.get(milestone_type, {})
        milestone_text = None

        for threshold, text in sorted(milestone_map.items(), reverse=True):
            if value >= threshold:
                milestone_text = text
                break

        if not milestone_text:
            return False

        subject = f"🎉 마일스톤 달성: {milestone_text}"
        body = f"""
        <h2>{milestone_text}</h2>
        <p><strong>{milestone_type.upper()}:</strong> {value:,}</p>
        <p><strong>달성 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """

        slack_message = f"🎉 {milestone_text}\n{milestone_type.upper()}: {value:,}"

        email_sent = self.send_email(subject, body)
        slack_sent = self.send_slack(slack_message)

        return email_sent or slack_sent
