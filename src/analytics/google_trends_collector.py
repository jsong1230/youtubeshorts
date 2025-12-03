"""
Google Trends 트렌드 키워드 수집 모듈
pytrends를 사용하여 Google 검색 트렌드를 분석하고 주제로 변환
"""
import os
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class GoogleTrendsCollector:
    """Google Trends 트렌드 키워드 수집 클래스"""
    
    # 재태크/생산성 관련 키워드 카테고리
    FINANCE_KEYWORDS = [
        'investing', 'saving money', 'budget', 'financial planning',
        'retirement', 'stocks', 'crypto', 'passive income', 'wealth building'
    ]
    
    PRODUCTIVITY_KEYWORDS = [
        'productivity', 'time management', 'morning routine', 'focus',
        'organization', 'efficiency', 'work habits', 'goal setting'
    ]
    
    LIFESTYLE_KEYWORDS = [
        'minimalism', 'declutter', 'home organization', 'simple living',
        'lifestyle', 'self improvement', 'habits', 'routine'
    ]
    
    def __init__(self):
        """Google Trends 수집기 초기화"""
        self.pytrends = None
        self.openai_client = None
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 최소 요청 간격 (초) - Google Trends rate limiting 방지
        
        # pytrends 초기화
        if PYTRENDS_AVAILABLE:
            try:
                # 언어와 시간대 설정 (영어, 미국)
                self.pytrends = TrendReq(hl='en-US', tz=360)
                logger.info("✅ Google Trends 클라이언트 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ Google Trends 클라이언트 초기화 실패: {e}")
        
        # OpenAI API 초기화 (주제 변환용)
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")
    
    def get_trending_keywords(
        self,
        keywords: List[str],
        timeframe: str = 'today 7-d',  # 'now 7-d', 'today 1-m', 'today 3-m' 등
        geo: str = 'US'  # 지역 코드
    ) -> List[Dict]:
        """
        Google Trends에서 키워드 트렌드 가져오기
        
        Args:
            keywords: 검색할 키워드 리스트 (최대 5개)
            timeframe: 시간 범위
            geo: 지역 코드
        
        Returns:
            트렌드 키워드 리스트 (키워드, 트렌드 점수 등)
        """
        if not self.pytrends:
            logger.warning("⚠️ Google Trends API가 초기화되지 않았습니다.")
            return []
        
        try:
            # Rate limiting: 최소 요청 간격 유지
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last_request
                time.sleep(sleep_time)
            
            # 최대 5개 키워드만 처리
            keywords_to_check = keywords[:5]
            
            # 트렌드 데이터 가져오기
            self.pytrends.build_payload(
                kw_list=keywords_to_check,
                timeframe=timeframe,
                geo=geo
            )
            
            # 요청 시간 업데이트
            self.last_request_time = time.time()
            
            # 트렌드 데이터 가져오기
            trend_data = self.pytrends.interest_over_time()
            
            if trend_data.empty:
                return []
            
            # 평균 트렌드 점수 계산
            trending_keywords = []
            for keyword in keywords_to_check:
                if keyword in trend_data.columns:
                    avg_score = trend_data[keyword].mean()
                    max_score = trend_data[keyword].max()
                    trending_keywords.append({
                        'keyword': keyword,
                        'avg_score': float(avg_score),
                        'max_score': float(max_score),
                        'trending': max_score > 50  # 50 이상이면 트렌딩으로 간주
                    })
            
            # 트렌드 점수 순으로 정렬
            trending_keywords.sort(key=lambda x: x['max_score'], reverse=True)
            
            logger.info(f"✅ Google Trends에서 {len(trending_keywords)}개 키워드 트렌드 수집")
            return trending_keywords
        except Exception as e:
            logger.warning(f"⚠️ Google Trends 키워드 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_trending_keywords_by_category(
        self,
        category: str = 'finance',
        timeframe: str = 'today 7-d',
        geo: str = 'US'
    ) -> List[Dict]:
        """
        카테고리별 트렌드 키워드 가져오기
        
        Args:
            category: 카테고리 ('finance', 'productivity', 'lifestyle')
            timeframe: 시간 범위
            geo: 지역 코드
        
        Returns:
            트렌드 키워드 리스트
        """
        # 카테고리별 키워드 선택
        if category == 'finance':
            keywords = self.FINANCE_KEYWORDS
        elif category == 'productivity':
            keywords = self.PRODUCTIVITY_KEYWORDS
        elif category == 'lifestyle':
            keywords = self.LIFESTYLE_KEYWORDS
        else:
            keywords = self.FINANCE_KEYWORDS + self.PRODUCTIVITY_KEYWORDS + self.LIFESTYLE_KEYWORDS
        
        # 5개씩 나눠서 처리 (Google Trends 제한)
        # 각 배치 사이에 추가 지연 시간 (rate limiting 방지)
        all_trending = []
        for i in range(0, len(keywords), 5):
            batch = keywords[i:i+5]
            trending = self.get_trending_keywords(
                keywords=batch,
                timeframe=timeframe,
                geo=geo
            )
            all_trending.extend(trending)
            
            # 마지막 배치가 아니면 추가 지연 (Google rate limiting 방지)
            if i + 5 < len(keywords):
                time.sleep(1.0)  # 배치 사이 1초 추가 지연
        
        # 트렌드 점수 순으로 정렬
        all_trending.sort(key=lambda x: x['max_score'], reverse=True)
        
        return all_trending
    
    def convert_keywords_to_topics(
        self,
        keywords: List[Dict],
        content_type: str = 'hook',
        num_topics: int = 10,
        language: str = 'en'
    ) -> List[str]:
        """
        Google Trends 키워드를 YouTube Shorts 주제로 변환
        
        Args:
            keywords: 트렌드 키워드 리스트
            content_type: 콘텐츠 타입
            num_topics: 생성할 주제 수
            language: 언어
        
        Returns:
            변환된 주제 리스트
        """
        if not self.openai_client:
            logger.warning("⚠️ OpenAI API가 없어 Google Trends 키워드를 주제로 변환할 수 없습니다.")
            # 간단한 변환만 수행
            topics = []
            for kw_data in keywords[:num_topics]:
                keyword = kw_data['keyword']
                # 키워드를 주제로 변환
                topics.append(f"Latest trends in {keyword}")
            return topics[:num_topics]
        
        try:
            # 상위 키워드들을 프롬프트에 포함
            keyword_list = [kw['keyword'] for kw in keywords[:15]]  # 상위 15개만
            keywords_text = '\n'.join([f"- {kw}" for kw in keyword_list])
            
            system_prompt = f"""You are an expert at creating engaging YouTube Shorts topics based on Google Trends keywords.

Your task is to convert trending keywords into YouTube Shorts topics that are:
- Engaging and click-worthy
- Suitable for {content_type} content type
- 55-60 seconds long
- Related to finance, productivity, or lifestyle
- In {language} language

Return only the topics, one per line, without numbering or bullets."""

            user_prompt = f"""Based on these trending Google keywords, generate {num_topics} YouTube Shorts topics:

{keywords_text}

Requirements:
- Convert trending keywords into engaging YouTube Shorts topics
- Make them suitable for {content_type} content type
- Keep them relevant to finance, productivity, or lifestyle
- Each topic should be a complete sentence or phrase ready to use as a video title
- Make them compelling and click-worthy
- In {language} language

Return only the topics, one per line."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.8
            )
            
            topics_text = response.choices[0].message.content.strip()
            
            # 주제 파싱
            import re
            topics = []
            for line in topics_text.split('\n'):
                line = line.strip()
                # 번호나 불릿 제거
                line = re.sub(r'^[\d\.\-\*\•\s]+', '', line)
                if line and len(line) > 10:  # 최소 10자 이상
                    topics.append(line)
            
            # 중복 제거
            unique_topics = list(dict.fromkeys(topics))
            
            logger.info(f"✅ Google Trends 키워드에서 {len(unique_topics)}개 주제 생성")
            return unique_topics[:num_topics]
            
        except Exception as e:
            logger.warning(f"⚠️ Google Trends 키워드 주제 변환 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_trending_topics(
        self,
        content_type: str = 'hook',
        num_topics: int = 10,
        categories: List[str] = None,
        language: str = 'en'
    ) -> List[str]:
        """
        Google Trends 트렌드 주제 가져오기 (통합 메서드)
        
        Args:
            content_type: 콘텐츠 타입
            num_topics: 생성할 주제 수
            categories: 카테고리 리스트
            language: 언어
        
        Returns:
            트렌드 주제 리스트
        """
        if categories is None:
            categories = ['finance', 'productivity', 'lifestyle']
        
        # 각 카테고리에서 트렌드 키워드 수집
        all_keywords = []
        for category in categories:
            keywords = self.get_trending_keywords_by_category(
                category=category,
                timeframe='today 7-d',
                geo='US'
            )
            all_keywords.extend(keywords)
        
        # 트렌드 점수 순으로 정렬
        all_keywords.sort(key=lambda x: x['max_score'], reverse=True)
        
        if not all_keywords:
            return []
        
        # 주제로 변환
        topics = self.convert_keywords_to_topics(
            keywords=all_keywords,
            content_type=content_type,
            num_topics=num_topics,
            language=language
        )
        
        return topics

