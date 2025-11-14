"""
수익화 추적 및 분석 모듈
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import config
from youtube_uploader import YouTubeUploader


class MonetizationTracker:
    """YouTube 수익화 추적 및 분석 클래스"""
    
    def __init__(self):
        self.data_file = 'monetization_data.json'
        self.uploader = YouTubeUploader()
        self._load_data()
    
    def _load_data(self):
        """데이터 로드"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            # 기존 데이터에 stats가 없으면 초기화
            if 'stats' not in self.data:
                self.data['stats'] = {
                    'total_views': 0,
                    'total_likes': 0,
                    'total_comments': 0,
                    'total_revenue': 0,
                    'subscriber_count': 0
                }
            # stats에 total_revenue가 없으면 추가
            if 'total_revenue' not in self.data['stats']:
                self.data['stats']['total_revenue'] = 0
        else:
            self.data = {
                'videos': [],
                'total_revenue': 0,
                'monthly_revenue': {},
                'stats': {
                    'total_views': 0,
                    'total_likes': 0,
                    'total_comments': 0,
                    'total_revenue': 0,
                    'subscriber_count': 0
                }
            }
            self._save_data()
    
    def _save_data(self):
        """데이터 저장"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_video(self, video_id: str, title: str, upload_date: str = None):
        """새 영상 추가"""
        if not upload_date:
            upload_date = datetime.now().isoformat()
        
        video_entry = {
            'video_id': video_id,
            'title': title,
            'upload_date': upload_date,
            'views': 0,
            'likes': 0,
            'comments': 0,
            'revenue': 0,
            'cpm': 0,  # Cost Per Mille (천 뷰당 수익)
            'updated_at': upload_date
        }
        
        self.data['videos'].append(video_entry)
        self._save_data()
    
    def update_video_stats(self, video_id: str):
        """영상 통계 업데이트"""
        stats = self.uploader.get_video_stats(video_id)
        if not stats:
            return
        
        # 영상 찾기
        video = next((v for v in self.data['videos'] if v['video_id'] == video_id), None)
        if not video:
            return
        
        # 통계 업데이트
        video['views'] = stats['views']
        video['likes'] = stats['likes']
        video['comments'] = stats['comments']
        video['updated_at'] = datetime.now().isoformat()
        
        # 수익 계산 (예상)
        video['revenue'] = self._calculate_revenue(video['views'], video['cpm'])
        
        # 전체 통계 업데이트
        self._update_total_stats()
        
        self._save_data()
    
    def _calculate_revenue(self, views: int, cpm: float = None) -> float:
        """
        수익 계산 (예상)
        
        YouTube Shorts의 경우:
        - 일반적으로 CPM이 낮음 ($0.50 - $2.00)
        - 3개월 후 수익화 시작
        - 월 $100-500 목표를 위해서는 약 50,000-250,000 뷰 필요
        """
        if cpm is None:
            # 기본 CPM 설정 (Shorts는 일반적으로 낮음)
            cpm = 1.0  # $1.00 per 1000 views
        
        # 수익 = (뷰 / 1000) * CPM
        revenue = (views / 1000) * cpm
        return round(revenue, 2)
    
    def _update_total_stats(self):
        """전체 통계 업데이트"""
        total_views = sum(v['views'] for v in self.data['videos'])
        total_likes = sum(v['likes'] for v in self.data['videos'])
        total_comments = sum(v['comments'] for v in self.data['videos'])
        total_revenue = sum(v['revenue'] for v in self.data['videos'])
        
        self.data['stats'] = {
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_revenue': total_revenue
        }
        
        # 월별 수익 계산
        self._calculate_monthly_revenue()
    
    def _calculate_monthly_revenue(self):
        """월별 수익 계산"""
        monthly = {}
        
        for video in self.data['videos']:
            upload_date = datetime.fromisoformat(video['upload_date'])
            month_key = upload_date.strftime('%Y-%m')
            
            if month_key not in monthly:
                monthly[month_key] = 0
            
            monthly[month_key] += video['revenue']
        
        self.data['monthly_revenue'] = monthly
    
    def get_progress_report(self) -> Dict:
        """진행 상황 리포트"""
        total_videos = len(self.data['videos'])
        days_since_start = 0
        
        if self.data['videos']:
            first_video_date = datetime.fromisoformat(self.data['videos'][0]['upload_date'])
            days_since_start = (datetime.now() - first_video_date).days
        
        # 목표 달성률 계산
        # 목표: 3개월(90일) 후 수익화, 월 $100-500
        target_days = 90
        days_until_monetization = max(0, target_days - days_since_start)
        
        # 예상 수익 (현재 추세 기반)
        avg_views_per_video = 0
        if total_videos > 0:
            avg_views_per_video = self.data['stats']['total_views'] / total_videos
        
        # 월별 예상 수익 (하루 1개 업로드 가정)
        estimated_monthly_revenue = avg_views_per_video * 30 * 0.001  # CPM $1.0 가정
        
        report = {
            'total_videos': total_videos,
            'days_since_start': days_since_start,
            'days_until_monetization': days_until_monetization,
            'total_views': self.data['stats']['total_views'],
            'total_revenue': self.data['stats']['total_revenue'],
            'monthly_revenue': self.data['monthly_revenue'],
            'avg_views_per_video': round(avg_views_per_video, 0),
            'estimated_monthly_revenue': round(estimated_monthly_revenue, 2),
            'target_revenue_range': {'min': 100, 'max': 500},
            'on_track': estimated_monthly_revenue >= 100
        }
        
        return report
    
    def print_report(self):
        """리포트 출력"""
        report = self.get_progress_report()
        
        print("\n" + "="*50)
        print("📊 수익화 진행 상황 리포트")
        print("="*50)
        print(f"총 업로드 영상: {report['total_videos']}개")
        print(f"시작 후 경과일: {report['days_since_start']}일")
        print(f"수익화까지 남은 일수: {report['days_until_monetization']}일")
        print(f"\n📈 통계:")
        print(f"  총 조회수: {report['total_views']:,}회")
        print(f"  총 예상 수익: ${report['total_revenue']:.2f}")
        print(f"  영상당 평균 조회수: {report['avg_views_per_video']:,.0f}회")
        print(f"\n💰 수익 분석:")
        print(f"  예상 월 수익: ${report['estimated_monthly_revenue']:.2f}")
        print(f"  목표 범위: ${report['target_revenue_range']['min']}-${report['target_revenue_range']['max']}")
        
        if report['monthly_revenue']:
            print(f"\n  월별 수익:")
            for month, revenue in sorted(report['monthly_revenue'].items()):
                print(f"    {month}: ${revenue:.2f}")
        
        if report['on_track']:
            print(f"\n✅ 목표 달성 가능!")
        else:
            print(f"\n⚠️ 목표 달성을 위해 더 많은 조회수가 필요합니다.")
        
        print("="*50 + "\n")
    
    def update_all_videos(self):
        """모든 영상 통계 업데이트"""
        print("📊 모든 영상 통계 업데이트 중...")
        for video in self.data['videos']:
            print(f"  업데이트 중: {video['title']}")
            self.update_video_stats(video['video_id'])
        print("✅ 업데이트 완료!")

