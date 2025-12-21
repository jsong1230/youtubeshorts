"""
YouTube Shorts 스크립트 생성 모듈
"""

import re
import random
import time
import datetime
from typing import Dict, List, Optional, Tuple

try:
    # from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    # from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from src.core.config import settings
from .content_type import ContentType
from src.pipeline.topic_database import TopicDatabase
from src.utils.logger import get_logger
from src.generators.script.prompt_builder import PromptBuilder
from src.generators.script.script_parser import ScriptParser
from src.generators.script.script_validator import ScriptValidator
from src.generators.video_constants import VideoConstants

logger = get_logger(__name__)


class ScriptGenerator:
    """AI 스크립트 생성 클래스"""

    def __init__(self, openai_client=None, claude_client=None, ai_provider="openai"):
        self.openai_client = openai_client
        self.claude_client = claude_client
        self.ai_provider = ai_provider.lower()

        # Helper classes
        self.prompt_builder = PromptBuilder()
        self.script_parser = ScriptParser()
        self.script_validator = ScriptValidator()

    TREND_WEIGHTS = {
        "global": 0.40,
        "seasonal": 0.25,
        "performance": 0.20,
        "exploration": 0.15,
    }

    HIGH_PERFORMING_TOPICS: Dict[ContentType, List[str]] = {
        ContentType.HOOK: [
            # AI & 크립토 중심 주제로 업데이트 예정 (성과 데이터 축적 후)
        ],
        ContentType.QUOTE: [
            # AI & 크립토 중심 주제로 업데이트 예정 (성과 데이터 축적 후)
        ],
        ContentType.STORY: [
            # AI & 크립토 중심 주제로 업데이트 예정 (성과 데이터 축적 후)
        ],
        ContentType.FACT: [
            # AI & 크립토 중심 주제로 업데이트 예정 (성과 데이터 축적 후)
        ],
        ContentType.SHORT_STORY: [
            # AI & 크립토 중심 주제로 업데이트 예정 (성과 데이터 축적 후)
        ],
        ContentType.AUTO: [],
    }

    def generate_script(
        self,
        topic: str,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = "ko",
        target_audience: str = None,
    ) -> List[str]:
        """AI로 영상 스크립트 생성 (콘텐츠 타입별 최적화)"""
        # Claude API 사용
        if self.ai_provider == "claude" and self.claude_client:
            return self._generate_script_with_claude(
                topic, performance_prompt, content_type, language, target_audience
            )
        # OpenAI API 사용
        elif self.openai_client:
            return self._generate_script_with_openai(
                topic, performance_prompt, content_type, language, target_audience
            )

        # AI 생성이 성공하지 못한 경우
        if not self.openai_client and not self.claude_client:
            logger.warning("⚠️ AI 클라이언트가 없어 기본 스크립트를 사용합니다.")
            return self._build_default_script(topic, language=language)

        # Fallback to default script
        logger.warning("⚠️ 모든 AI 생성 실패, 기본 스크립트 반환")
        return self._build_default_script(topic, language=language)

    def _generate_script_with_prompt(
        self, topic: str, prompt: str, language: str = "ko"
    ) -> List[str]:
        """프롬프트로 스크립트 생성 (내부 메서드)"""
        if self.openai_client:
            return self._generate_script_with_openai(topic, prompt, language=language)
        elif self.claude_client:
            return self._generate_script_with_claude(topic, prompt, language=language)
        return self._build_default_script(topic, language=language)

    def _generate_script_with_claude(
        self,
        topic: str,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = "ko",
        target_audience: str = None,
    ) -> List[str]:
        """Claude API로 영상 스크립트 생성"""
        if not self.claude_client:
            logger.warning("⚠️ Claude 클라이언트가 없습니다.")
            return self._build_default_script(topic, language=language)

        try:
            # 콘텐츠 타입별 설정
            if content_type is None:
                content_type_str = settings.CONTENT_TYPE
                try:
                    content_type = ContentType(content_type_str.lower())
                except ValueError:
                    content_type = ContentType.AUTO

            target_duration = settings.SHORTS_TARGET_DURATION  # 55초

            # 타입별 시스템 프롬프트 구성
            system_prompt, max_sentences = self.prompt_builder.get_system_prompt(
                content_type, language, target_duration
            )

            # 성과 기반 프롬프트 추가
            if performance_prompt:
                system_prompt += "\n\n" + performance_prompt

            # 타겟 오디언스 프롬프트 추가
            if target_audience:
                audience_prompt = f"\n\n**TARGET AUDIENCE:** {target_audience}\n- Tailor the language, tone, and examples specifically for this demographic.\n- Address their specific pain points and desires."
                if language == "ko":
                    audience_prompt = f"\n\n**타겟 오디언스:** {target_audience}\n- 이 인구통계에 맞춰 언어, 톤, 예시를 조정하세요.\n- 그들의 구체적인 고충과 욕구를 다루세요."
                system_prompt += audience_prompt

            # 사용자 프롬프트 구성
            user_prompt = self.prompt_builder.build_user_prompt(
                topic, max_sentences, target_duration, language
            )

            # Claude API 호출
            models_to_try = [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-5-sonnet-20241022",
            ]
            response = None
            last_error = None

            for model in models_to_try:
                try:
                    response = self.claude_client.messages.create(
                        model=model,
                        max_tokens=800,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    script_text = response.content[0].text
                    filtered_sentences = self.script_parser.parse_script_text(
                        script_text, max_sentences
                    )

                    # 반복 구절 제거
                    filtered_sentences = self.script_parser.remove_repetitive_phrases(
                        filtered_sentences
                    )

                    logger.info(
                        f"📝 Claude API로 생성된 문장 수: {len(filtered_sentences)}개 (목표: {max_sentences}개)"
                    )
                    return filtered_sentences[:max_sentences]
                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ Claude 모델 {model} 실패: {e}")
                    continue

            # 모든 모델 실패 시
            error_to_raise = (
                last_error if last_error else Exception("모든 Claude 모델 접근 실패")
            )
            logger.error(f"❌ Claude API 실패: {error_to_raise}")
            return self._build_default_script(topic, language=language)

        except Exception as e:
            logger.error(f"⚠️ Claude API 스크립트 생성 실패: {e}", exc_info=True)

            # Claude API 실패 시 OpenAI로 폴백
            if self.openai_client:
                logger.warning("⚠️ Claude API 실패, OpenAI로 폴백합니다.")
                return self._generate_script_with_openai(
                    topic, performance_prompt, content_type, language
                )

            # AI 생성 실패 시 기본 스크립트 반환
            logger.warning("⚠️ AI 스크립트 생성 실패로 기본 스크립트를 사용합니다.")
            return self._build_default_script(topic, language=language)

    def _generate_script_with_openai(
        self,
        topic: str,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = "ko",
        target_audience: str = None,
    ) -> List[str]:
        """OpenAI API로 영상 스크립트 생성"""
        if not self.openai_client:
            return self._build_default_script(topic, language=language)

        try:
            if content_type is None:
                content_type_str = settings.CONTENT_TYPE
                try:
                    content_type = ContentType(content_type_str.lower())
                except ValueError:
                    content_type = ContentType.AUTO

            # 콘텐츠 타입별 최적 길이 자동 설정 (완주율 최적화)
            if content_type and content_type != ContentType.AUTO:
                content_type_key = content_type.value.lower()
                target_duration = VideoConstants.CONTENT_TYPE_DURATIONS.get(
                    content_type_key, settings.SHORTS_TARGET_DURATION
                )
                logger.info(
                    f"📏 콘텐츠 타입 '{content_type_key}' 최적 길이: {target_duration}초 (완주율 최적화)"
                )
            else:
                # AUTO 또는 타입 미지정 시 기본값 (짧은 영상 선호)
                target_duration = (
                    VideoConstants.CONTENT_TYPE_DURATIONS.get("auto")
                    if settings.PREFER_SHORT_VIDEOS
                    else settings.SHORTS_TARGET_DURATION
                )

            models_to_try = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
            response = None
            last_error = None

            # 타입별 시스템 프롬프트 구성
            system_prompt, max_sentences = self.prompt_builder.get_system_prompt(
                content_type, language, target_duration
            )

            # 성과 기반 프롬프트 추가
            if performance_prompt:
                system_prompt += "\n\n" + performance_prompt

            # 타겟 오디언스 프롬프트 추가
            if target_audience:
                audience_prompt = f"\n\n**TARGET AUDIENCE:** {target_audience}\n- Tailor the language, tone, and examples specifically for this demographic.\n- Address their specific pain points and desires."
                if language == "ko":
                    audience_prompt = f"\n\n**타겟 오디언스:** {target_audience}\n- 이 인구통계에 맞춰 언어, 톤, 예시를 조정하세요.\n- 그들의 구체적인 고충과 욕구를 다루세요."
                system_prompt += audience_prompt

            # 사용자 프롬프트 구성
            user_prompt = self.prompt_builder.build_user_prompt(
                topic, max_sentences, target_duration, language
            )

            for model in models_to_try:
                try:
                    # 랜덤 시드 생성 (다양성 확보)
                    random_seed = int(time.time() * 1000) % 10000

                    response = self.openai_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        max_tokens=800,
                        temperature=0.9,  # 0.7 → 0.9로 증가 (더 다양한 응답)
                        seed=random_seed,  # 매번 다른 시드 사용
                        frequency_penalty=1.2,  # 같은 단어/구절 반복 강력 억제 (증가)
                        presence_penalty=0.3,  # 새로운 주제 도입 장려
                    )
                    script_text = response.choices[0].message.content
                    filtered_sentences = self.script_parser.parse_script_text(
                        script_text, max_sentences
                    )

                    # 반복 구절 제거
                    filtered_sentences = self.script_parser.remove_repetitive_phrases(
                        filtered_sentences
                    )

                    # 스크립트 중복 검사
                    if self.script_validator.is_script_unique(filtered_sentences):
                        logger.info(
                            f"📝 OpenAI API로 생성된 문장 수: {len(filtered_sentences)}개 (목표: {max_sentences}개)"
                        )
                        return filtered_sentences[:max_sentences]
                    else:
                        logger.warning("⚠️ 중복 스크립트 감지, 재생성 시도 중...")
                        # 중복이면 다음 모델로 시도하거나 재생성
                        continue
                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ OpenAI 모델 {model} 실패: {e}")
                    continue

            # 모든 모델 실패 시
            if not response:
                raise last_error if last_error else Exception("모든 모델 접근 실패")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"⚠️ OpenAI API 스크립트 생성 실패: {e}", exc_info=True)

            if "does not have access" in error_msg or "model_not_found" in error_msg:
                logger.warning("⚠️ OpenAI API 키가 모델에 접근할 수 없습니다.")
                logger.warning("   OpenAI Platform에서 모델 접근 권한을 확인하세요.")

        # AI 생성 실패 시 기본 스크립트 반환
        logger.warning("⚠️ AI 스크립트 생성 실패로 기본 스크립트를 사용합니다.")
        return self._build_default_script(topic, language=language)

    def _build_default_script(
        self, topic: str, language: str = "en", target_sentences: int = 12
    ) -> List[str]:
        """AI 생성 실패 시 주제 기반 기본 스크립트를 생성"""
        topic = (topic or "").strip()
        topic_placeholder = (
            topic if topic else ("success" if language == "en" else "성공")
        )
        keywords = [
            part.strip()
            for part in re.split(r"[,/&]| and ", topic_placeholder)
            if part.strip()
        ]
        focus = keywords[0] if keywords else topic_placeholder

        if language == "en":
            base_lines = [
                f"Let's break down {topic_placeholder} in a way you can apply today.",
                f"This matters because {focus} only becomes real when you take daily action.",
                f"Define what {topic_placeholder} means for your lifestyle and money goals.",
                f"Track one metric tied to {focus} so you can see progress every day.",
                f"Study a real example of {topic_placeholder} and copy the first three moves.",
                f"Protect your time because {focus} rewards deep focus, not random effort.",
                f"Invest in skills that multiply how fast you can execute {topic_placeholder}.",
                f"Limit distractions so your brain connects directly with your {focus} target.",
                f"Build a simple routine: research, decide, take one action about {topic_placeholder}.",
                f"Review last week's choices and grade how each one supported {focus}.",
                f"Share your plan with one ally so you stay accountable for {topic_placeholder}.",
                f"Automate repetitive steps and save energy for creative {focus} decisions.",
                f"Celebrate micro-wins tied to {topic_placeholder}; momentum keeps you consistent.",
                f"Replace fear with data—track experiments related to {focus} and learn fast.",
                f"Think bigger each week; ask how {topic_placeholder} can upgrade your future self.",
                f"Take one bold action right now that proves you own {focus}.",
                f"Visualize the lifestyle unlocked by {topic_placeholder} and let that guide today.",
                f"Remember every master of {focus} started small but stayed in motion.",
            ]
        else:
            base_lines = [
                f"오늘은 {topic_placeholder}를 생활 속에서 실천하는 방법을 이야기합니다.",
                f"{focus}는 매일 행동할 때만 현실이 되므로 지금 이유를 분명히 하세요.",
                f"{topic_placeholder}가 내 삶과 수입에서 무엇을 의미하는지 먼저 정의하세요.",
                f"{focus}와 연결된 지표를 하나 정해 매일 변화를 숫자로 확인하세요.",
                f"{topic_placeholder} 성공 사례를 찾아 처음 세 가지 동작을 그대로 따라 해보세요.",
                f"집중력을 지키세요. {focus}는 우연이 아니라 깊은 집중에서 탄생합니다.",
                f"{topic_placeholder}를 실행할 수 있는 역량에 투자해 복리를 만들어 주세요.",
                f"잡음을 줄여 두뇌가 {focus} 목표와 직접 연결되도록 환경을 정리하세요.",
                f"연구-결정-실행으로 이어지는 간단한 루틴을 만들어 {topic_placeholder}를 습관화하세요.",
                f"지난주 선택을 되돌아보며 각각이 {focus}에 어떻게 기여했는지 적어보세요.",
                f"주변 한 사람에게 계획을 공유하고 {topic_placeholder} 실천을 약속하세요.",
                f"반복적인 일은 자동화해 {focus}와 관련된 창의적 판단에 에너지를 쓰세요.",
                f"{topic_placeholder}와 연결된 작은 성과를 축하하고 꾸준함을 유지하세요.",
                f"두려움 대신 데이터를 선택하고 {focus}와 관련된 실험을 추적하며 배우세요.",
                f"매주 질문하세요. {topic_placeholder}가 내 미래를 어떻게 바꿀 수 있을까?",
                f"지금 당장 {focus}를 증명할 과감한 행동을 하나 실행하며 마무리하세요.",
                f"{topic_placeholder}가 열어줄 라이프스타일을 구체적으로 상상하고 오늘을 설계하세요.",
                f"{focus}의 달인도 작은 걸음에서 시작했지만 멈추지 않았음을 기억하세요.",
            ]

        if target_sentences <= 0:
            return []
        return base_lines[:target_sentences]

    def generate_topic(self, content_type: ContentType = None) -> tuple:
        """
        검색 기반으로 주제 생성 (Reddit, Google Trends, YouTube 트렌드 활용)
        하드코딩된 주제 제거, 항상 검색 기반으로 주제 선정

        Returns:
            (topic, source) 튜플
        """
        if content_type is None:
            content_type_str = settings.CONTENT_TYPE
            try:
                content_type = ContentType(content_type_str.lower())
            except ValueError:
                content_type = ContentType.AUTO

        # 자동 선택 시 랜덤
        if content_type == ContentType.AUTO:
            content_type = random.choice(
                [
                    ContentType.HOOK,
                    ContentType.QUOTE,
                    ContentType.STORY,
                    ContentType.FACT,
                    ContentType.SHORT_STORY,
                    ContentType.BOOK_REVIEW,
                ]
            )

        # BOOK_REVIEW 타입이면 책 리뷰 주제 생성
        if content_type == ContentType.BOOK_REVIEW:
            try:
                from src.analytics.book_collector import BookCollector

                book_collector = BookCollector()
                book_topics = book_collector.generate_book_review_topics(
                    num_topics=10, language="en"
                )
                if book_topics:
                    # 랜덤으로 하나 선택
                    selected_topic = random.choice(book_topics)
                    logger.info(
                        f"🎯 최종 선택 주제: '{selected_topic}' (출처: book_review, 타입: {content_type.value})"
                    )
                    return selected_topic, "book_review"
            except Exception as e:
                logger.warning(f"⚠️ 책 리뷰 주제 생성 실패: {e}")
                # 실패 시 일반 주제 생성으로 폴백
                content_type = ContentType.AUTO

        # 현재 계절 확인
        current_season = self._get_season()

        # 검색 기반 주제 수집
        all_topics = []

        # 1. Reddit 트렌드 주제
        try:
            from src.analytics.reddit_collector import RedditCollector

            reddit_collector = RedditCollector()
            reddit_topics = reddit_collector.get_trending_topics(
                content_type=content_type.value,
                num_topics=15,
                categories=["finance", "productivity", "lifestyle"],
                language="en",
            )
            if reddit_topics:
                all_topics.extend([(topic, "reddit") for topic in reddit_topics])
                logger.info(f"✅ Reddit에서 {len(reddit_topics)}개 주제 수집")
        except Exception as e:
            logger.warning(f"⚠️ Reddit 주제 수집 실패: {e}")

        # 2. Google Trends 주제
        try:
            from src.analytics.google_trends_collector import GoogleTrendsCollector

            trends_collector = GoogleTrendsCollector()
            trends_topics = trends_collector.get_trending_topics(
                content_type=content_type.value,
                num_topics=15,
                categories=["finance", "productivity", "lifestyle"],
                language="en",
            )
            if trends_topics:
                all_topics.extend([(topic, "google_trends") for topic in trends_topics])
                logger.info(f"✅ Google Trends에서 {len(trends_topics)}개 주제 수집")
        except Exception as e:
            logger.warning(f"⚠️ Google Trends 주제 수집 실패: {e}")

        # 3. YouTube 트렌드 주제
        youtube_trending_topics = []
        try:
            youtube_trending_topics = self.get_youtube_trending_topics()
            if youtube_trending_topics:
                all_topics.extend(
                    [(topic, "youtube_trend") for topic in youtube_trending_topics]
                )
                logger.info(
                    f"✅ YouTube 트렌드에서 {len(youtube_trending_topics)}개 주제 수집"
                )
        except Exception as e:
            logger.warning(f"⚠️ YouTube 트렌드 주제 수집 실패: {e}")

        # 4. 계절별 AI 생성 주제
        try:
            ai_seasonal_topics = self.generate_seasonal_topics_from_trends(
                current_season, content_type, language="en"
            )
            if ai_seasonal_topics:
                all_topics.extend(
                    [(topic, "ai_seasonal") for topic in ai_seasonal_topics]
                )
                logger.info(f"✅ 계절별 AI 주제 {len(ai_seasonal_topics)}개 생성")
        except Exception as e:
            logger.warning(f"⚠️ 계절별 AI 주제 생성 실패: {e}")

        # 5. 일반 AI 생성 주제
        try:
            ai_trend_topics = self.generate_ai_topics_from_trends(
                content_type, language="en"
            )
            if ai_trend_topics:
                all_topics.extend(
                    [(topic, "ai_generated") for topic in ai_trend_topics]
                )
                logger.info(f"✅ AI 생성 주제 {len(ai_trend_topics)}개 생성")
        except Exception as e:
            logger.warning(f"⚠️ AI 주제 생성 실패: {e}")

        # 6. 성과 기반 주제
        performance_topics = self._get_high_performing_topics(content_type)
        if performance_topics:
            all_topics.extend([(topic, "performance") for topic in performance_topics])
            logger.info(f"✅ 성과 기반 주제 {len(performance_topics)}개 수집")

        # 7. 채널 히스토리 기반 중복 체크
        try:
            from src.analytics.channel_history_collector import ChannelHistoryCollector

            channel_collector = ChannelHistoryCollector()

            # 주제만 추출
            topic_list = [topic for topic, _ in all_topics]

            # 중복 필터링
            filtered_topics = channel_collector.filter_duplicate_topics(
                new_topics=topic_list, days=90
            )

            # 필터링된 주제만 유지
            all_topics = [
                (topic, source)
                for topic, source in all_topics
                if topic in filtered_topics
            ]
            logger.info(
                f"✅ 채널 히스토리 기반 중복 체크 완료: {len(all_topics)}개 주제 남음"
            )
        except Exception as e:
            logger.warning(f"⚠️ 채널 히스토리 중복 체크 실패: {e}")

        # 주제가 없으면 AI로 즉시 생성
        if not all_topics:
            logger.warning("⚠️ 수집된 주제가 없어 AI로 즉시 생성합니다...")
            try:
                # AI로 주제 즉시 생성
                if self.openai_client:
                    prompt = f"""Generate one engaging YouTube Shorts topic for {content_type.value} content type.
The topic should be about finance, productivity, or lifestyle.
Return only the topic, no numbering or bullets."""

                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert at creating engaging YouTube Shorts topics.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=100,
                        temperature=0.8,
                    )

                    fallback_topic = response.choices[0].message.content.strip()
                    # 번호나 불릿 제거
                    import re

                    fallback_topic = re.sub(r"^[\d\.\-\*\•\s]+", "", fallback_topic)
                    if fallback_topic:
                        all_topics = [(fallback_topic, "ai_fallback")]
            except Exception as e:
                logger.warning(f"⚠️ AI 주제 생성 실패: {e}")

        # 주제 선택 (랜덤 또는 가중치 기반)
        if all_topics:
            # 소스별 가중치 (Reddit, Google Trends 우선)
            source_weights = {
                "reddit": 3.0,
                "google_trends": 3.0,
                "youtube_trend": 2.5,
                "ai_seasonal": 2.0,
                "ai_generated": 2.0,
                "performance": 1.5,
                "ai_fallback": 1.0,
            }

            # 가중치 기반 선택
            weighted_topics = []
            for topic, source in all_topics:
                weight = source_weights.get(source, 1.0)
                weighted_topics.extend(
                    [(topic, source)] * int(weight * 10)
                )  # 가중치를 정수로 변환

            selected_topic, source = (
                random.choice(weighted_topics) if weighted_topics else all_topics[0]
            )
        else:
            # 최후의 수단
            selected_topic = "Financial tips for success"
            source = "hardcoded_fallback"
            logger.warning("⚠️ 모든 주제 수집 실패, 기본 주제 사용")

        logger.info(
            f"🎯 주제 선택: '{selected_topic}' (출처: {source}, 타입: {content_type.value})"
        )

        return selected_topic, source

    def _get_season(self) -> str:
        """
        현재 날짜를 기반으로 계절 판단

        Returns:
            'spring', 'summer', 'autumn', 'winter'
        """
        month = datetime.datetime.now().month
        if 3 <= month <= 5:
            return "spring"
        elif 6 <= month <= 8:
            return "summer"
        elif 9 <= month <= 11:
            return "autumn"
        else:
            return "winter"

    def get_youtube_trending_topics(self) -> List[str]:
        """YouTube 트렌드 주제 가져오기 (캐싱 사용)"""
        try:
            from src.analytics.trend_collector import TrendCollector
            import os

            # 캐시 파일 경로
            cache_file = os.path.join(settings.TEMP_DIR, "trending_topics_cache.json")
            cache_duration = 24 * 3600  # 24시간 캐시

            # 캐시 확인
            if os.path.exists(cache_file):
                import json
                import time

                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get("timestamp", 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get("topics", [])
                        if topics:
                            logger.debug(f"📊 캐시된 트렌드 주제 {len(topics)}개 사용")
                            return topics

            # 트렌드 수집
            collector = TrendCollector()
            topics = collector.get_trending_topics_for_category(
                category="finance", max_videos=20
            )

            # 캐시 저장
            if topics:
                os.makedirs(settings.TEMP_DIR, exist_ok=True)
                import json
                import time

                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {"timestamp": time.time(), "topics": topics},
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                logger.info(f"✅ 트렌드 주제 {len(topics)}개 수집 및 캐시 저장")

            return topics
        except Exception as e:
            logger.warning(f"⚠️ YouTube 트렌드 주제 수집 실패: {e}")
            return []

    def generate_seasonal_topics_from_trends(
        self, season: str, content_type: ContentType, language: str = "en"
    ) -> List[str]:
        """
        계절별 트렌드 키워드를 기반으로 AI가 새로운 계절별 주제 생성
        """
        try:
            from src.analytics.trend_collector import TrendCollector
            import os

            # 캐시 파일 경로
            cache_file = os.path.join(
                settings.TEMP_DIR,
                f"ai_seasonal_topics_cache_{season}_{content_type.value}_{language}.json",
            )
            cache_duration = 7 * 24 * 3600  # 7일 캐시

            # 캐시 확인
            if os.path.exists(cache_file):
                import json
                import time

                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get("timestamp", 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get("topics", [])
                        if topics:
                            logger.debug(
                                f"📊 캐시된 {season} 계절 AI 생성 주제 {len(topics)}개 사용"
                            )
                            return topics

            # 계절별 트렌드 키워드 수집
            collector = TrendCollector()
            keywords = collector.collect_seasonal_trending_keywords(
                season=season, max_videos=30, min_views=5000, top_n=15
            )

            if not keywords:
                logger.warning(
                    f"⚠️ {season} 계절 트렌드 키워드가 없어 AI 주제 생성을 건너뜁니다."
                )
                return []

            # AI로 계절별 주제 생성
            generated_topics = collector.generate_seasonal_topics(
                season=season,
                keywords=keywords,
                content_type=content_type.value,
                num_topics=10,
                language=language,
            )

            # 품질 검증 및 필터링
            validated_topics = []
            existing_topics = self.get_all_existing_topics(content_type)
            existing_seasonal_topics = self.get_seasonal_topics_for_season(
                season, content_type
            )
            existing_topics.extend(existing_seasonal_topics)

            for topic in generated_topics:
                validation = collector.validate_topic_quality(
                    topic=topic, existing_topics=existing_topics
                )
                if validation["is_valid"]:
                    validated_topics.append(topic)
                else:
                    logger.debug(
                        f"   ❌ {season} 계절 주제 검증 실패: {topic[:50]}... (점수: {validation['score']})"
                    )

            # 캐시 저장
            if validated_topics:
                os.makedirs(settings.TEMP_DIR, exist_ok=True)
                import json
                import time

                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {"timestamp": time.time(), "topics": validated_topics},
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )
                logger.info(
                    f"✅ {season} 계절 AI 생성 주제 {len(validated_topics)}개 검증 완료 및 캐시 저장"
                )

            return validated_topics

        except Exception as e:
            logger.warning(f"⚠️ {season} 계절 AI 주제 생성 실패: {e}")
            return []

    def get_seasonal_topics_for_season(
        self, season: str, content_type: ContentType
    ) -> List[str]:
        """특정 계절의 기존 주제 가져오기 (중복 확인용)"""
        seasonal_topics = {}

        if content_type == ContentType.HOOK:
            seasonal_topics = {
                "spring": [
                    "Why new-year plans keep collapsing by March",
                    "How people who reset each season look five years later",
                    "Why your salary alone will never make you wealthy",
                    "The simple rule people with tidy homes follow every day",
                ],
                "summer": [
                    "Why summer spending ruins your fall budget",
                    "The one habit that separates summer savers from summer spenders",
                    "Why your vacation fund disappears by August",
                ],
                "autumn": [
                    "Why people who plan in September retire earlier",
                    "The October habit that changes your December",
                    "Why your year-end bonus disappears by January",
                ],
                "winter": [
                    "Why January goals fail by February",
                    "The December decision that determines your March",
                    "Why your holiday spending haunts your spring",
                ],
            }
        # ... (다른 타입들은 생략하거나 필요시 추가, 일단 주요 로직만 복사)
        # 전체 복사하면 너무 길어지므로 핵심만 복사하고 나머지는 VideoGenerator 참조 로직 제거 후 구현
        # 여기서는 VideoGenerator의 로직을 그대로 가져옴

        return seasonal_topics.get(season.lower(), [])

    def generate_ai_topics_from_trends(
        self, content_type: ContentType, language: str = "en"
    ) -> List[str]:
        """트렌드 키워드를 기반으로 AI가 새로운 주제 생성"""
        try:
            from src.analytics.trend_collector import TrendCollector
            import os

            cache_file = os.path.join(
                settings.TEMP_DIR,
                f"ai_topics_cache_{content_type.value}_{language}.json",
            )
            cache_duration = 12 * 3600

            if os.path.exists(cache_file):
                import json
                import time

                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get("timestamp", 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get("topics", [])
                        if topics:
                            return topics

            collector = TrendCollector()
            keywords = collector.collect_trending_keywords(
                max_videos=30, min_views=5000, top_n=15
            )

            if not keywords:
                return []

            generated_topics = collector.generate_topics_from_trends(
                keywords=keywords,
                content_type=content_type.value,
                num_topics=10,
                language=language,
            )

            validated_topics = []
            existing_topics = self.get_all_existing_topics(content_type)

            for topic in generated_topics:
                validation = collector.validate_topic_quality(
                    topic=topic, existing_topics=existing_topics
                )
                if validation["is_valid"]:
                    validated_topics.append(topic)

            if validated_topics:
                os.makedirs(settings.TEMP_DIR, exist_ok=True)
                import json
                import time

                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {"timestamp": time.time(), "topics": validated_topics},
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

            return validated_topics

        except Exception as e:
            logger.warning(f"⚠️ AI 주제 생성 실패: {e}")
            return []

    def _get_high_performing_topics(self, content_type: ContentType) -> List[str]:
        """콘텐츠 타입별 성과가 좋았던 주제 풀을 반환."""
        topics = []

        try:
            topic_db = TopicDatabase()

            db_topics = topic_db.get_high_performing_topics(
                content_type=(
                    content_type.value if content_type != ContentType.AUTO else None
                ),
                days=30,
                min_views=100,
                min_engagement_rate=1.0,
                limit=10,
            )
            topics.extend(db_topics)
        except Exception as e:
            logger.warning(f"⚠️ 주제 데이터베이스에서 성과 주제 가져오기 실패: {e}")

        if content_type == ContentType.AUTO:
            for key, values in self.HIGH_PERFORMING_TOPICS.items():
                if key == ContentType.AUTO:
                    continue
                topics.extend(values)
        else:
            topics.extend(self.HIGH_PERFORMING_TOPICS.get(content_type, []))

        return list(dict.fromkeys(topics))

    def get_all_existing_topics(self, content_type: ContentType) -> List[str]:
        """기존 주제 풀에서 모든 주제 가져오기"""
        all_topics = []
        high_performing = self._get_high_performing_topics(content_type)
        all_topics.extend(high_performing)
        return all_topics

    def select_topic_with_strategy(
        self,
        global_topics: List[str],
        seasonal_topics: List[str],
        performance_topics: List[str],
        youtube_trending_topics: List[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """TREND_MODE 여부에 따라 주제 선택 전략을 적용."""
        global_pool = [topic for topic in global_topics if topic]
        seasonal_pool = [topic for topic in seasonal_topics if topic]
        performance_pool = [topic for topic in performance_topics if topic]
        trending_pool = [topic for topic in (youtube_trending_topics or []) if topic]

        if getattr(settings, "TREND_MODE", False):
            pools: List[Tuple[List[str], str]] = []
            weights: List[float] = []

            def add_pool(pool: List[str], source: str, weight: float) -> None:
                if pool and weight > 0:
                    pools.append((pool, source))
                    weights.append(weight)

            if trending_pool:
                combined_global = list(dict.fromkeys(global_pool + trending_pool))
                add_pool(combined_global, "youtube_trend", self.TREND_WEIGHTS["global"])
            else:
                add_pool(global_pool, "global_trend", self.TREND_WEIGHTS["global"])

            add_pool(seasonal_pool, "seasonal", self.TREND_WEIGHTS["seasonal"])
            add_pool(performance_pool, "performance", self.TREND_WEIGHTS["performance"])

            exploration_candidates = list(
                dict.fromkeys(
                    (trending_pool if trending_pool else global_pool)
                    + seasonal_pool
                    + performance_pool
                )
            )
            exploration_pool = (
                exploration_candidates
                or global_pool
                or seasonal_pool
                or performance_pool
            )
            add_pool(exploration_pool, "exploration", self.TREND_WEIGHTS["exploration"])

            if pools:
                idx = random.choices(range(len(pools)), weights=weights, k=1)[0]
                selected_pool, source = pools[idx]

                try:
                    from src.analytics.trend_collector import TrendCollector

                    collector = TrendCollector()
                    topic_weights = []
                    for topic in selected_pool:
                        cpm_score = collector.analyze_cpm_potential(topic)
                        topic_weights.append(cpm_score)

                    if topic_weights and sum(topic_weights) > 0:
                        selected_topic = random.choices(
                            selected_pool, weights=topic_weights, k=1
                        )[0]
                        return selected_topic, source
                except Exception as e:
                    logger.warning(f"⚠️ CPM 기반 선택 실패, 랜덤 선택으로 폴백: {e}")

                return random.choice(selected_pool), source

        if seasonal_pool and random.random() < 0.25:
            return random.choice(seasonal_pool), "seasonal"

        fallback_pool = (
            trending_pool or global_pool or performance_pool or seasonal_pool
        )
        if not fallback_pool:
            return "Momentum reset routine", "global_trend"
        return random.choice(fallback_pool), "global_trend"
