"""
웹 대시보드 및 API 서버
실시간 통계, 리포트, 설정 관리
"""

from flask import Flask, render_template, jsonify, request
import os
import json
from datetime import datetime, timedelta

from src.core.config import settings
from src.pipeline.database import VideoDatabase
from src.analytics.monetization import MonetizationTracker
from src.analytics.ab_testing import ABTestDatabase
from src.analytics.thumbnail_optimizer import ThumbnailOptimizer
from src.analytics.advanced_analytics import AutoOptimizer, AudienceSegmentAnalyzer
from src.pipeline.topic_database import TopicDatabase
from src.generators.series_generator import SeriesGenerator, SeriesType
from src.generators.user_request_handler import UserRequestHandler
from src.analytics.comment_analyzer import CommentAnalyzer


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY", "dev-secret-key-change-in-production"
)


# 전역 데이터베이스 인스턴스
video_db = VideoDatabase()
monetization = MonetizationTracker()
ab_test_db = ABTestDatabase()
thumbnail_optimizer = ThumbnailOptimizer()
auto_optimizer = AutoOptimizer()
audience_segment_analyzer = AudienceSegmentAnalyzer()
topic_db = TopicDatabase()
series_generator = SeriesGenerator()
user_request_handler = UserRequestHandler()
comment_analyzer = CommentAnalyzer()


@app.route("/")
def index():
    """메인 대시보드 페이지"""
    return render_template("dashboard.html")


@app.route("/api/stats/overview")
def get_overview_stats():
    """전체 통계 개요"""
    try:
        # 최근 30일 데이터
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()

        # 영상 통계 (모든 영상 조회)
        videos = video_db.get_all_videos(limit=None, days=None, order_by="upload_date")
        total_videos = len(videos)
        total_views = sum(v.get("views", 0) for v in videos)
        total_likes = sum(v.get("likes", 0) for v in videos)
        total_comments = sum(v.get("comments", 0) for v in videos)
        avg_engagement_rate = (
            sum(v.get("engagement_rate", 0) for v in videos) / total_videos
            if total_videos > 0
            else 0
        )

        # 수익화 통계
        monetization_data = monetization.data
        total_revenue = monetization_data.get("stats", {}).get("total_revenue", 0)
        subscriber_count = monetization_data.get("stats", {}).get("subscriber_count", 0)

        # 최근 7일 성장률
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        week_videos = [v for v in videos if v.get("upload_date", "") >= week_ago]
        week_views = sum(v.get("views", 0) for v in week_videos)

        return jsonify(
            {
                "success": True,
                "data": {
                    "videos": {
                        "total": total_videos,
                        "total_views": total_views,
                        "total_likes": total_likes,
                        "total_comments": total_comments,
                        "avg_engagement_rate": round(avg_engagement_rate, 2),
                        "week_views": week_views,
                    },
                    "monetization": {
                        "total_revenue": total_revenue,
                        "subscriber_count": subscriber_count,
                    },
                    "last_updated": datetime.now().isoformat(),
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats/videos")
def get_video_stats():
    """영상별 통계"""
    try:
        days_str = request.args.get("days")
        limit_str = request.args.get("limit")
        order_by = request.args.get("order_by", "upload_date")

        # days와 limit을 int로 변환 (None이면 그대로 유지)
        days: int | None = int(days_str) if days_str else None
        limit: int | None = int(limit_str) if limit_str else None

        # 모든 영상 조회 (필터 없이)
        videos = video_db.get_all_videos(limit=limit, days=days, order_by=order_by)

        return jsonify({"success": True, "data": videos, "count": len(videos)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats/topics")
def get_topic_stats():
    """주제별 통계"""
    try:
        days = int(request.args.get("days", 30))

        # 주제별 성과 데이터
        topics = topic_db.get_topics(status="active", limit=50)
        topic_stats = []

        for topic in topics:
            topic_videos = topic_db.get_videos_by_topic(topic["topic"])
            if topic_videos:
                views = [v.get("views", 0) for v in topic_videos]
                engagement_rates = [v.get("engagement_rate", 0) for v in topic_videos]

                topic_stats.append(
                    {
                        "topic": topic["topic"],
                        "content_type": topic["content_type"],
                        "video_count": len(topic_videos),
                        "total_views": sum(views),
                        "avg_views": sum(views) / len(views) if views else 0,
                        "avg_engagement_rate": (
                            sum(engagement_rates) / len(engagement_rates)
                            if engagement_rates
                            else 0
                        ),
                    }
                )

        # 평균 조회수 순으로 정렬
        topic_stats.sort(key=lambda x: x["avg_views"], reverse=True)

        return jsonify(
            {"success": True, "data": topic_stats, "count": len(topic_stats)}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats/ab-testing")
def get_ab_testing_stats():
    """A/B 테스트 통계"""
    try:
        days = int(request.args.get("days", 30))

        performance = ab_test_db.get_style_performance(days=days, min_views=50)

        return jsonify(
            {"success": True, "data": performance, "count": len(performance)}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats/thumbnails")
def get_thumbnail_stats():
    """썸네일 통계"""
    try:
        days = int(request.args.get("days", 30))

        performance = thumbnail_optimizer.get_thumbnail_performance(
            days=days, min_impressions=100
        )

        return jsonify(
            {"success": True, "data": performance, "count": len(performance)}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/optimization/recommendations")
def get_optimization_recommendations():
    """최적화 권장사항"""
    try:
        recommendations = auto_optimizer.get_optimization_recommendations()

        return jsonify({"success": True, "data": recommendations})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analytics/audience-segments")
def get_audience_segments():
    """시청자 세그먼트 분석"""
    try:
        days = int(request.args.get("days", 30))

        segments = audience_segment_analyzer.analyze_audience_segments(days=days)

        return jsonify({"success": True, "data": segments})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings")
def get_settings():
    """설정 조회"""
    try:
        settings_data = {
            "upload_schedule_time": settings.UPLOAD_SCHEDULE_TIME,
            "upload_timezone": settings.UPLOAD_TIMEZONE,
            "use_background_music": settings.USE_BACKGROUND_MUSIC,
            "background_music_volume": settings.BACKGROUND_MUSIC_VOLUME,
            "subtitle_mode": settings.SUBTITLE_MODE,
            "trend_mode": settings.TREND_MODE,
            "ai_api_provider": settings.AI_API_PROVIDER,
            "tts_provider": settings.TTS_PROVIDER,
        }

        return jsonify({"success": True, "data": settings_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """설정 업데이트"""
    try:
        data = request.json

        # .env 파일 업데이트 (실제 구현 시 주의 필요)
        # 여기서는 JSON 파일로 설정 저장
        settings_file = "data/settings.json"
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)

        # 기존 설정 로드
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                settings = json.load(f)
        else:
            settings = {}

        # 새 설정 업데이트
        settings.update(data)
        settings["updated_at"] = datetime.now().isoformat()

        # 저장
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)

        return jsonify(
            {
                "success": True,
                "message": "Settings updated successfully",
                "data": settings,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health")
def health_check():
    """헬스 체크"""
    return jsonify(
        {"success": True, "status": "healthy", "timestamp": datetime.now().isoformat()}
    )


@app.route("/api/content/series/generate", methods=["POST"])
def generate_series():
    """시리즈 콘텐츠 주제 생성"""
    try:
        data = request.json
        main_topic = data.get("main_topic")
        series_type = data.get("series_type", "sequential")
        num_episodes = int(data.get("num_episodes", 5))
        content_type = data.get("content_type", "auto")

        if not main_topic:
            return jsonify({"success": False, "error": "main_topic is required"}), 400

        # SeriesType 변환
        try:
            series_type_enum = SeriesType(series_type)
        except ValueError:
            series_type_enum = SeriesType.SEQUENTIAL

        # ContentType 변환
        from src.generators.content_type import ContentType

        try:
            content_type_enum = ContentType(content_type.lower())
        except ValueError:
            content_type_enum = ContentType.AUTO

        # 시리즈 주제 생성
        series_topics = series_generator.generate_series_topics(
            main_topic=main_topic,
            series_type=series_type_enum,
            num_episodes=num_episodes,
            content_type=content_type_enum,
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "main_topic": main_topic,
                    "series_type": series_type,
                    "num_episodes": num_episodes,
                    "topics": series_topics,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/content/user-requests", methods=["GET", "POST"])
def handle_user_requests():
    """사용자 요청 주제 관리"""
    try:
        if request.method == "GET":
            # 요청 목록 조회
            status = request.args.get("status", "pending")
            limit = int(request.args.get("limit", 20))

            if status == "pending":
                requests = user_request_handler.get_pending_requests(limit=limit)
            else:
                # 모든 요청 조회 (간단한 구현)
                requests = user_request_handler.get_pending_requests(limit=limit)

            return jsonify({"success": True, "data": requests, "count": len(requests)})
        else:
            # 새 요청 추가
            data = request.json
            topic = data.get("topic")
            source = data.get("source", "manual")
            priority = int(data.get("priority", 5))
            requested_by = data.get("requested_by")
            notes = data.get("notes")

            if not topic:
                return jsonify({"success": False, "error": "topic is required"}), 400

            request_id = user_request_handler.add_request(
                topic=topic,
                source=source,
                priority=priority,
                requested_by=requested_by,
                notes=notes,
            )

            return jsonify({"success": True, "data": {"request_id": request_id}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/content/user-requests/<int:request_id>/approve", methods=["POST"])
def approve_user_request(request_id):
    """사용자 요청 승인"""
    try:
        success = user_request_handler.approve_request(request_id)
        if success:
            return jsonify({"success": True})
        else:
            return (
                jsonify({"success": False, "error": "Failed to approve request"}),
                500,
            )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/content/comments/analyze", methods=["POST"])
def analyze_comments():
    """댓글 분석 및 주제 제안"""
    try:
        data = request.json
        video_id = data.get("video_id")
        num_videos = int(data.get("num_videos", 10))

        if video_id:
            # 특정 영상 댓글 분석
            result = comment_analyzer.analyze_video_comments(video_id)
        else:
            # 최근 영상들 댓글 분석
            result = comment_analyzer.analyze_recent_videos_comments(
                num_videos=num_videos
            )

        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# 템플릿 폴더 설정 (모듈 로드 시 설정)
template_dir = os.path.join(os.path.dirname(__file__), "templates")
static_dir = os.path.join(os.path.dirname(__file__), "static")

app.template_folder = template_dir
app.static_folder = static_dir

# 템플릿 폴더가 없으면 생성
os.makedirs(template_dir, exist_ok=True)
os.makedirs(static_dir, exist_ok=True)

if __name__ == "__main__":
    # 개발 서버 실행
    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    port = int(os.getenv("DASHBOARD_PORT", "5001"))
    logger.info(f"🚀 대시보드 서버 시작: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
