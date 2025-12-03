"""
TTS 엔진 추상화 모듈
gTTS와 OpenAI TTS를 선택적으로 사용할 수 있도록 추상화
"""
import os
import re
from abc import ABC, abstractmethod
from enum import Enum
from src.core.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

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

try:
    from google.cloud import texttospeech
    GOOGLE_CLOUD_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_TTS_AVAILABLE = False


class TTSProvider(Enum):
    """TTS 제공자"""
    GTTS = "gtts"
    OPENAI = "openai"
    GOOGLE_CLOUD = "google_cloud"  # Google Cloud Text-to-Speech (한글 발음 우수)


class TTSEngineBase(ABC):
    """TTS 엔진 기본 클래스"""
    
    @staticmethod
    def _preprocess_text(text: str, lang: str = 'ko') -> str:
        """
        텍스트 전처리 (발음 정확도 향상)
        - 숫자를 단어로 변환 (영어인 경우)
        - 약어 확장
        - 특수 문자 처리
        
        Args:
            text: 원본 텍스트
            lang: 언어 코드 ('ko' 또는 'en')
        
        Returns:
            전처리된 텍스트
        """
        # 공통 전처리: 특수 문자 정리
        text = re.sub(r'\.{2,}', '.', text)  # 여러 점을 하나로
        text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
        text = text.strip()
        
        # 한국어인 경우: 영어 변환 로직 건너뛰기
        if lang == 'ko':
            # 한국어 전용 전처리 (필요시 추가)
            # 예: 'AI' -> '에이아이' 등
            abbreviations_ko = {
                r'\bAI\b': '에이아이',
                r'\bCEO\b': '씨이오',
            }
            for pattern, replacement in abbreviations_ko.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            return text
            
        # 영어인 경우: 숫자 변환 및 약어 확장 수행
        
        # 숫자를 단어로 변환하는 헬퍼 함수 (확장 버전)
        def number_to_words(num: int) -> str:
            """숫자를 영어 단어로 변환"""
            if num == 0:
                return 'zero'
            
            # 1-19
            ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                   'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']
            
            # 20-90
            tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
            
            if num < 20:
                return ones[num]
            elif num < 100:
                return tens[num // 10] + ('' if num % 10 == 0 else ' ' + ones[num % 10])
            elif num < 1000:
                return ones[num // 100] + ' hundred' + ('' if num % 100 == 0 else ' ' + number_to_words(num % 100))
            elif num < 1000000:
                # 100,000의 경우 "hundred thousand"로 읽히도록 특별 처리
                if num == 100000:
                    return 'hundred thousand'
                elif num % 1000 == 0 and num // 1000 == 100:
                    return 'hundred thousand'
                return number_to_words(num // 1000) + ' thousand' + ('' if num % 1000 == 0 else ' ' + number_to_words(num % 1000))
            elif num < 1000000000:
                return number_to_words(num // 1000000) + ' million' + ('' if num % 1000000 == 0 else ' ' + number_to_words(num % 1000000))
            else:
                return number_to_words(num // 1000000000) + ' billion' + ('' if num % 1000000000 == 0 else ' ' + number_to_words(num % 1000000000))
        
        # 달러 금액 변환 ($30,000 → thirty thousand dollars, $100K → hundred thousand dollars)
        def convert_dollar(match):
            num_str = match.group(1).replace(',', '')  # 콤마 제거
            
            # K, M, B 단위 처리 (100K → 100000, 5M → 5000000, 2B → 2000000000)
            multiplier = 1
            if num_str.upper().endswith('K'):
                multiplier = 1000
                num_str = num_str[:-1]
            elif num_str.upper().endswith('M'):
                multiplier = 1000000
                num_str = num_str[:-1]
            elif num_str.upper().endswith('B'):
                multiplier = 1000000000
                num_str = num_str[:-1]
            
            # 빈 문자열이나 숫자가 없는 경우 원본 유지
            if not num_str or not num_str.strip().replace('.', '').isdigit():
                return match.group(0)
            
            try:
                num = int(float(num_str)) * multiplier
                return number_to_words(num) + ' dollars'
            except:
                return match.group(0)  # 변환 실패 시 원본 유지
        
        # 콤마를 포함한 달러 금액 매칭 ($100,000, $100K, $5M 등)
        # 숫자로 시작해야 함 ($,000 같은 잘못된 형식 방지)
        text = re.sub(r'\$(\d+(?:,\d{3})*(?:\.\d+)?[KMBkmb]?)', convert_dollar, text)
        
        # 퍼센트 변환 (30% → thirty percent)
        def convert_percent(match):
            num_str = match.group(1).replace(',', '')
            try:
                num = int(float(num_str))
                if num < 100:
                    return number_to_words(num) + ' percent'
                else:
                    return number_to_words(num) + ' percent'
            except:
                return match.group(0)
        
        text = re.sub(r'([\d,]+(?:\.\d+)?)%', convert_percent, text)
        
        # 작은 숫자 변환 (0-99만)
        def convert_small_numbers(match):
            num_str = match.group(0)
            try:
                num = int(num_str)
                if 0 <= num <= 99:
                    return number_to_words(num)
                else:
                    return num_str
            except:
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
            processed_text = GTTSEngine._preprocess_text(text, lang=lang)
            
            # gTTS는 voice와 speed 옵션이 제한적이므로 기본 설정 사용
            tts = gTTS(text=processed_text, lang=lang, slow=False)
            tts.save(output_path)
            return True
        except Exception as e:
            logger.warning(f"⚠️ gTTS 음성 생성 실패: {e}")
            return False


class OpenAIEngine(TTSEngineBase):
    """OpenAI TTS 엔진"""
    
    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI가 설치되지 않았습니다. pip install openai로 설치하세요.")
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate(self, text: str, output_path: str, lang: str = 'ko', content_type: str = None, voice: str = None, speed: float = None) -> bool:
        """OpenAI TTS로 음성 생성 (콘텐츠 타입별 voice/speed 최적화)"""
        try:
            # 텍스트 전처리 (발음 정확도 향상)
            processed_text = OpenAIEngine._preprocess_text(text, lang=lang)
            
            # 콘텐츠 타입별 voice 및 speed 선택 (감정 표현 최적화)
            if voice is None:
                voice = self._select_voice_for_content_type(content_type, lang)
            
            if speed is None:
                speed = self._select_speed_for_content_type(content_type)
            
            # speed 범위 제한 (0.25 ~ 4.0)
            speed = max(0.25, min(4.0, speed))
            
            # 한글인 경우 더 나은 발음을 위해 tts-1-hd 사용 (고품질)
            # 영어인 경우도 tts-1-hd 사용 (일관성)
            model = "tts-1-hd" if lang == 'ko' else "tts-1-hd"
            
            response = self.client.audio.speech.create(
                model=model,  # 고품질 TTS (한글 발음 개선)
                voice=voice,
                input=processed_text,
                speed=speed
            )
            
            # 응답을 파일로 저장
            response.stream_to_file(output_path)
            logger.debug(f"   🔊 TTS 생성: voice={voice}, speed={speed:.2f}, content_type={content_type}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ OpenAI TTS 음성 생성 실패: {e}")
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
            # 한글 발음 개선: shimmer가 더 부드럽고 자연스러운 한글 발음 제공
            return "shimmer"  # 한국어는 shimmer가 더 자연스러운 발음 (부드러운 여성 음성)
        
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


class GoogleCloudEngine(TTSEngineBase):
    """Google Cloud Text-to-Speech 엔진 (한글 발음 우수)"""
    
    def __init__(self):
        if not GOOGLE_CLOUD_TTS_AVAILABLE:
            raise ImportError("google-cloud-texttospeech가 설치되지 않았습니다. pip install google-cloud-texttospeech로 설치하세요.")
        
        # Google Cloud 인증 확인
        google_credentials = settings.GOOGLE_CLOUD_CREDENTIALS_PATH
        if google_credentials and os.path.exists(google_credentials):
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials
        
        try:
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            raise ValueError(f"Google Cloud TTS 클라이언트 초기화 실패: {e}. GOOGLE_APPLICATION_CREDENTIALS 환경 변수 또는 서비스 계정 키를 확인하세요.")
    
    def generate(self, text: str, output_path: str, lang: str = 'ko', content_type: str = None, voice: str = None, speed: float = None) -> bool:
        """Google Cloud TTS로 음성 생성 (한글 발음 우수)"""
        try:
            # 텍스트 전처리
            processed_text = GoogleCloudEngine._preprocess_text(text, lang=lang)
            
            # 언어 코드 및 voice 설정
            if lang == 'ko':
                language_code = "ko-KR"
                # 한글 최적 voice 선택
                if voice is None:
                    # Google Cloud의 한글 voice 중 가장 자연스러운 것 선택
                    # Wavenet이 더 고품질이지만 유료, Standard는 무료 할당량 있음
                    voice_name = "ko-KR-Wavenet-A"  # 여성 음성 (최고 품질, 한글 발음 우수)
                    # 대안: "ko-KR-Standard-A" (무료 할당량, 품질 양호)
                    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
                else:
                    voice_name = voice
                    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
            else:
                language_code = "en-US"
                if voice is None:
                    voice_name = "en-US-Standard-C"  # 여성 음성
                    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
                else:
                    voice_name = voice
                    ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
            
            # 속도 설정 (0.25 ~ 4.0)
            if speed is None:
                speed = 1.0
            speed = max(0.25, min(4.0, speed))
            
            # 음성 설정
            voice_config = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
                ssml_gender=ssml_gender
            )
            
            # 오디오 설정
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speed
            )
            
            # TTS 요청
            synthesis_input = texttospeech.SynthesisInput(text=processed_text)
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )
            
            # 파일 저장
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            
            logger.debug(f"   🔊 Google Cloud TTS 생성: voice={voice_name}, speed={speed:.2f}, lang={lang}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Google Cloud TTS 음성 생성 실패: {e}")
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
            # 자동 선택: 한글인 경우 Google Cloud 우선, 아니면 OpenAI 우선
            tts_provider_str = settings.TTS_PROVIDER
            if tts_provider_str:
                try:
                    provider = TTSProvider(tts_provider_str.lower())
                except ValueError:
                    provider = None
            
            if provider is None:
                # 자동 선택 로직
                # Google Cloud가 설정되어 있으면 우선 사용 (한글 발음 우수)
                if GOOGLE_CLOUD_TTS_AVAILABLE and settings.GOOGLE_CLOUD_CREDENTIALS_PATH:
                    provider = TTSProvider.GOOGLE_CLOUD
                # OpenAI가 설정되어 있으면 사용
                elif settings.OPENAI_API_KEY and OPENAI_AVAILABLE:
                    provider = TTSProvider.OPENAI
                # 그 외에는 gTTS
                elif GTTS_AVAILABLE:
                    provider = TTSProvider.GTTS
                else:
                    raise ImportError("사용 가능한 TTS 엔진이 없습니다. gTTS, OpenAI, 또는 Google Cloud TTS를 설치하세요.")
        
        self.provider = provider
        self._engine = self._create_engine(provider)
    
    def _create_engine(self, provider: TTSProvider) -> TTSEngineBase:
        """엔진 생성"""
        if provider == TTSProvider.GTTS:
            return GTTSEngine()
        elif provider == TTSProvider.OPENAI:
            return OpenAIEngine()
        elif provider == TTSProvider.GOOGLE_CLOUD:
            return GoogleCloudEngine()
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

