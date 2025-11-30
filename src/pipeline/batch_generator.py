"""
Batch video generation with sequential processing
"""
import time
from typing import List, Optional, Dict, Any

from src.pipeline.bot import ShortsBot
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BatchVideoGenerator:
    """순차 영상 생성 관리자"""
    
    def __init__(self, max_workers: int = 1):
        """
        Args:
            max_workers: 호환성을 위한 파라미터 (사용하지 않음, 순차 처리)
        """
        self.max_workers = 1  # 순차 처리만 지원
        self.results = []
        
    def generate_batch(
        self, 
        count: int, 
        topics: Optional[List[str]] = None,
        upload: bool = False,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        여러 영상을 순차적으로 생성
        
        Args:
            count: 생성할 영상 개수
            topics: 주제 리스트 (None이면 자동 생성)
            upload: 생성 후 업로드 여부
            force: 강제 업로드 (중복 체크 건너뛰기)
            
        Returns:
            결과 딕셔너리 (성공/실패 개수, 소요 시간 등)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 순차 영상 생성 시작")
        logger.info(f"{'='*60}")
        logger.info(f"📊 생성할 영상 개수: {count}")
        logger.info(f"📤 업로드 여부: {'예' if upload else '아니오'}")
        logger.info(f"{'='*60}\n")
        
        start_time = time.time()
        self.results = []
        
        # 주제 준비
        if topics:
            if len(topics) < count:
                logger.warning(f"⚠️ 주제가 부족합니다 ({len(topics)} < {count}). 나머지는 자동 생성됩니다.")
                topics = topics + [None] * (count - len(topics))
        else:
            topics = [None] * count
        
        # 순차 실행
        for i in range(count):
            topic = topics[i] if i < len(topics) else None
            index = i + 1
            
            try:
                result = self._generate_single_video(
                    index=index,
                    topic=topic,
                    upload=upload,
                    force=force
                )
                self.results.append(result)
                
                if result['success']:
                    logger.info(f"\n✅ [{index}/{count}] 영상 #{index} 생성 완료")
                    if result.get('video_path'):
                        logger.info(f"   📹 경로: {result['video_path']}")
                    if result.get('video_id'):
                        logger.info(f"   🎬 YouTube ID: {result['video_id']}")
                else:
                    logger.error(f"\n❌ [{index}/{count}] 영상 #{index} 생성 실패")
                    logger.error(f"   오류: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"\n❌ [{index}/{count}] 영상 #{index} 예외 발생: {e}", exc_info=True)
                self.results.append({
                    'index': index,
                    'success': False,
                    'error': str(e)
                })
        
        # 결과 집계
        end_time = time.time()
        duration = end_time - start_time
        
        success_count = sum(1 for r in self.results if r['success'])
        failure_count = count - success_count
        
        # 결과 출력
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 순차 생성 완료")
        logger.info(f"{'='*60}")
        logger.info(f"✅ 성공: {success_count}/{count}")
        logger.info(f"❌ 실패: {failure_count}/{count}")
        logger.info(f"⏱️  총 소요 시간: {duration:.1f}초 ({duration/60:.1f}분)")
        logger.info(f"⚡ 평균 시간/영상: {duration/count:.1f}초")
        
        if success_count > 0:
            logger.info(f"\n생성된 영상:")
            for r in self.results:
                if r['success'] and r.get('video_path'):
                    logger.info(f"  - {r['video_path']}")
        
        logger.info(f"{'='*60}\n")
        
        return {
            'total': count,
            'success': success_count,
            'failure': failure_count,
            'duration': duration,
            'results': self.results
        }
    
    def _generate_single_video(
        self,
        index: int,
        topic: Optional[str] = None,
        upload: bool = False,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        단일 영상 생성 (순차 실행)
        
        Args:
            index: 영상 번호
            topic: 주제
            upload: 업로드 여부
            force: 강제 업로드
            
        Returns:
            결과 딕셔너리
        """
        try:
            logger.info(f"\n🎬 영상 #{index} 생성 시작... (주제: {topic or '자동 생성'})")
            
            # ShortsBot 인스턴스 생성
            bot = ShortsBot()
            
            if upload:
                # 생성 및 업로드
                result = bot.create_and_upload(topic=topic, force=force)
                return {
                    'index': index,
                    'success': True,
                    'video_path': result.get('video_path'),
                    'video_id': result.get('video_id'),
                    'topic': result.get('topic')
                }
            else:
                # 생성만 (create_video_only는 video_path만 반환)
                video_path = bot.create_video_only(topic=topic)
                if video_path:
                    return {
                        'index': index,
                        'success': True,
                        'video_path': video_path,
                        'topic': topic
                    }
                else:
                    return {
                        'index': index,
                        'success': False,
                        'error': 'Video generation returned None'
                    }
                
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            logger.error(f"\n❌ 영상 #{index} 생성 중 오류: {e}", exc_info=True)
            return {
                'index': index,
                'success': False,
                'error': error_msg
            }
