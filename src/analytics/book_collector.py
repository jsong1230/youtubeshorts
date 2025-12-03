"""
책 리뷰 주제 수집 모듈
기관 선정/추천/수상 도서를 기반으로 주제 생성
"""
import random
from typing import List, Optional
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class BookCollector:
    """책 리뷰 주제 수집 클래스"""
    
    # 유명 기관/매체 목록
    AUTHORITIES = [
        "New York Times",
        "Amazon",
        "Goodreads",
        "Pulitzer Prize",
        "Nobel Prize in Literature",
        "Booker Prize",
        "Financial Times",
        "Wall Street Journal",
        "Harvard Business Review",
        "Forbes",
        "Bill Gates",
        "Warren Buffett",
        "Oprah's Book Club",
        "Reese's Book Club",
        "TIME Magazine",
        "The Guardian",
        "BBC",
        "Penguin Random House",
        "Barnes & Noble"
    ]
    
    # 책 관련 키워드
    BOOK_KEYWORDS = [
        "book", "books", "literature", "novel", "author", "writer",
        "bestseller", "reading", "library", "publishing", "fiction",
        "non-fiction", "biography", "memoir", "self-help", "business book"
    ]
    
    def __init__(self):
        """책 리뷰 수집기 초기화"""
        self.openai_client = None
        
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"⚠️ OpenAI 클라이언트 초기화 실패: {e}")
    
    def generate_book_review_topics(
        self,
        num_topics: int = 10,
        language: str = 'en'
    ) -> List[str]:
        """
        책 리뷰 주제 생성
        
        Args:
            num_topics: 생성할 주제 수
            language: 언어
        
        Returns:
            책 리뷰 주제 리스트
        """
        if not self.openai_client:
            # OpenAI 없으면 기본 주제 생성
            return self._generate_default_topics(num_topics)
        
        try:
            # 랜덤으로 기관 선택
            authority = random.choice(self.AUTHORITIES)
            
            # 책 권수 랜덤 선택 (5, 7, 10)
            num_books = random.choice([5, 7, 10])
            
            system_prompt = f"""You are an expert at creating engaging YouTube Shorts topics for book review videos.

Your task is to generate book review topics that:
- Feature books selected/recommended by famous authorities (New York Times, Amazon, Pulitzer Prize, etc.)
- Include specific number of books (5, 7, or 10) based on video length
- Are engaging and click-worthy
- Focus on finance, productivity, or self-improvement books
- In {language} language

Return only the topics, one per line, without numbering or bullets."""

            user_prompt = f"""Generate {num_topics} YouTube Shorts book review topics.

Requirements:
- Each topic should mention a specific authority (e.g., "{authority}") and number of books (e.g., "{num_books} books")
- Examples:
  * "{num_books} {authority} bestsellers that changed how I think about money"
  * "{authority} recommended {num_books} books for financial freedom"
  * "{num_books} {authority} award-winning books on productivity"
- Make them compelling and click-worthy
- Focus on finance, productivity, or self-improvement
- In {language} language
- Vary the authorities and number of books across topics

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
            
            logger.info(f"✅ 책 리뷰 주제 {len(unique_topics)}개 생성")
            return unique_topics[:num_topics]
            
        except Exception as e:
            logger.warning(f"⚠️ 책 리뷰 주제 생성 실패: {e}")
            return self._generate_default_topics(num_topics)
    
    def _generate_default_topics(self, num_topics: int) -> List[str]:
        """기본 책 리뷰 주제 생성 (OpenAI 없을 때)"""
        authorities = random.sample(self.AUTHORITIES, min(num_topics, len(self.AUTHORITIES)))
        num_books_list = [5, 7, 10]
        
        topics = []
        for i, authority in enumerate(authorities):
            num_books = num_books_list[i % len(num_books_list)]
            topic = f"{num_books} {authority} books that changed everything"
            topics.append(topic)
        
        return topics[:num_topics]
    
    def get_book_keywords(self) -> List[str]:
        """책 관련 키워드 반환"""
        return self.BOOK_KEYWORDS

