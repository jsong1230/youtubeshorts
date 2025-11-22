"""
Batch video generation with parallel processing
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict, Any
from datetime import datetime

import config
from src.pipeline.bot import ShortsBot


class BatchVideoGenerator:
    """병렬 영상 생성 관리자"""
    
    def __init__(self, max_workers: int = 3):
        """
        Args:
            max_workers: 동시 실행할 최대 워커 수 (기본: 3)
        """
        self.max_workers = max_workers
        self.results = []
        
    def generate_batch(
        self, 
        count: int, 
        topics: Optional[List[str]] = None,
        upload: bool = False,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        여러 영상을 병렬로 생성
        
        Args:
            count: 생성할 영상 개수
            topics: 주제 리스트 (None이면 자동 생성)
            upload: 생성 후 업로드 여부
            force: 강제 업로드 (중복 체크 건너뛰기)
            
        Returns:
            결과 딕셔너리 (성공/실패 개수, 소요 시간 등)
        """
        print(f"\n{'='*60}")
        print(f"🚀 병렬 영상 생성 시작")
        print(f"{'='*60}")
        print(f"📊 생성할 영상 개수: {count}")
        print(f"⚙️  워커 수: {self.max_workers}")
        print(f"📤 업로드 여부: {'예' if upload else '아니오'}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        self.results = []
        
        # 주제 준비
        if topics:
            if len(topics) < count:
                print(f"⚠️ 주제가 부족합니다 ({len(topics)} < {count}). 나머지는 자동 생성됩니다.")
                topics = topics + [None] * (count - len(topics))
        else:
            topics = [None] * count
        
        # ThreadPoolExecutor로 병렬 실행
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 작업 제출
            futures = {}
            for i in range(count):
                topic = topics[i] if i < len(topics) else None
                future = executor.submit(
                    self._generate_single_video,
                    index=i + 1,
                    topic=topic,
                    upload=upload,
                    force=force
                )
                futures[future] = i + 1
            
            # 진행 상황 추적
            completed = 0
            for future in as_completed(futures):
                index = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    if result['success']:
                        print(f"\n✅ [{completed}/{count}] 영상 #{index} 생성 완료")
                        if result.get('video_path'):
                            print(f"   📹 경로: {result['video_path']}")
                        if result.get('video_id'):
                            print(f"   🎬 YouTube ID: {result['video_id']}")
                    else:
                        print(f"\n❌ [{completed}/{count}] 영상 #{index} 생성 실패")
                        print(f"   오류: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"\n❌ [{completed}/{count}] 영상 #{index} 예외 발생: {e}")
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
        print(f"\n{'='*60}")
        print(f"📊 병렬 생성 완료")
        print(f"{'='*60}")
        print(f"✅ 성공: {success_count}/{count}")
        print(f"❌ 실패: {failure_count}/{count}")
        print(f"⏱️  총 소요 시간: {duration:.1f}초 ({duration/60:.1f}분)")
        print(f"⚡ 평균 시간/영상: {duration/count:.1f}초")
        
        if success_count > 0:
            print(f"\n생성된 영상:")
            for r in self.results:
                if r['success'] and r.get('video_path'):
                    print(f"  - {r['video_path']}")
        
        print(f"{'='*60}\n")
        
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
        단일 영상 생성 (워커 스레드에서 실행)
        
        Args:
            index: 영상 번호
            topic: 주제
            upload: 업로드 여부
            force: 강제 업로드
            
        Returns:
            결과 딕셔너리
        """
        try:
            print(f"\n🎬 영상 #{index} 생성 시작... (주제: {topic or '자동 생성'})")
            
            # ShortsBot 인스턴스 생성 (각 워커마다 독립적)
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
            print(f"\n❌ 영상 #{index} 생성 중 오류: {e}")
            return {
                'index': index,
                'success': False,
                'error': error_msg
            }
