"""
TTS 엔진 추상화 모듈
gTTS와 OpenAI TTS를 선택적으로 사용할 수 있도록 추상화
"""

import os
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import cast, Literal
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

try:
    import importlib.util

    REPLICATE_AVAILABLE = importlib.util.find_spec("replicate") is not None
except Exception:
    REPLICATE_AVAILABLE = False


class TTSProvider(Enum):
    """TTS 제공자"""

    GTTS = "gtts"
    OPENAI = "openai"
    GOOGLE_CLOUD = "google_cloud"  # Google Cloud Text-to-Speech (한글 발음 우수)
    NAVER_CLOVA = "naver_clova"  # Naver Clova Voice (한글 발음 최고)
    REPLICATE = "replicate"  # Replicate Coqui TTS (고품질, 다국어 지원)
    OPEN_ROUTER = "open_router"  # OpenRouter TTS (OpenAI API 호환)


class TTSEngineBase(ABC):
    """TTS 엔진 기본 클래스"""

    @staticmethod
    def _preprocess_text(text: str, lang: str = "ko") -> str:
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
        text = re.sub(r"\.{2,}", ".", text)  # 여러 점을 하나로
        text = re.sub(r"\s+", " ", text)  # 여러 공백을 하나로
        text = text.strip()

        # 한국어인 경우: 영어 변환 로직 건너뛰기
        if lang == "ko":
            # 한국어 전용 전처리 (필요시 추가)
            # 예: 'AI' -> '에이아이' 등
            abbreviations_ko = {
                r"\bAI\b": "에이아이",
                r"\bCEO\b": "씨이오",
            }
            for pattern, replacement in abbreviations_ko.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            return text

        # 영어인 경우: 숫자 변환 및 약어 확장 수행

        # 숫자를 단어로 변환하는 헬퍼 함수 (확장 버전)
        def number_to_words(num: int) -> str:
            """숫자를 영어 단어로 변환"""
            if num == 0:
                return "zero"

            # 1-19
            ones = [
                "",
                "one",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
                "nine",
                "ten",
                "eleven",
                "twelve",
                "thirteen",
                "fourteen",
                "fifteen",
                "sixteen",
                "seventeen",
                "eighteen",
                "nineteen",
            ]

            # 20-90
            tens = [
                "",
                "",
                "twenty",
                "thirty",
                "forty",
                "fifty",
                "sixty",
                "seventy",
                "eighty",
                "ninety",
            ]

            if num < 20:
                return ones[num]
            elif num < 100:
                return tens[num // 10] + ("" if num % 10 == 0 else " " + ones[num % 10])
            elif num < 1000:
                return (
                    ones[num // 100]
                    + " hundred"
                    + ("" if num % 100 == 0 else " " + number_to_words(num % 100))
                )
            elif num < 1000000:
                # 100,000의 경우 "hundred thousand"로 읽히도록 특별 처리
                if num == 100000:
                    return "hundred thousand"
                elif num % 1000 == 0 and num // 1000 == 100:
                    return "hundred thousand"
                return (
                    number_to_words(num // 1000)
                    + " thousand"
                    + ("" if num % 1000 == 0 else " " + number_to_words(num % 1000))
                )
            elif num < 1000000000:
                return (
                    number_to_words(num // 1000000)
                    + " million"
                    + (
                        ""
                        if num % 1000000 == 0
                        else " " + number_to_words(num % 1000000)
                    )
                )
            else:
                return (
                    number_to_words(num // 1000000000)
                    + " billion"
                    + (
                        ""
                        if num % 1000000000 == 0
                        else " " + number_to_words(num % 1000000000)
                    )
                )

        # 달러 금액 변환 ($30,000 → thirty thousand dollars, $100K → hundred thousand dollars)
        def convert_dollar(match):
            num_str = match.group(1).replace(",", "")  # 콤마 제거

            # K, M, B 단위 처리 (100K → 100000, 5M → 5000000, 2B → 2000000000)
            multiplier = 1
            if num_str.upper().endswith("K"):
                multiplier = 1000
                num_str = num_str[:-1]
            elif num_str.upper().endswith("M"):
                multiplier = 1000000
                num_str = num_str[:-1]
            elif num_str.upper().endswith("B"):
                multiplier = 1000000000
                num_str = num_str[:-1]

            # 빈 문자열이나 숫자가 없는 경우 원본 유지
            if not num_str or not num_str.strip().replace(".", "").isdigit():
                return match.group(0)

            try:
                num = int(float(num_str)) * multiplier
                return number_to_words(num) + " dollars"
            except Exception:
                return match.group(0)  # 변환 실패 시 원본 유지

        # 퍼센트 변환 (30% → thirty percent)
        def convert_percent(match):
            num_str = match.group(1).replace(",", "")
            try:
                num = int(float(num_str))
                if num < 100:
                    return number_to_words(num) + " percent"
                else:
                    return number_to_words(num) + " percent"
            except Exception:
                return match.group(0)

        text = re.sub(r"\$(\d+(?:,\d{3})*(?:\.\d+)?[KMBkmb]?)", convert_dollar, text)

        text = re.sub(r"([\d,]+(?:\.\d+)?)%", convert_percent, text)

        # 작은 숫자 변환 (0-99만)
        def convert_small_numbers(match):
            num_str = match.group(0)
            try:
                if len(num_str) == 4 and 1900 <= int(num_str) <= 2100:
                    return num_str
                else:
                    return number_to_words(int(num_str))
            except Exception:
                return num_str

        text = re.sub(r"\b(\d{1,2})\b", convert_small_numbers, text)

        # 약어 확장
        abbreviations = {
            r"\bAI\b": "A I",
            r"\bCEO\b": "C E O",
            r"\bOK\b": "okay",
            r"\bvs\b": "versus",
            r"\betc\b": "etcetera",
            r"\bDIY\b": "D I Y",
            r"\bFYI\b": "F Y I",
        }
        for pattern, replacement in abbreviations.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    @abstractmethod
    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
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
            raise ImportError(
                "gTTS가 설치되지 않았습니다. pip install gTTS로 설치하세요."
            )

    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
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
            raise ImportError(
                "OpenAI가 설치되지 않았습니다. pip install openai로 설치하세요."
            )

        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
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
            model = "tts-1-hd" if lang == "ko" else "tts-1-hd"

            # voice 타입을 Literal로 캐스팅 (OpenAI API 요구사항)
            voice_literal = cast(
                Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"], voice
            )
            response = self.client.audio.speech.create(
                model=model,  # 고품질 TTS (한글 발음 개선)
                voice=voice_literal,
                input=processed_text,
                speed=speed,
            )

            # 응답을 파일로 저장
            response.stream_to_file(output_path)
            logger.debug(
                f"   🔊 TTS 생성: voice={voice}, speed={speed:.2f}, content_type={content_type}"
            )
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
        if lang == "ko":
            # 한글 발음 개선: shimmer가 더 부드럽고 자연스러운 한글 발음 제공
            return (
                "shimmer"  # 한국어는 shimmer가 더 자연스러운 발음 (부드러운 여성 음성)
            )

        # 영어 voice 선택 (콘텐츠 타입별)
        voice_map = {
            "hook": "onyx",  # 강렬하고 빠른 음성
            "quote": "alloy",  # 명확하고 중립적인 음성
            "story": "shimmer",  # 감성적이고 부드러운 음성
            "fact": "alloy",  # 명확하고 빠른 음성
            "short_story": "nova",  # 자연스럽고 감성적인 음성
            "meditation": "shimmer",  # 차분하고 부드러운 음성
            "breathing": "shimmer",  # 차분하고 부드러운 음성
        }

        return voice_map.get(content_type, "alloy")  # 기본값: alloy

    def _select_speed_for_content_type(self, content_type: str) -> float:
        """
        콘텐츠 타입에 맞는 speed 선택

        Args:
            content_type: 콘텐츠 타입

        Returns:
            speed 값 (0.25 ~ 4.0)
        """
        speed_map = {
            "hook": 1.1,  # 빠르고 강렬하게
            "quote": 1.0,  # 중간 속도, 명확하게
            "story": 0.9,  # 느리고 감성적으로
            "fact": 1.05,  # 빠르고 명확하게
            "short_story": 0.95,  # 중간 속도, 감성적
            "meditation": 0.85,  # 매우 느리고 차분하게
            "breathing": 0.85,  # 매우 느리고 차분하게
        }

        return speed_map.get(content_type, 1.0)  # 기본값: 1.0


class GoogleCloudEngine(TTSEngineBase):
    """Google Cloud Text-to-Speech 엔진 (한글 발음 우수)"""

    def __init__(self):
        if not GOOGLE_CLOUD_TTS_AVAILABLE:
            raise ImportError(
                "google-cloud-texttospeech가 설치되지 않았습니다. pip install google-cloud-texttospeech로 설치하세요."
            )

        # Google Cloud 인증 확인
        google_credentials = settings.GOOGLE_CLOUD_CREDENTIALS_PATH
        if google_credentials and os.path.exists(google_credentials):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_credentials

        try:
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            raise ValueError(
                f"Google Cloud TTS 클라이언트 초기화 실패: {e}. GOOGLE_APPLICATION_CREDENTIALS 환경 변수 또는 서비스 계정 키를 확인하세요."
            )

    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
        """Google Cloud TTS로 음성 생성 (한글 발음 우수)"""
        try:
            # 텍스트 전처리
            processed_text = GoogleCloudEngine._preprocess_text(text, lang=lang)

            # 언어 코드 및 voice 설정
            if lang == "ko":
                language_code = "ko-KR"
                # 한글 최적 voice 선택 (Neural2 모델 - 가장 자연스러운 모델)
                if voice is None:
                    # Google Cloud의 Neural2 모델 사용 (가장 자연스럽고 최신 모델)
                    # 동기부여/힐링 콘텐츠에 적합한 차분하고 따뜻한 여성 음성
                    voice_name = "ko-KR-Neural2-A"  # Neural2 모델 (가장 자연스러운 한글 음성, 차분하고 따뜻한 여성 톤)
                    # 대안: "ko-KR-Neural2-B" (다른 톤의 여성 음성), "ko-KR-Neural2-C" (남성 음성)
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
                language_code=language_code, name=voice_name, ssml_gender=ssml_gender
            )

            # 오디오 설정
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=speed
            )

            # TTS 요청
            # 한글인 경우 SSML을 사용하여 언어를 강제로 지정 (영어 단어가 영어로 읽히는 문제 방지)
            if lang == "ko":
                # SSML을 사용하여 한글 언어 강제 지정
                ssml_text = (
                    f'<speak><lang xml:lang="ko-KR">{processed_text}</lang></speak>'
                )
                synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
            else:
                synthesis_input = texttospeech.SynthesisInput(text=processed_text)

            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice_config, audio_config=audio_config
            )

            # 파일 저장
            with open(output_path, "wb") as out:
                out.write(response.audio_content)

            logger.debug(
                f"   🔊 Google Cloud TTS 생성: voice={voice_name}, speed={speed:.2f}, lang={lang}"
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️ Google Cloud TTS 음성 생성 실패: {e}")
            return False


class ClovaVoiceEngine(TTSEngineBase):
    """Naver Clova Voice TTS 엔진 (한글 발음 최고)"""

    def __init__(self):
        if not settings.NAVER_CLOVA_CLIENT_ID or not settings.NAVER_CLOVA_CLIENT_SECRET:
            raise ValueError(
                "NAVER_CLOVA_CLIENT_ID와 NAVER_CLOVA_CLIENT_SECRET이 설정되지 않았습니다."
            )

        try:
            import requests

            self.requests = requests
        except ImportError:
            raise ImportError(
                "requests가 설치되지 않았습니다. pip install requests로 설치하세요."
            )

        self.client_id = settings.NAVER_CLOVA_CLIENT_ID
        self.client_secret = settings.NAVER_CLOVA_CLIENT_SECRET
        self.api_url = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
        """Naver Clova Voice TTS로 음성 생성 (한글 발음 최고)"""
        try:
            # 텍스트 전처리
            processed_text = ClovaVoiceEngine._preprocess_text(text, lang=lang)

            # 음성 선택
            if voice is None:
                voice = settings.NAVER_CLOVA_VOICE_NAME or "nara"

            # 속도 설정 (Clova Voice는 0.5 ~ 2.0 범위)
            if speed is None:
                # 콘텐츠 타입별 속도 최적화
                speed_map = {
                    "hook": 1.0,  # 중간 속도
                    "quote": 0.95,  # 약간 느리게
                    "story": 0.9,  # 느리고 감성적으로
                    "fact": 1.0,  # 중간 속도
                    "short_story": 0.95,  # 약간 느리게
                    "meditation": 0.85,  # 매우 느리고 차분하게
                    "breathing": 0.85,  # 매우 느리고 차분하게
                }
                speed = speed_map.get(content_type, 1.0)

            # Clova Voice 속도 범위 제한 (0.5 ~ 2.0)
            speed = max(0.5, min(2.0, speed))

            # API 요청 헤더
            headers = {
                "X-NCP-APIGW-API-KEY-ID": self.client_id,
                "X-NCP-APIGW-API-KEY": self.client_secret,
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # API 요청 데이터
            data = {
                "speaker": voice,  # 음성 선택
                "speed": str(speed),  # 속도
                "text": processed_text,  # 변환할 텍스트
            }

            # API 호출
            response = self.requests.post(self.api_url, headers=headers, data=data)

            if response.status_code == 200:
                # 오디오 파일 저장
                with open(output_path, "wb") as f:
                    f.write(response.content)

                logger.debug(
                    f"   🔊 Naver Clova Voice TTS 생성: voice={voice}, speed={speed:.2f}, lang={lang}"
                )
                return True
            else:
                logger.warning(
                    f"⚠️ Naver Clova Voice TTS API 오류: {response.status_code} - {response.text[:200]}"
                )
                return False

        except Exception as e:
            logger.warning(f"⚠️ Naver Clova Voice TTS 음성 생성 실패: {e}")
            return False


class ReplicateEngine(TTSEngineBase):
    """Replicate Coqui TTS 엔진 (고품질, 다국어 지원)"""

    def __init__(self):
        if not REPLICATE_AVAILABLE:
            raise ImportError(
                "replicate가 설치되지 않았습니다. pip install replicate로 설치하세요."
            )

        if not settings.REPLICATE_API_TOKEN:
            raise ValueError("REPLICATE_API_TOKEN이 설정되지 않았습니다.")

        try:
            import replicate

            self.replicate = replicate
            self.client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
        except Exception as e:
            raise ValueError(f"Replicate 클라이언트 초기화 실패: {e}")

    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
        """Replicate Coqui TTS로 음성 생성 (고품질, 다국어 지원)"""
        try:
            # 텍스트 전처리
            processed_text = ReplicateEngine._preprocess_text(text, lang=lang)

            # XTTS-v2 모델 사용 (다국어 지원, voice cloning 가능)
            # lucataco/xtts-v2: 고품질 다국어 TTS 모델
            # 최신 버전 사용
            model = "lucataco/xtts-v2"

            # 언어 코드 매핑 (XTTS-v2 지원 언어)
            # XTTS-v2는 한국어를 직접 지원하지 않으므로 영어로 폴백
            # 한국어는 다른 TTS 엔진(Google Cloud, Naver Clova) 사용 권장
            language_map = {
                "ko": "en",  # 한국어는 영어로 폴백 (한국어 미지원)
                "en": "en",
            }
            language_code = language_map.get(lang, "en")

            # XTTS-v2는 speaker 파라미터가 필수입니다 (최소 6초 오디오)
            # 기본 speaker 오디오 파일 URL 사용
            # 여성 음성 기본 샘플
            default_speaker_url = "https://replicate.delivery/pbxt/Jt79w0xsT64R1JsiJ0LQRL8UcWspg5J4RFrU6YwEKpOT1ukS/male.wav"

            # 속도 설정 (XTTS-v2는 속도 조절을 직접 지원하지 않음)
            # 속도는 나중에 오디오 후처리로 조절 가능
            if speed is None:
                speed_map = {
                    "hook": 1.1,
                    "quote": 1.0,
                    "story": 0.9,
                    "fact": 1.05,
                    "short_story": 0.95,
                    "meditation": 0.85,
                    "breathing": 0.85,
                }
                speed = speed_map.get(content_type, 1.0)

            # Replicate API 호출
            # XTTS-v2는 text, language, speaker(필수) 입력 필요
            input_params = {
                "text": processed_text,
                "language": language_code,
                "speaker": default_speaker_url,  # 기본 speaker 사용
                "cleanup_voice": False,  # 오디오 정리 비활성화
            }

            output = self.client.run(
                model,
                input=input_params,
            )

            # 출력이 URL인 경우 다운로드
            if output:
                import requests

                # output이 문자열(URL)인지 딕셔너리인지 확인
                audio_url: str
                if isinstance(output, str):
                    audio_url = output
                elif isinstance(output, dict):
                    # 딕셔너리인 경우 'audio' 키 확인
                    audio_value = output.get("audio") or output.get("output")
                    if isinstance(audio_value, str):
                        audio_url = audio_value
                    else:
                        audio_url = str(output)
                else:
                    audio_url = str(output)

                # URL에서 오디오 파일 다운로드
                if audio_url.startswith("http"):
                    response = requests.get(audio_url, stream=True)
                    if response.status_code == 200:
                        with open(output_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)

                        logger.debug(
                            f"   🔊 Replicate Coqui TTS 생성: lang={lang}, speed={speed:.2f}"
                        )
                        return True
                    else:
                        logger.warning(
                            f"⚠️ Replicate TTS 오디오 다운로드 실패: {response.status_code}"
                        )
                        return False
                else:
                    logger.warning(
                        f"⚠️ Replicate TTS 출력이 유효한 URL이 아닙니다: {audio_url}"
                    )
                    return False
            else:
                logger.warning("⚠️ Replicate TTS 출력이 비어있습니다.")
                return False

        except Exception as e:
            logger.warning(f"⚠️ Replicate Coqui TTS 음성 생성 실패: {e}")
            return False


class OpenRouterEngine(TTSEngineBase):
    """OpenRouter TTS 엔진 (OpenAI API 호환)"""

    def __init__(self):
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai가 설치되지 않았습니다. pip install openai로 설치하세요."
            )

        if not settings.OPEN_ROUTER_API_KEY:
            raise ValueError("OPEN_ROUTER_API_KEY가 설정되지 않았습니다.")

        try:
            from openai import OpenAI

            # OpenRouter는 OpenAI API와 호환되므로 base_url을 변경
            self.client = OpenAI(
                api_key=settings.OPEN_ROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
        except Exception as e:
            raise ValueError(f"OpenRouter 클라이언트 초기화 실패: {e}")

    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
        """OpenRouter TTS로 음성 생성 (OpenAI API 호환)"""
        try:
            # 텍스트 전처리
            processed_text = OpenRouterEngine._preprocess_text(text, lang=lang)

            # 음성 선택
            if voice is None:
                voice = self._select_voice_for_content_type(content_type, lang)

            # 속도 설정
            if speed is None:
                speed = self._select_speed_for_content_type(content_type)

            speed = max(0.25, min(4.0, speed))

            # OpenRouter는 OpenAI API와 호환되므로 동일한 방식으로 호출
            # 단, 모델을 OpenRouter에서 지원하는 TTS 모델로 지정해야 함
            # 예: "openai/tts-1" 또는 "openai/tts-1-hd"
            model = "openai/tts-1-hd" if lang == "ko" else "openai/tts-1-hd"

            # voice 타입을 Literal로 캐스팅 (OpenAI API 요구사항)
            voice_literal = cast(
                Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"], voice
            )
            response = self.client.audio.speech.create(
                model=model,
                voice=voice_literal,
                input=processed_text,
                speed=speed,
            )

            # 응답을 파일로 저장
            response.stream_to_file(output_path)

            logger.debug(
                f"   🔊 OpenRouter TTS 생성: voice={voice}, speed={speed:.2f}, lang={lang}"
            )
            return True

        except Exception as e:
            logger.warning(f"⚠️ OpenRouter TTS 음성 생성 실패: {e}")
            return False

    def _select_voice_for_content_type(self, content_type: str, lang: str) -> str:
        """콘텐츠 타입에 맞는 voice 선택"""
        if lang == "ko":
            return "shimmer"  # 한국어는 shimmer가 더 자연스러운 발음

        voice_map = {
            "hook": "onyx",
            "quote": "alloy",
            "story": "shimmer",
            "fact": "alloy",
            "short_story": "nova",
            "meditation": "shimmer",
            "breathing": "shimmer",
        }

        return voice_map.get(content_type, "alloy")

    def _select_speed_for_content_type(self, content_type: str) -> float:
        """콘텐츠 타입에 맞는 speed 선택"""
        speed_map = {
            "hook": 1.1,
            "quote": 1.0,
            "story": 0.9,
            "fact": 1.05,
            "short_story": 0.95,
            "meditation": 0.85,
            "breathing": 0.85,
        }

        return speed_map.get(content_type, 1.0)


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
                # 자동 선택 로직 (기존 검증된 TTS 엔진만 사용)
                # Naver Clova Voice가 설정되어 있으면 최우선 사용 (한글 발음 최고)
                if (
                    settings.NAVER_CLOVA_CLIENT_ID
                    and settings.NAVER_CLOVA_CLIENT_SECRET
                ):
                    provider = TTSProvider.NAVER_CLOVA
                # Google Cloud가 설정되어 있으면 우선 사용 (한글 발음 우수)
                elif (
                    GOOGLE_CLOUD_TTS_AVAILABLE
                    and settings.GOOGLE_CLOUD_CREDENTIALS_PATH
                ):
                    provider = TTSProvider.GOOGLE_CLOUD
                # OpenAI가 설정되어 있으면 사용
                elif settings.OPENAI_API_KEY and OPENAI_AVAILABLE:
                    provider = TTSProvider.OPENAI
                # 그 외에는 gTTS
                elif GTTS_AVAILABLE:
                    provider = TTSProvider.GTTS
                else:
                    raise ImportError(
                        "사용 가능한 TTS 엔진이 없습니다. gTTS, OpenAI, Google Cloud TTS, 또는 Naver Clova Voice를 설치하세요."
                    )

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
        elif provider == TTSProvider.NAVER_CLOVA:
            return ClovaVoiceEngine()
        elif provider == TTSProvider.REPLICATE:
            return ReplicateEngine()
        elif provider == TTSProvider.OPEN_ROUTER:
            return OpenRouterEngine()
        else:
            raise ValueError(f"지원하지 않는 TTS 제공자: {provider}")

    def generate(
        self,
        text: str,
        output_path: str,
        lang: str = "ko",
        content_type: str = None,
        voice: str = None,
        speed: float = None,
    ) -> bool:
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
        return self._engine.generate(
            text, output_path, lang, content_type, voice, speed
        )

    def get_provider(self) -> TTSProvider:
        """현재 사용 중인 TTS 제공자 반환"""
        return self.provider
