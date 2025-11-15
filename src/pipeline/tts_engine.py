"""
TTS 엔진 추상화 모듈
gTTS와 OpenAI TTS를 선택적으로 사용할 수 있도록 추상화
"""
import os
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
    
    @abstractmethod
    def generate(self, text: str, output_path: str, lang: str = 'ko') -> bool:
        """
        음성 생성
        
        Args:
            text: 변환할 텍스트
            output_path: 출력 파일 경로
            lang: 언어 코드 (기본값: 'ko')
        
        Returns:
            성공 여부
        """
        pass


class GTTSEngine(TTSEngineBase):
    """Google TTS 엔진"""
    
    def __init__(self):
        if not GTTS_AVAILABLE:
            raise ImportError("gTTS가 설치되지 않았습니다. pip install gTTS로 설치하세요.")
    
    def generate(self, text: str, output_path: str, lang: str = 'ko') -> bool:
        """gTTS로 음성 생성"""
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
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
    
    def generate(self, text: str, output_path: str, lang: str = 'ko') -> bool:
        """OpenAI TTS로 음성 생성"""
        try:
            # OpenAI TTS는 한국어를 지원하지 않으므로 영어로 변환하거나 기본 모델 사용
            # 한국어의 경우 'nova' 또는 'alloy' 모델 사용 가능
            # voice 옵션: alloy, echo, fable, onyx, nova, shimmer
            voice = "nova"  # 한국어에 가장 적합한 음성
            
            response = self.client.audio.speech.create(
                model="tts-1",  # 또는 "tts-1-hd" (더 고품질, 더 비쌈)
                voice=voice,
                input=text,
                speed=1.0
            )
            
            # 응답을 파일로 저장
            response.stream_to_file(output_path)
            return True
        except Exception as e:
            print(f"⚠️ OpenAI TTS 음성 생성 실패: {e}")
            return False


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
    
    def generate(self, text: str, output_path: str, lang: str = 'ko') -> bool:
        """
        음성 생성
        
        Args:
            text: 변환할 텍스트
            output_path: 출력 파일 경로
            lang: 언어 코드 (기본값: 'ko')
        
        Returns:
            성공 여부
        """
        return self._engine.generate(text, output_path, lang)
    
    def get_provider(self) -> TTSProvider:
        """현재 사용 중인 TTS 제공자 반환"""
        return self.provider

