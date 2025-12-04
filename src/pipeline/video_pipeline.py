from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import json
from pathlib import Path
from src.core.config import settings
from src.generators.content_type import ContentType
from src.utils.logger import get_logger
from src.pipeline.metadata_manager import MetadataManager

logger = get_logger(__name__)

class VideoPipeline:
    """Encapsulates the video creation and upload workflow."""

    def __init__(
        self,
        video_generator,
        uploader,
        database,
        sync_manager,
        user_request_handler,
        notification_service,
        monetization_tracker,
        use_multi_platform: bool = False
    ):
        self.video_generator = video_generator
        self.uploader = uploader
        self.database = database
        self.sync_manager = sync_manager
        self.user_request_handler = user_request_handler
        self.notification_service = notification_service
        self.monetization = monetization_tracker
        self.use_multi_platform = use_multi_platform
        self.metadata_manager = MetadataManager()
        self._last_topic_source = None

    def run(
        self, 
        topic: str = None, 
        content_type: ContentType = None, 
        force: bool = False, 
        language: str = None, 
        auto_upload: bool = False
    ) -> Optional[str]:
        """Executes the full video pipeline: create -> upload -> notify."""
        try:
            content_type_name = content_type.value if content_type else "Auto"
            logger.info("="*50)
            logger.info(f"🚀 Starting Video Pipeline")
            logger.info(f"📌 Content Type: {content_type_name}")
            if force:
                logger.warning(f"⚠️ Force Mode: Skipping duplicate checks")
            logger.info("="*50)
            
            # 1. Check constraints
            if not self._check_constraints(force):
                return None
            
            # 2. Determine parameters
            topic, language, request_id = self._determine_parameters(topic, language)
            
            # 3. Get performance prompt
            performance_prompt = self._get_performance_prompt()
            
            # 4. Generate content
            video_assets = self._generate_content(topic, content_type, language, performance_prompt)
            
            # 5. User confirmation (if not auto)
            if not auto_upload:
                if not self._confirm_upload(video_assets):
                    return None
            
            # 6. Upload
            upload_results = self._upload(video_assets)
            
            # 7. Update DB & Logs
            self._update_records(video_assets, upload_results, request_id, content_type, performance_prompt)
            self._save_upload_log(video_assets, upload_results, content_type)
            
            video_id = upload_results.get('youtube')
            if video_id:
                logger.info(f"✅ Pipeline Complete! Video ID: {video_id}")
                logger.info(f"🔗 https://www.youtube.com/watch?v={video_id}")
                
                # 8. Notify
                self._notify(video_assets, video_id)
            
            # Report
            self.monetization.print_report()
            
            return video_id
            
        except Exception as e:
            logger.error(f"❌ Pipeline Error: {str(e)}", exc_info=True)
            return None

    def _check_constraints(self, force: bool) -> bool:
        """Checks upload constraints."""
        self.sync_manager.print_sync_status()
        
        if force:
            return True
            
        if self.sync_manager.check_today_uploaded():
            today_info = self.sync_manager.get_today_upload_info()
            logger.warning(f"⚠️ Already uploaded today (Local Check).")
            logger.info(f"   Video ID: {today_info.get('video_id', 'N/A')}")
            return False
        
        if not self.use_multi_platform:
            if hasattr(self.uploader, 'check_today_uploaded'):
                if self.uploader.check_today_uploaded():
                    logger.warning(f"⚠️ Already uploaded today (API Check).")
                    return False
                    
        return True

    def _determine_parameters(self, topic: str, language: str) -> Tuple[str, str, Optional[str]]:
        """Determines topic and language."""
        request_id = None
        
        # Language detection
        if language is None and topic:
            import re
            korean_chars = len(re.findall(r'[가-힣]', topic))
            total_chars = len(re.findall(r'[a-zA-Z가-힣]', topic))
            if total_chars > 0 and korean_chars / total_chars > 0.5:
                language = 'ko'
                logger.info(f"🌐 Detected Language: Korean (Topic: {topic})")
            else:
                language = 'en'
                logger.info(f"🌐 Detected Language: English (Topic: {topic})")
        elif language is None:
            language = 'en'
            logger.info(f"🌐 Default Language: English")
        
        # User request
        if not topic:
            user_request = self.user_request_handler.get_next_request()
            if user_request:
                topic = user_request['topic']
                request_id = user_request['id']
                logger.info(f"📝 Using User Request: {topic} (ID: {request_id})")
                self.user_request_handler.mark_in_progress(request_id)
                
        return topic, language, request_id

    def _get_performance_prompt(self) -> str:
        """Generates performance-based prompt."""
        try:
            top_videos = self.database.get_top_performing_videos(limit=3, days=30, min_views=50)
            top_topics = self.database.get_top_topics(limit=3, days=30)
            
            additions = []
            if top_topics:
                topics_text = ", ".join([t['topic'] for t in top_topics if t.get('topic')])
                if topics_text:
                    additions.append(f"Recent top topics: {topics_text}. Use similar style/tone but offer new perspectives.")
            
            if top_videos:
                avg_engagement = sum(v.get('engagement_rate', 0) for v in top_videos) / len(top_videos)
                if avg_engagement > 2.0:
                    additions.append("Recent high engagement features: Clear practical info, curiosity-inducing structure, actionable tips.")
            
            return "\n\n" + "\n".join(additions) if additions else ""
        except Exception as e:
            logger.warning(f"⚠️ Failed to get performance prompt: {e}")
            return ""

    def _generate_content(self, topic: str, content_type: ContentType, language: str, performance_prompt: str) -> Dict[str, Any]:
        """Generates video content."""
        logger.info("📹 Step 1: Generating Video Content...")
        result = self.video_generator.generate_video(
            topic=topic, 
            duration=None,
            performance_prompt=performance_prompt,
            content_type=content_type,
            language=language
        )
        
        # Parse result
        if len(result) == 4:
            video_path, thumbnail_path, generated_topic, script = result
            topic_source = None
        elif len(result) == 3:
            video_path, script, generated_topic = result
            thumbnail_path = None
            topic_source = None
        else:
            # Fallback for flexible return signatures
            video_path = result[0]
            thumbnail_path = result[1] if len(result) > 1 else None
            generated_topic = result[2] if len(result) > 2 else topic
            script = result[3] if len(result) > 3 else None
            topic_source = result[4] if len(result) > 4 else None
        
        if not video_path:
            raise Exception("Video generation failed")
            
        actual_topic = generated_topic if generated_topic else topic
        self._last_topic_source = topic_source # Store for DB update
        
        # Title
        title = self.metadata_manager.generate_title(topic, actual_topic)
        
        # Thumbnail Embedding
        if thumbnail_path:
            logger.info("🎞️ Embedding thumbnail...")
            self.video_generator.image_generator.embed_thumbnail_frame(video_path, thumbnail_path)
        
        # Description
        channel_info = getattr(self.uploader, 'get_channel_info', lambda: None)()
        recent_videos: list = getattr(self.uploader, 'get_recent_videos', lambda **k: [])(max_results=3)
        description = self.metadata_manager.generate_description(
            language, topic, actual_topic, channel_info, recent_videos
        )
        
        # Clean temp files
        try:
            from src.utils.temp_cleaner import TempCleaner
            TempCleaner(max_age_hours=1).clean_old_files()
        except Exception:
            pass
        
        return {
            'video_path': video_path,
            'thumbnail_path': thumbnail_path,
            'title': title,
            'description': description,
            'tags': settings.DEFAULT_TAGS,
            'actual_topic': actual_topic,
            'script': script,
            'topic_source': topic_source
        }

    def _confirm_upload(self, video_assets: Dict[str, Any]) -> bool:
        """Asks user for confirmation."""
        logger.info("="*60)
        logger.info("📋 Review Video Before Upload")
        logger.info("="*60)
        logger.info(f"Title: {video_assets.get('title')}")
        logger.info(f"Topic: {video_assets.get('actual_topic')}")
        logger.info(f"File: {video_assets.get('video_path')}")
        
        print(f"\nUpload to YouTube? (y/n): ", end='', flush=True)
        try:
            if input().strip().lower() not in ['y', 'yes', '예']:
                logger.info("❌ Upload Cancelled.")
                return False
        except (EOFError, KeyboardInterrupt):
            logger.info("❌ Upload Cancelled.")
            return False
            
        logger.info("✅ Proceeding with Upload...")
        return True

    def _upload(self, video_assets: Dict[str, Any]) -> Dict[str, str]:
        """Uploads to platforms."""
        logger.info("☁️ Step 2: Uploading to Platforms...")
        
        results = {}
        if self.use_multi_platform:
            results = self.uploader.upload_to_all(
                video_path=video_assets['video_path'],
                title=video_assets['title'],
                description=video_assets['description'],
                tags=video_assets['tags'],
                thumbnail_path=video_assets['thumbnail_path']
            )
        else:
            video_id = self.uploader.upload_video(
                video_path=video_assets['video_path'],
                title=video_assets['title'],
                description=video_assets['description'],
                tags=video_assets['tags'],
                privacy_status=settings.PRIVACY_STATUS,
                thumbnail_path=video_assets['thumbnail_path'],
                schedule_delay_hours=settings.UPLOAD_DELAY_HOURS
            )
            if video_id:
                results['youtube'] = video_id
                
        return results

    def _update_records(self, assets, upload_results, request_id, content_type, performance_prompt):
        """Updates database and sync manager."""
        video_id = upload_results.get('youtube')
        if not video_id:
            return
            
        # DB
        self.database.add_video(
            video_id=video_id,
            title=assets['title'],
            topic=assets['actual_topic'],
            video_path=assets['video_path'],
            privacy_status=settings.PRIVACY_STATUS,
            tags=assets['tags'],
            category_id=settings.CATEGORY_ID,
            language=settings.VIDEO_LANGUAGE,
            script=assets['script'],
            topic_source=self._last_topic_source
        )
        
        # Sync
        self.sync_manager.update_last_upload(video_id, assets['title'])
        
        # User Request
        if request_id:
            self.user_request_handler.mark_completed(request_id, video_id)
            
        # Monetization
        self.monetization.track_upload()

    def _notify(self, assets, video_id):
        """Sends notifications."""
        try:
            self.notification_service.send_upload_notification(
                video_title=assets['title'],
                video_url=f"https://www.youtube.com/watch?v={video_id}",
                thumbnail_url=None,
                topic=assets['actual_topic']
            )
        except Exception as e:
            logger.warning(f"⚠️ Notification failed: {e}")

    def _save_upload_log(self, video_assets: Dict[str, Any], upload_results: Dict[str, str], 
                        content_type: ContentType):
        """Saves upload log to file."""
        try:
            video_id = upload_results.get('youtube')
            if not video_id:
                return
            
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            log_file = data_dir / "upload_log.json"
            
            upload_logs = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        upload_logs = json.load(f)
                except:
                    upload_logs = []
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'video_id': video_id,
                'title': video_assets.get('title'),
                'topic': video_assets.get('actual_topic'),
                'content_type': content_type.value if content_type else 'auto',
                'video_path': video_assets.get('video_path'),
                'thumbnail_path': video_assets.get('thumbnail_path'),
                'upload_results': upload_results,
                'url': f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            }
            
            upload_logs.append(log_entry)
            if len(upload_logs) > 1000:
                upload_logs = upload_logs[-1000:]
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(upload_logs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Upload log saved: {log_file}")
            self._append_to_history(log_entry)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to save upload log: {e}", exc_info=True)
    
    def _append_to_history(self, log_entry: Dict[str, Any]):
        """Appends upload record to HISTORY.md."""
        try:
            history_file = Path("HISTORY.md")
            if not history_file.exists():
                return
            
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            upload_date = datetime.fromisoformat(log_entry['timestamp']).strftime('%Y-%m-%d')
            
            history_entry = f"""
- **{upload_date} - Video Uploaded**
  - **Title**: {log_entry.get('title', 'N/A')}
  - **Topic**: {log_entry.get('topic', 'N/A')}
  - **Type**: {log_entry.get('content_type', 'auto')}
  - **Video ID**: {log_entry.get('video_id', 'N/A')}
  - **URL**: {log_entry.get('url', 'N/A')}
"""
            
            # Simple append logic for now, or insert at top if possible
            # The original logic was complex regex. I'll simplify it to append to "Recent Updates" or top.
            if "## Recent Updates" in content:
                content = content.replace("## Recent Updates", f"## Recent Updates\n{history_entry}")
            elif "## 최근 업데이트" in content:
                content = content.replace("## 최근 업데이트", f"## 최근 업데이트\n{history_entry}")
            else:
                content = f"## Recent Updates\n{history_entry}\n\n" + content
            
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ Appended to HISTORY.md")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to append to history: {e}")
