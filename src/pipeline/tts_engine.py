"""
TTS 엔진 추상화 모듈
gTTS와 OpenAI TTS를 선택적으로 사용할 수 있도록 추상화
"""
import os
import re
from abc import ABC, abstractmethod
from enum import Enum
import config

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class TTSProvider(Enum):
    """TTS 제공자"""
    GTTS = "gtts"
    OPENAI = "openai"


class TTSEngineBase(ABC):
    """TTS 엔진 기본 클래스"""
    
    @staticmethod
    def _preprocess_text(text: str) -> str:
        """
        텍스트 전처리 (발음 정확도 향상)
        - 숫자를 단어로 변환
        - 약어 확장
        - 특수 문자 처리
        
        Args:
            text: 원본 텍스트
        
        Returns:
            전처리된 텍스트
        """
        # 숫자를 단어로 변환하는 헬퍼 함수 (0-99만 변환, 나머지는 TTS가 잘 처리)
        def number_to_words_simple(num_str: str) -> str:
            """0-99 사이의 숫자를 단어로 변환"""
            try:
                num = int(float(num_str))
                if num == 0:
                    return 'zero'
                elif num < 20:
                    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                           'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
                    return ones[num]
                elif num < 100:
                    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
                    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
                    return tens[num // 10] + (' ' + ones[num % 10] if num % 10 > 0 else '')
                else:
                    # 100 이상은 그대로 유지 (TTS가 잘 처리함)
                    return num_str
            except:
                return num_str
        
        # 달러 금액 변환 ($500 → five hundred dollars, $30 → thirty dollars)
        def convert_dollar(match):
            num_str = match.group(1)
            num = int(float(num_str))
            if num < 100:
                return number_to_words_simple(num_str) + ' dollars'
            else:
                # 큰 금액은 그대로 유지 (TTS가 잘 처리함)
                return num_str + ' dollars'
        
        text = re.sub(r'\$(\d+(?:\.\d+)?)', convert_dollar, text)
        
        # 퍼센트 변환 (30% → thirty percent, 5% → five percent)
        def convert_percent(match):
            num_str = match.group(1)
            num = int(float(num_str))
            if num < 100:
                return number_to_words_simple(num_str) + ' percent'
            else:
                return num_str + ' percent'
        
        text = re.sub(r'(\d+(?:\.\d+)?)%', convert_percent, text)
        
        # 작은 숫자 변환 (0-99만, 큰 숫자는 그대로 - TTS가 잘 처리함)
        def convert_small_numbers(match):
            num_str = match.group(0)
            num = int(float(num_str)) if '.' not in num_str else int(float(num_str))
            if 0 <= num <= 99:
                return number_to_words_simple(num_str)
            else:
                return num_str
        
        text = re.sub(r'\b(\d{1,2})\b', convert_small_numbers, text)
        
        # 약어 확장
        abbreviations = {
            r'\bAI\b': 'A I',
            r'\bCEO\b': 'C E O',
            r'\bOK\b': 'okay',
            r'\bvs\b': 'versus',
            r'\betc\b': 'etcetera',
            r'\bDIY\b': 'D I Y',
            r'\bFYI\b': 'F Y I',
        }
        for pattern, replacement in abbreviations.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # 특수 문자 정리
        text = re.sub(r'\.{2,}', '.', text)  # 여러 점을 하나로
        text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
        text = text.strip()
        
        return text
    
    @abstractmethod
    def generate(self, text: str, output_path: str, lang: str = 'ko', content_type: str = None, voice: str = None, speed: float = None) -> bool:
        """
        음성 생성
        
        Args:
            text: 변환할 텍스트
            output_path: 출력 파일 경로
            lang: 언어 코드 (기본값: 'ko')
            content_type: 콘텐츠 타입 (hook, quote, story, fact, short_story)
            voice: 음성 선택 (OpenAI TTS만 지원)
            speed: 속도 (0.25 ~ 4.0, 기본값: 1.0)
        
        Returns:
            성공 여부
        """
        pass


class GTTSEngine(TTSEngineBase):
    """Google TTS 엔진"""
    
    def __init__(self):
        if not GTTS_AVAILABLE:
            raise ImportError("gTTS가 설치되지 않았습니다. pip install gTTS로 설치하세요.")
    
    def generate(self, text: str, output_path: str, lang: str = 'ko', content_type: str = None, voice: str = None, speed: float = None) -> bool:
        """gTTS로 음성 생성"""
        try:
            # 텍스트 전처리 (발음 정확도 향상)
            processed_text = GTTSEngine._preprocess_text(text)
            
            # gTTS는 voice와 speed 옵션이 제한적이므로 기본 설정 사용
            tts = gTTS(text=processed_text, lang=lang, slow=False)
            tts.save(output_path)
            return True
        except Exception as e:
            print(f"⚠️ gTTS 음성 생성 실패: {e}")
            return False


class OpenAIEngine(TTSEngineBase):
    """OpenAI TTS 엔진"""
    
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI가 설치되지 않았습니다. pip install openai로 설치하세요.")
        
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    def generate(self, text: str, output_path: str, lang: str = 'ko', content_type: str = None, voice: str = None, speed: float = None) -> bool:
        """OpenAI TTS로 음성 생성 (콘텐츠 타입별 voice/speed 최적화)"""
        try:
            # 텍스트 전처리 (발음 정확도 향상)
            processed_text = OpenAIEngine._preprocess_text(text)
            
            # 콘텐츠 타입별 voice 및 speed 선택 (감정 표현 최적화)
            if voice is None:
                voice = self._select_voice_for_content_type(content_type, lang)
            
            if speed is None:
                speed = self._select_speed_for_content_type(content_type)
            
            # speed 범위 제한 (0.25 ~ 4.0)
            speed = max(0.25, min(4.0, speed))
            
            response = self.client.audio.speech.create(
                model="tts-1-hd",  # 고품질 TTS (더 나은 음질)
                voice=voice,
                input=processed_text,
                speed=speed
            )
            
            # 응답을 파일로 저장
            response.stream_to_file(output_path)
            print(f"   🔊 TTS 생성: voice={voice}, speed={speed:.2f}, content_type={content_type}")
            return True
        except Exception as e:
            print(f"⚠️ OpenAI TTS 음성 생성 실패: {e}")
            return False
    
    def _select_voice_for_content_type(self, content_type: str, lang: str) -> str:
        """
        콘텐츠 타입에 맞는 voice 선택
        
        Args:
            content_type: 콘텐츠 타입 (hook, quote, story, fact, short_story)
            lang: 언어 코드
        
        Returns:
            voice 이름
        """
        if lang == 'ko':
            return "nova"  # 한국어는 nova가 가장 적합
        
        # 영어 voice 선택 (콘텐츠 타입별)
        voice_map = {
            'hook': 'onyx',      # 강렬하고 빠른 음성
            'quote': 'alloy',    # 명확하고 중립적인 음성
            'story': 'shimmer',  # 감성적이고 부드러운 음성
            'fact': 'alloy',     # 명확하고 빠른 음성
            'short_story': 'nova',  # 자연스럽고 감성적인 음성
            'meditation': 'shimmer',  # 차분하고 부드러운 음성
            'breathing': 'shimmer',  # 차분하고 부드러운 음성
        }
        
        return voice_map.get(content_type, 'alloy')  # 기본값: alloy
    
    def _select_speed_for_content_type(self, content_type: str) -> float:
        """
        콘텐츠 타입에 맞는 speed 선택
        
        Args:
            content_type: 콘텐츠 타입
        
        Returns:
            speed 값 (0.25 ~ 4.0)
        """
        speed_map = {
            'hook': 1.1,         # 빠르고 강렬하게
            'quote': 1.0,        # 중간 속도, 명확하게
            'story': 0.9,        # 느리고 감성적으로
            'fact': 1.05,       # 빠르고 명확하게
            'short_story': 0.95,  # 중간 속도, 감성적
            'meditation': 0.85,  # 매우 느리고 차분하게
            'breathing': 0.85,   # 매우 느리고 차분하게
        }
        
        return speed_map.get(content_type, 1.0)  # 기본값: 1.0


class TTSEngine:
    """TTS 엔진 팩토리 클래스"""
    
    def __init__(self, provider: TTSProvider = None):
        """
        TTS 엔진 초기화
        
        Args:
            provider: TTS 제공자 (None이면 자동 선택)
        """
        if provider is None:
            # 자동 선택: OpenAI가 설정되어 있으면 OpenAI, 아니면 gTTS
            # OpenAI TTS와 DALL-E 3는 OpenAI API로 사용 가능하므로 함께 사용
            if config.OPENAI_API_KEY and OPENAI_AVAILABLE:
                provider = TTSProvider.OPENAI
            elif GTTS_AVAILABLE:
                provider = TTSProvider.GTTS
            else:
                raise ImportError("사용 가능한 TTS 엔진이 없습니다. gTTS 또는 OpenAI를 설치하세요.")
        
        self.provider = provider
        self._engine = self._create_engine(provider)
    
    def _create_engine(self, provider: TTSProvider) -> TTSEngineBase:
        """엔진 생성"""
        if provider == TTSProvider.GTTS:
            return GTTSEngine()
        elif provider == TTSProvider.OPENAI:
            return OpenAIEngine()
        else:
            raise ValueError(f"지원하지 않는 TTS 제공자: {provider}")
    
    def generate(self, text: str, output_path: str, lang: str = 'ko', content_type: str = None, voice: str = None, speed: float = None) -> bool:
        """
        음성 생성
        
        Args:
            text: 변환할 텍스트
            output_path: 출력 파일 경로
            lang: 언어 코드 (기본값: 'ko')
            content_type: 콘텐츠 타입 (hook, quote, story, fact, short_story)
            voice: 음성 선택 (OpenAI TTS만 지원)
            speed: 속도 (0.25 ~ 4.0, 기본값: 1.0)
        
        Returns:
            성공 여부
        """
        return self._engine.generate(text, output_path, lang, content_type, voice, speed)
    
    def get_provider(self) -> TTSProvider:
        """현재 사용 중인 TTS 제공자 반환"""
        return self.provider

