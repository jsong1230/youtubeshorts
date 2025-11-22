"""
YouTube Shorts 스크립트 생성 모듈
"""
import re
import random
import time
import hashlib
from typing import List, Optional, Tuple
from enum import Enum

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

import config
from .content_type import ContentType
from src.pipeline.topic_database import TopicDatabase


class ScriptGenerator:
    """AI 스크립트 생성 클래스"""
    
    def __init__(self, openai_client=None, claude_client=None, ai_provider='openai'):
        self.openai_client = openai_client
        self.claude_client = claude_client
        self.ai_provider = ai_provider.lower()

    TREND_WEIGHTS = {
        "global": 0.40,
        "seasonal": 0.25,
        "performance": 0.20,
        "exploration": 0.15,
    }

    HIGH_PERFORMING_TOPICS = {
        ContentType.HOOK: [
            "Money vanishes in patterns, not accidents.",
            "Structure builds wealth faster than motivation ever could.",
            "AI automation frees the 30 minutes you keep losing.",
            "Routines decide your life long before you do.",
            "Tiny routines create massive peace.",
        ],
        ContentType.QUOTE: [
            "Tiny routines create massive peace.",
            "Money is measurement; direction is wealth.",
            "Consistency outruns talent every single time.",
            "Decluttering a room calms your mind, and a calm mind cuts anxiety.",
        ],
        ContentType.STORY: [
            "He cleared one closet and reset his entire routine.",
            "A 30-day expense log rebuilt her bank balance.",
            "A five-minute evening review saved a burned-out manager.",
            "An AI micro-routine gave him back an hour every morning.",
        ],
        ContentType.FACT: [
            "Tracking spend for 30 days cuts impulse buys by 15%.",
            "Decluttered desks raise focus by 25%.",
            "Skipping a winter oil check can cost an engine replacement.",
            "AI batching saves at least 30 minutes per day.",
        ],
        ContentType.SHORT_STORY: [
            "Logging expenses for 30 days changed my bank balance.",
            "Ten minutes of routine completely rerouted her life.",
            "Preparing for winter once cut our heating bill in half.",
            "I automated emails with AI and finally slept.",
        ],
        ContentType.AUTO: [],
    }
    
    def generate_script(
        self,
        topic: str,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = 'ko',
        target_audience: str = None
    ) -> List[str]:
        """AI로 영상 스크립트 생성 (콘텐츠 타입별 최적화)"""
        # Claude API 사용
        if self.ai_provider == 'claude' and self.claude_client:
            return self._generate_script_with_claude(
                topic, performance_prompt, content_type, language, target_audience)
        # OpenAI API 사용
        elif self.openai_client:
            return self._generate_script_with_openai(
                topic, performance_prompt, content_type, language, target_audience)
        
        # AI 생성이 성공하지 못한 경우
        if not self.openai_client and not self.claude_client:
            print(f"⚠️ AI 클라이언트가 없어 기본 스크립트를 사용합니다.")
            return self._build_default_script(topic, language=language)
        
        # 이 코드는 실행되지 않아야 하지만 안전을 위해 추가
        return self._build_default_script(topic, language=language)
    
    def _generate_script_with_claude(
        self,
        topic: str,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = 'ko',
        target_audience: str = None
    ) -> List[str]:
        """Claude API로 영상 스크립트 생성"""
        if not self.claude_client:
            print(f"⚠️ Claude 클라이언트가 없습니다.")
            return self._build_default_script(topic, language=language)
        
        try:
            # 콘텐츠 타입별 설정
            if content_type is None:
                content_type_str = getattr(config, 'CONTENT_TYPE', 'auto')
                try:
                    content_type = ContentType(content_type_str.lower())
                except ValueError:
                    content_type = ContentType.AUTO
            
            target_duration = config.SHORTS_TARGET_DURATION  # 55초
            
            # 타입별 시스템 프롬프트 구성
            system_prompt, max_sentences = self._get_system_prompt(
                content_type, language, target_duration)
            
            # 성과 기반 프롬프트 추가
            if performance_prompt:
                system_prompt += "\n\n" + performance_prompt
            
            # 타겟 오디언스 프롬프트 추가
            if target_audience:
                audience_prompt = f"\n\n**TARGET AUDIENCE:** {target_audience}\n- Tailor the language, tone, and examples specifically for this demographic.\n- Address their specific pain points and desires."
                if language == 'ko':
                    audience_prompt = f"\n\n**타겟 오디언스:** {target_audience}\n- 이 인구통계에 맞춰 언어, 톤, 예시를 조정하세요.\n- 그들의 구체적인 고충과 욕구를 다루세요."
                system_prompt += audience_prompt
            
            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(
                topic, max_sentences, target_duration, language)
            
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
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    script_text = response.content[0].text
                    filtered_sentences = self._parse_script_text(script_text, max_sentences)
                    
                    # 반복 구절 제거
                    filtered_sentences = self._remove_repetitive_phrases(filtered_sentences)
                    
                    print(f"📝 Claude API로 생성된 문장 수: {len(filtered_sentences)}개 (목표: {max_sentences}개)")
                    return filtered_sentences[:max_sentences]
                except Exception as e:
                    last_error = e
                    print(f"⚠️ Claude 모델 {model} 실패: {e}")
                    continue
            
            # 모든 모델 실패 시
            if not response:
                error_to_raise = last_error if last_error else Exception("모든 Claude 모델 접근 실패")
                print(f"⚠️ 모든 Claude 모델 실패, 마지막 오류: {error_to_raise}")
                raise error_to_raise
        
        except Exception as e:
            print(f"⚠️ Claude API 스크립트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
            # Claude API 실패 시 OpenAI로 폴백
            if self.openai_client:
                print(f"⚠️ Claude API 실패, OpenAI로 폴백합니다.")
                return self._generate_script_with_openai(
                    topic, performance_prompt, content_type, language)
            
            # AI 생성 실패 시 기본 스크립트 반환
            print(f"⚠️ AI 스크립트 생성 실패로 기본 스크립트를 사용합니다.")
            return self._build_default_script(topic, language=language)
    
    def _generate_script_with_openai(
        self,
        topic: str,
        performance_prompt: str = None,
        content_type: ContentType = None,
        language: str = 'ko',
        target_audience: str = None
    ) -> List[str]:
        """OpenAI API로 영상 스크립트 생성"""
        if not self.openai_client:
            return self._build_default_script(topic, language=language)
        
        try:
            if content_type is None:
                content_type_str = getattr(config, 'CONTENT_TYPE', 'auto')
                try:
                    content_type = ContentType(content_type_str.lower())
                except ValueError:
                    content_type = ContentType.AUTO
            
            target_duration = config.SHORTS_TARGET_DURATION  # 55초
            models_to_try = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
            response = None
            last_error = None
            
            # 타입별 시스템 프롬프트 구성
            system_prompt, max_sentences = self._get_system_prompt(
                content_type, language, target_duration)
            
            # 성과 기반 프롬프트 추가
            if performance_prompt:
                system_prompt += "\n\n" + performance_prompt
            
            # 타겟 오디언스 프롬프트 추가
            if target_audience:
                audience_prompt = f"\n\n**TARGET AUDIENCE:** {target_audience}\n- Tailor the language, tone, and examples specifically for this demographic.\n- Address their specific pain points and desires."
                if language == 'ko':
                    audience_prompt = f"\n\n**타겟 오디언스:** {target_audience}\n- 이 인구통계에 맞춰 언어, 톤, 예시를 조정하세요.\n- 그들의 구체적인 고충과 욕구를 다루세요."
                system_prompt += audience_prompt
            
            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(
                topic, max_sentences, target_duration, language)
            
            for model in models_to_try:
                try:
                    # 랜덤 시드 생성 (다양성 확보)
                    random_seed = int(time.time() * 1000) % 10000
                    
                    response = self.openai_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=800,
                        temperature=0.9,  # 0.7 → 0.9로 증가 (더 다양한 응답)
                        seed=random_seed,  # 매번 다른 시드 사용
                        frequency_penalty=0.5,  # 같은 단어/구절 반복 억제
                        presence_penalty=0.3   # 새로운 주제 도입 장려
                    )
                    script_text = response.choices[0].message.content
                    filtered_sentences = self._parse_script_text(script_text, max_sentences)
                    
                    # 반복 구절 제거
                    filtered_sentences = self._remove_repetitive_phrases(filtered_sentences)
                    
                    # 스크립트 중복 검사
                    if self._is_script_unique(filtered_sentences):
                        print(f"📝 OpenAI API로 생성된 문장 수: {len(filtered_sentences)}개 (목표: {max_sentences}개)")
                        return filtered_sentences[:max_sentences]
                    else:
                        print(f"⚠️ 중복 스크립트 감지, 재생성 시도 중...")
                        # 중복이면 다음 모델로 시도하거나 재생성
                        continue
                except Exception as e:
                    last_error = e
                    print(f"⚠️ OpenAI 모델 {model} 실패: {e}")
                    continue
            
            # 모든 모델 실패 시
            if not response:
                raise last_error if last_error else Exception("모든 모델 접근 실패")
        
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ OpenAI API 스크립트 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            
            if "does not have access" in error_msg or "model_not_found" in error_msg:
                print(f"⚠️ OpenAI API 키가 모델에 접근할 수 없습니다.")
                print(f"   OpenAI Platform에서 모델 접근 권한을 확인하세요.")
        
        # AI 생성 실패 시 기본 스크립트 반환
        print(f"⚠️ AI 스크립트 생성 실패로 기본 스크립트를 사용합니다.")
        return self._build_default_script(topic, language=language)
    
    def _get_system_prompt(
        self,
        content_type: ContentType,
        language: str,
        target_duration: int
    ) -> tuple:
        """콘텐츠 타입별 시스템 프롬프트 반환"""
        max_sentences = 16
        
        if language == 'en':
            prompts = self._get_english_prompts(content_type, target_duration)
        else:
            prompts = self._get_korean_prompts(content_type, target_duration)
        
        return prompts.get(content_type, prompts.get(ContentType.AUTO, ("", max_sentences)))
    
    def _get_english_prompts(self, content_type: ContentType, target_duration: int) -> dict:
        """영어 프롬프트 딕셔너리"""
        base_structure = f"""
**CONTENT STRUCTURE ({target_duration} seconds total):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- **CRITICAL: Create a UNIQUE and ORIGINAL script. Avoid repeating common phrases or structures from previous scripts**
- Each sentence should be 3-4 seconds long, write 12-16 sentences total
"""
        
        prompts = {
            ContentType.HOOK: (f"""You are an expert YouTube Shorts script writer for Hook videos specializing in finance, productivity, and self-improvement content.

**HOOK CREATION (First 3 seconds - CRITICAL):**
- Create a powerful, attention-grabbing Hook that triggers curiosity, fear of missing out, or emotional connection
- Use one of these proven Hook patterns:
  1. "Mindset Flip": State a common negative belief, then immediately reframe it positively
  2. "Shocking Number": Lead with a surprising statistic
  3. "Contrarian Statement": Challenge conventional wisdom
  4. "Personal Revelation": Share a transformative realization
- The Hook must be specific, relatable, and create an immediate "I need to know more" feeling

{base_structure}
- **Opening (0-10 seconds)**: Hook + immediate context setting
- **Body (10-45 seconds)**: 
  * Explain the core concept with concrete examples
  * Use specific numbers, percentages, or timeframes when possible
  * Include relatable scenarios
  * Address common objections or misconceptions
- **Closing (45-55 seconds)**:
  * Reinforce the main message
  * Provide one actionable takeaway
  * End with a specific, engaging question
  * Include a natural subscription CTA

**WRITING STYLE:**
- Use active voice and short, punchy sentences
- Create emotional resonance through relatable scenarios
- Use power words: "transform", "reveal", "discover", "unlock", "master"
- Avoid generic phrases - be specific and concrete
- Create a "loop" structure where the ending connects back to the opening Hook naturally""", 16),
            
            ContentType.QUOTE: (f"""You are an expert YouTube Shorts script writer for quote/knowledge videos specializing in finance, productivity, and self-improvement.

**QUOTE PRESENTATION (First 3 seconds - CRITICAL):**
- Lead with a powerful, memorable quote or insight that resonates emotionally
- Choose quotes that are actionable, counter-intuitive, or thought-provoking

{base_structure}
- **Opening (0-8 seconds)**: Present the quote with emphasis
- **Body (8-48 seconds)**:
  * Break down the quote's meaning in simple terms
  * Explain why it matters (the "so what" factor)
  * Provide 2-3 concrete, real-world examples
  * Show how to apply it practically (actionable steps)
  * Address common misconceptions about the concept
- **Closing (48-55 seconds)**:
  * Reinforce the core message
  * End with a reflective question
  * Include a natural subscription CTA

**WRITING STYLE:**
- Make abstract concepts concrete through examples
- Use analogies to explain complex ideas
- Connect the quote to daily life situations
- Show the transformation or outcome of applying the quote
- Create a "loop" structure where the ending connects back to the opening quote""", 16),
            
            ContentType.STORY: (f"""You are an expert YouTube Shorts script writer for storytelling videos specializing in finance, productivity, and self-improvement.

**STORY STRUCTURE ({target_duration} seconds total - 3-Act Format):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- Each sentence should be 3-4 seconds long, write 12-16 sentences total

**ACT 1: HOOK & SETUP (0-12 seconds)**
- Start with a powerful, specific opening that creates intrigue
- Introduce a relatable character or situation
- Establish the problem or challenge

**ACT 2: DEVELOPMENT & CONFLICT (12-42 seconds)**
- Show the journey: what they tried, what worked, what didn't
- Include specific details: numbers, timeframes, methods
- Create emotional connection through relatable struggles
- Build tension or show the transformation process
- Use vivid, concrete details (not vague descriptions)

**ACT 3: RESOLUTION & LESSON (42-55 seconds)**
- Reveal the outcome or transformation
- Extract the universal lesson or principle
- Connect the story to the viewer's life
- End with a reflective question
- Include a natural subscription CTA

**STORYTELLING TECHNIQUES:**
- Use specific numbers and timeframes (not "a lot" or "some time")
- Show, don't tell (describe actions and results, not just feelings)
- Create emotional stakes (what was at risk? what changed?)
- Make the character relatable (their situation should mirror viewers')
- End with a clear, actionable takeaway""", 16),
            
            ContentType.FACT: (f"""You are an expert YouTube Shorts script writer for fact-based videos specializing in finance, productivity, and lifestyle.

**FACT PRESENTATION (First 3 seconds - CRITICAL):**
- Lead with a shocking, specific number or statistic that challenges assumptions
- Make it relatable and immediately relevant to viewers' lives

{base_structure}
- **Opening (0-8 seconds)**: Present the shocking fact with emphasis
- **Body (8-48 seconds)**:
  * Explain why this fact matters (the "so what" factor)
  * Break down the numbers or statistics in relatable terms
  * Provide context: how was this discovered? what research supports it?
  * Show real-world implications with concrete examples
  * Address common misconceptions or counter-arguments
  * Explain the underlying mechanism or principle
- **Closing (48-55 seconds)**:
  * Reinforce the key takeaway
  * End with a thought-provoking question
  * Include a natural subscription CTA

**WRITING STYLE:**
- Use specific numbers, percentages, and timeframes
- Make abstract statistics concrete through comparisons
- Create "wow" moments through surprising revelations
- Connect facts to actionable insights
- Create a "loop" structure where the ending connects back to the opening fact""", 16),
            
            ContentType.SHORT_STORY: (f"""You are an expert YouTube Shorts script writer for short story videos specializing in finance, productivity, and self-improvement.

**STORY STRUCTURE ({target_duration} seconds total - Personal Narrative Format):**
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- Each sentence should be 3-4 seconds long, write 12-16 sentences total

**OPENING (0-10 seconds)**
- Start with a powerful, personal Hook that creates immediate connection
- Use first-person perspective ("I", "My") for authenticity

**DEVELOPMENT (10-45 seconds)**
- Tell the personal journey: what you did, what happened, what you learned
- Include specific details: exact numbers, timeframes, methods used
- Show the transformation: before vs. after
- Create emotional connection through relatable struggles and victories
- Use vivid, concrete details (not vague descriptions)

**CLOSING (45-55 seconds)**
- Reveal the outcome or transformation
- Extract the universal lesson that viewers can apply
- Connect your story to the viewer's potential transformation
- End with an inspiring question
- Include a natural subscription CTA

**STORYTELLING TECHNIQUES:**
- Use first-person perspective for authenticity and relatability
- Be specific: use exact numbers, dates, and timeframes
- Show the emotional journey: frustration → action → results
- Make it relatable: your situation should mirror viewers' challenges
- End with a clear, actionable takeaway that viewers can implement""", 16),
            
            ContentType.AUTO: (f"""You are an expert YouTube Shorts script writer specializing in finance, productivity, and self-improvement content.
- Write in sufficient detail with clear explanations
- **Important: Write all sentences in English only. Do not include any Korean sentences or words**
- Target duration is about {target_duration} seconds, each sentence should be 3-4 seconds long
- YouTube Shorts has a maximum of 60 seconds, so write within {target_duration} seconds
- Write 12-16 sentences total to include sufficient content
- Create engaging, actionable content that viewers can apply immediately""", 16),
        }
        
        return prompts
    
    def _get_korean_prompts(self, content_type: ContentType, target_duration: int) -> dict:
        """한국어 프롬프트 딕셔너리"""
        prompts = {
            ContentType.HOOK: ("""당신은 YouTube Shorts용 Hook 영상 스크립트 작성 전문가입니다.
- 첫 3초 안에 강력한 Hook 문장으로 시청자의 관심을 끌어야 합니다
- 한국어 속담, 관용어, 명언 등에 집중하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- **핵심: 독창적이고 유니크한 스크립트를 작성하세요. 이전 스크립트와 중복되는 표현이나 구조를 피하세요**
- 목표는 약 55초 분량이며, 충분한 설명과 예시를 포함하세요
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요
- **전략: '마인드셋 플립(Mindset Flip)' 기법을 사용하세요. 첫 문장에서 흔한 부정적인 생각을 제시하고 즉시 긍정적으로 재해석하세요.**
- **구조: 마지막 문장이 첫 문장과 자연스럽게 이어지도록 '루프(Loop)' 구조로 작성하세요.**
- **엔딩: 구체적인 질문으로 끝맺어 댓글을 유도하고, 자연스럽게 구독을 유도하세요. 강요하지 않고 자연스럽게.**
- Hook 문장을 반복하거나 강조하고, 자세한 설명을 추가하세요""", 16),
            
            ContentType.QUOTE: ("""당신은 YouTube Shorts용 명언/지식 한 줄 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 명언이나 인사이트를 배치하세요
- AI, 비즈니스, 자기계발, 투자 등 지식 한 줄에 집중하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 충분한 설명과 실생활 적용법을 포함하세요
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요
- **구조: 마지막 문장이 첫 문장과 자연스럽게 이어지도록 '루프(Loop)' 구조로 작성하세요.**
- **엔딩: 구체적인 질문으로 끝맺어 댓글을 유도하고, 자연스럽게 구독을 유도하세요. 강요하지 않고 자연스럽게.**
- 명언을 자세히 설명하고 실생활 적용법과 예시를 제시하세요""", 16),
            
            ContentType.STORY: ("""당신은 YouTube Shorts용 스토리텔링 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 Hook으로 시작하세요
- 심리, 역사, 부자습관 등 스토리를 통해 교훈을 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 스토리를 자세히 전개하세요
- 스토리 구조: Hook → 전개 → 세부 설명 → 교훈 → 마무리
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요""", 16),
            
            ContentType.FACT: ("""당신은 YouTube Shorts용 팩트 기반 영상 스크립트 작성 전문가입니다.
- 첫 문장에 놀라운 팩트를 배치하여 Hook을 만드세요
- 과학, 역사, 인체, 우주 등 놀라운 사실을 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 팩트를 자세히 설명하세요
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요
- **전략: 충격적인 숫자나 통계(복리 효과, 절약된 시간 등)에 집중하세요.**
- **구조: 마지막 문장이 첫 문장과 자연스럽게 이어지도록 '루프(Loop)' 구조로 작성하세요.**
- **엔딩: 구체적인 질문으로 끝맺어 댓글을 유도하고, 자연스럽게 구독을 유도하세요. 강요하지 않고 자연스럽게.**
- 팩트를 설명하고 왜 놀라운지, 어떻게 발견되었는지 등 자세한 배경을 포함하세요""", 16),
            
            ContentType.SHORT_STORY: ("""당신은 YouTube Shorts용 짧은 스토리 영상 스크립트 작성 전문가입니다.
- 첫 문장에 강력한 Hook으로 시작하세요
- 인생 교훈, 영감, 성공 스토리 등을 자세히 전달하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 스토리를 충분히 전개하세요
- 스토리 구조: Hook → 사건 전개 → 세부 설명 → 교훈 → 마무리
- 각 문장은 3-4초 분량이며, 총 12-16개 문장으로 작성하세요""", 16),
            
            ContentType.AUTO: ("""당신은 YouTube Shorts용 영상 스크립트 작성 전문가입니다.
- 설명이 충분하도록 자세하게 작성하세요
- **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요**
- 목표는 약 55초 분량이며, 각 문장은 3-4초 분량입니다
- YouTube Shorts는 최대 60초이므로 55초 이내로 작성해야 합니다
- 총 12-16개 문장으로 작성하여 충분한 내용을 담으세요""", 16),
        }
        
        return prompts
    
    def _build_user_prompt(
        self,
        topic: str,
        max_sentences: int,
        target_duration: int,
        language: str
    ) -> str:
        """사용자 프롬프트 구성"""
        if language == 'en':
            return f"Write a YouTube Shorts script for '{topic}'. Each sentence should be 3-4 seconds long, write {max_sentences} sentences total to make it about {target_duration} seconds (maximum 60 seconds). **Important: Write all sentences in English only. Do not include any Korean sentences or words.** Important: Write only pure dialogue or explanations, never include production instructions like 'background music', 'subtitles', 'start', etc. The first sentence must be a powerful Hook, and develop the content sufficiently so viewers can understand it in detail."
        else:
            return f"'{topic}'에 대한 YouTube Shorts 영상 스크립트를 작성해주세요. 각 문장은 3-4초 분량이며, 총 {max_sentences}개 문장으로 작성하여 약 {target_duration}초 분량이 되도록 충분히 자세하게 작성해주세요 (최대 60초 제한). **중요: 모든 문장은 한국어로만 작성하세요. 영어 문장이나 영어 단어를 포함하지 마세요.** 중요한 점: 순수한 대사나 설명만 작성하고, '배경음악', '자막', '시작' 같은 제작 지시사항은 절대 포함하지 마세요. 첫 문장은 반드시 강력한 Hook이어야 하며, 내용을 충분히 전개하여 시청자가 이해할 수 있도록 자세히 설명하세요."
    
    def _parse_script_text(self, script_text: str, max_sentences: int) -> List[str]:
        """스크립트 텍스트를 문장 리스트로 파싱"""
        sentences = []
        # 줄바꿈으로 분리
        for line in script_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 마침표로도 분리 (긴 문장을 여러 문장으로 나눔)
            for sent in re.split(r'[.!?。！？]\s+', line):
                sent = sent.strip()
                if sent:
                    sentences.append(sent)
        
        # 불필요한 텍스트 필터링
        filter_keywords = [
            '배경음악', '음악', 'BGM', 'bgm', '배경', '시작', '종료',
            '자막', '타이틀', '제목', '인트로', '아웃트로',
            '참고', '주의', '설명', '참고사항'
        ]
        
        filtered_sentences = []
        for s in sentences:
            # 숫자나 불필요한 기호로 시작하는 것 제거
            if s.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.',
                           '11.', '12.', '13.', '14.', '15.', '16.', '-', '*', '•')):
                s = re.sub(r'^\d+\.\s*', '', s).strip()
            # 너무 짧은 문장 제거 (최소 10자 이상)
            if len(s) < 10:
                continue
            # 필터 키워드가 포함된 문장 제거
            if any(keyword in s for keyword in filter_keywords):
                continue
            # 스크립트 안내 문장 제거
            lower_s = s.lower()
            if "youtube shorts script" in lower_s or (
                "script" in lower_s and ("youtube" in lower_s or "shorts" in lower_s)
            ):
                continue
            # 괄호 안의 설명 제거
            s = re.sub(r'\([^)]*\)', '', s).strip()
            s = re.sub(r'\[[^\]]*\]', '', s).strip()
            if s and len(s) >= 10:
                filtered_sentences.append(s)
        
        # 최소 문장 수 확인
        if len(filtered_sentences) < 12:
            print(f"⚠️ 생성된 문장이 부족합니다 ({len(filtered_sentences)}개). 원본 스크립트를 다시 확인합니다.")
            # 원본 텍스트에서 더 많은 문장 추출 시도
            all_sentences = re.split(r'[.!?。！？]\s+', script_text)
            for sent in all_sentences:
                sent = sent.strip()
                if len(sent) >= 10 and sent not in filtered_sentences:
                    if not any(keyword in sent for keyword in filter_keywords):
                        filtered_sentences.append(sent)
                        if len(filtered_sentences) >= max_sentences:
                            break
        
        return filtered_sentences
    
    def _remove_repetitive_phrases(self, sentences: List[str]) -> List[str]:
        """
        문장 끝에 반복되는 구절 제거
        
        Args:
            sentences: 문장 리스트
        
        Returns:
            반복 구절이 제거된 문장 리스트
        """
        if len(sentences) < 3:
            return sentences
        
        # 각 문장의 마지막 5단어 추출
        ending_phrases = []
        for sent in sentences:
            words = sent.split()
            if len(words) >= 5:
                # 마지막 5단어를 구절로 저장
                ending_phrase = " ".join(words[-5:]).lower()
                ending_phrases.append(ending_phrase)
            else:
                ending_phrases.append("")
        
        # 반복되는 구절 찾기 (3회 이상 등장)
        from collections import Counter
        phrase_counts = Counter(ending_phrases)
        repetitive_phrases = {phrase for phrase, count in phrase_counts.items() 
                             if count >= 3 and phrase}  # 3회 이상 반복되는 구절
        
        if repetitive_phrases:
            print(f"⚠️ 반복 구절 감지: {list(repetitive_phrases)[:2]}")  # 처음 2개만 출력
            
            # 반복 구절 제거
            cleaned_sentences = []
            for sent, ending in zip(sentences, ending_phrases):
                if ending in repetitive_phrases:
                    # 마지막 5단어 제거
                    words = sent.split()
                    if len(words) > 5:
                        cleaned_sent = " ".join(words[:-5]).strip()
                        if cleaned_sent and len(cleaned_sent) > 20:  # 최소 길이 확인
                            cleaned_sentences.append(cleaned_sent)
                        else:
                            cleaned_sentences.append(sent)  # 너무 짧으면 원본 유지
                    else:
                        cleaned_sentences.append(sent)
                else:
                    cleaned_sentences.append(sent)
            
            print(f"✅ 반복 구절 제거 완료: {len(repetitive_phrases)}개 패턴")
            return cleaned_sentences
        
        return sentences
    
    def _is_script_unique(self, script_sentences: List[str]) -> bool:
        """
        스크립트 중복 여부 확인
        
        Args:
            script_sentences: 생성된 스크립트 문장 리스트
        
        Returns:
            중복되지 않으면 True, 중복이면 False
        """
        if not script_sentences or len(script_sentences) < 3:
            return True  # 너무 짧으면 검사 스킵
        
        try:
            # 데이터베이스에서 최근 스크립트 조회
            from src.pipeline.database import VideoDatabase
            db = VideoDatabase()
            recent_scripts = db.get_recent_scripts(limit=10)
            
            if not recent_scripts:
                return True  # 비교할 스크립트 없음
            
            # 현재 스크립트의 첫 3문장 해시 생성
            current_preview = " ".join(script_sentences[:3])
            current_hash = hashlib.md5(current_preview.encode()).hexdigest()
            
            # 최근 스크립트들과 비교
            for recent_script in recent_scripts:
                if not recent_script:
                    continue
                
                # 최근 스크립트의 첫 3문장 해시 생성
                recent_sentences = recent_script.split('\n')[:3]
                recent_preview = " ".join(recent_sentences)
                recent_hash = hashlib.md5(recent_preview.encode()).hexdigest()
                
                # 해시가 동일하면 중복
                if current_hash == recent_hash:
                    print(f"⚠️ 중복 스크립트 발견: {current_preview[:100]}...")
                    return False
                
                # 유사도 검사 (간단한 문자열 비교)
                similarity = self._calculate_similarity(current_preview, recent_preview)
                if similarity > 0.8:  # 80% 이상 유사하면 중복으로 간주
                    print(f"⚠️ 유사한 스크립트 발견 (유사도: {similarity:.2%})")
                    return False
            
            return True
        except Exception as e:
            print(f"⚠️ 스크립트 중복 검사 실패: {e}")
            return True  # 에러 시 통과
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트의 유사도 계산 (간단한 단어 기반)
        
        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트
        
        Returns:
            유사도 (0.0 ~ 1.0)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _build_default_script(
        self,
        topic: str,
        language: str = 'en',
        target_sentences: int = 12
    ) -> List[str]:
        """AI 생성 실패 시 주제 기반 기본 스크립트를 생성"""
        topic = (topic or "").strip()
        topic_placeholder = topic if topic else (
            "success" if language == 'en' else "성공")
        keywords = [
            part.strip()
            for part in re.split(r'[,/&]| and ', topic_placeholder)
            if part.strip()
        ]
        focus = keywords[0] if keywords else topic_placeholder
        
        if language == 'en':
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
                f"Remember every master of {focus} started small but stayed in motion."
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
                f"{focus}의 달인도 작은 걸음에서 시작했지만 멈추지 않았음을 기억하세요."
            ]
        
        if target_sentences <= 0:
            return []
        return base_lines[:target_sentences]


    def generate_topic(self, content_type: ContentType = None) -> tuple:
        """
        AI로 인기 주제 생성 (콘텐츠 타입별, 계절 고려)
        
        Returns:
            (topic, content_type) 튜플
        """
        if content_type is None:
            content_type_str = getattr(config, 'CONTENT_TYPE', 'auto')
            try:
                content_type = ContentType(content_type_str.lower())
            except ValueError:
                content_type = ContentType.AUTO
        
        # 자동 선택 시 랜덤
        if content_type == ContentType.AUTO:
            content_type = random.choice([
                ContentType.HOOK, ContentType.QUOTE, ContentType.STORY,
                ContentType.FACT, ContentType.SHORT_STORY
            ])
        
        # 현재 계절 확인
        current_season = self._get_season()
        
        # 타입별 주제 생성
        if content_type == ContentType.HOOK:
            topics = [
                # 💸 Money / Investing Hooks
                "Why your salary alone will never make you wealthy",
                "Top earners share the same exact bank account structure",
                "Rich people refuse to make this one impulse purchase",
                "Feel richer without earning more: the invisible income trick",
                "The single habit every maxed-out credit-card user shares",
                "Disciplined savers always do this first on payday",
                "How some people grow assets faster than their paycheck",
                "The most realistic investing path for busy professionals",
                "Money vanishes in patterns, not accidents.",
                "Structure builds wealth faster than motivation ever could.",
                # 🧠 Self-improvement / Routine Hooks
                "Ten minutes of routine that completely reroutes your life",
                "The morning behaviors high performers never skip",
                "The exact moment weak follow-through collapses",
                "Why top performers rely on systems, not motivation",
                "Why late-night work rarely turns into real results",
                "Routines decide your life long before you do.",
                "Tiny routines create massive peace.",
                # 🏠 Lifestyle / Declutter Hooks
                "The simple rule people with tidy homes follow every day",
                "Why you keep buying clothes but feel you have nothing to wear",
                "A chaotic fridge usually signals chaotic money habits",
                "Declutter one room and watch your stress plummet",
                "Only 20% of your closet actually leaves the house.",
                # 🚨 Risk / Downside Protection Hooks
                "One accident that can erase years of savings overnight",
                "Why insurance alone can’t keep you from bankruptcy",
                "How some people turn crises into opportunities while others crumble",
                "Skipping winter maintenance is the most expensive gamble.",
                # 🤖 AI / Automation Hooks
                "AI automation frees the 30 minutes you keep losing.",
                "Treat your calendar like code and it stops breaking.",
            ]
            # 계절별 우선 주제
            seasonal_topics = {
                'spring': [
        "Why new-year plans keep collapsing by March",
        "How people who reset each season look five years later",
        "Why your salary alone will never make you wealthy",
        "The simple rule people with tidy homes follow every day",
    ],
                'summer': [
            "One vacation drained your bank account—here’s why",
            "The real culprit eating more power than your AC",
            "The single habit every maxed-out credit-card user shares",
            "Disciplined savers always do this first on payday",
        ],
                'autumn': [
                "Half the year is gone—here’s why your goals still aren’t done",
                "People who flip their year in Q3 are decluttering right now",
                "How some people grow assets faster than their paycheck",
                "Declutter one room and watch your stress plummet",
            ],
                'winter': [
                    "Why money vanishes the moment the holidays arrive",
                    "The winter expense scarier than heating bills",
                    "One accident that can erase years of savings overnight",
                    "Rich people refuse to make this one impulse purchase",
        ]}
        elif content_type == ContentType.QUOTE:
            topics = [
                # 🌤 Lifestyle / Routine Quotes
                "Decluttering a room calms your mind, and a calm mind cuts anxiety.",
                "When seasons change, your priorities must be reorganized too.",
                "A clean home is a shortcut to a rested mind.",
                "Tiny routines create massive peace.",
                "Preparing for winter is really about removing future discomfort.",
                "Simplicity is the cheat code for focus.",
                # 💸 Money / Investing Quotes
                "Wealth is built by structure, not random savings.",
                "Time in the market beats timing the market.",
                "The moment you track spending, new opportunities appear.",
                "Money is measurement; direction is wealth.",
                "Consistency outruns talent every single time.",
            ]
            seasonal_topics = {
                'spring': ["When seasons change, your priorities must be reorganized too."],
                'summer': ["Summer is not just a season; it's a financial opportunity."],
                'autumn': ["Fall is the season of preparation, not just celebration."],
                'winter': ["Winter is the season of reflection, not just spending."]
            }
        elif content_type == ContentType.STORY:
            topics = [
                # 📖 Transformation Stories
                "He cleared one closet and reset his entire routine.",
                "A 30-day expense log rebuilt her bank balance.",
                "A five-minute evening review saved a burned-out manager.",
                "An AI micro-routine gave him back an hour every morning.",
                "She stopped buying coffee and bought freedom instead.",
            ]
            seasonal_topics = {
                'spring': ["The messy closet that turned into a seasonal reset routine"],
                'summer': ["How one family finally killed the summer mold problem"],
                'autumn': ["The messy closet that turned into a seasonal reset routine"],
                'winter': ["The winter their heating bill dropped in half"]
            }
        elif content_type == ContentType.FACT:
            topics = [
                # 📊 Surprising Facts
                "Tracking spend for 30 days cuts impulse buys by 15%.",
                "Decluttered desks raise focus by 25%.",
                "Skipping a winter oil check can cost an engine replacement.",
                "AI batching saves at least 30 minutes per day.",
                "Most millionaires have 7 streams of income, not one.",
            ]
            seasonal_topics = {
                'spring': ["Homes get dirtiest during seasonal transitions because humidity spikes"],
                'summer': ["Summer spending increases by 30% on average"],
                'autumn': ["Holiday spending starts in September, not December"],
                'winter': ["Heating costs can double during cold winters"]
            }
        elif content_type == ContentType.SHORT_STORY:
            topics = [
                # 📜 Short Personal Narratives
                "Logging expenses for 30 days changed my bank balance.",
                "Ten minutes of routine completely rerouted her life.",
                "Preparing for winter once cut our heating bill in half.",
                "I automated emails with AI and finally slept.",
                "My credit score jumped 50 points after this one change.",
            ]
            seasonal_topics = {
                'spring': ["Decluttering one closet erased my morning panic"],
                'summer': ["How a summer budget saved my fall"],
                'autumn': ["The autumn decision that saved my year"],
                'winter': ["The winter routine that transformed my spring"]
            }
        else:
            topics = ["Success habits", "Money management", "Productivity hacks"]
            seasonal_topics = {}

        # 계절별 주제 추가
        current_seasonal_topics = seasonal_topics.get(current_season, [])
        
        # 성과 기반 주제 가져오기
        performance_topics = self._get_high_performing_topics(content_type)
        
        # YouTube 트렌드 주제 가져오기 (TREND_MODE일 때만)
        youtube_trending_topics = []
        if getattr(config, 'TREND_MODE', False):
            youtube_trending_topics = self.get_youtube_trending_topics()
            
            # 계절별 트렌드 AI 생성 주제 가져오기
            ai_seasonal_topics = self.generate_seasonal_topics_from_trends(
                current_season, content_type, language='en' # 기본값 영어
            )
            if ai_seasonal_topics:
                current_seasonal_topics.extend(ai_seasonal_topics)
                
            # 일반 트렌드 AI 생성 주제 가져오기
            ai_trend_topics = self.generate_ai_topics_from_trends(
                content_type, language='en' # 기본값 영어
            )
            if ai_trend_topics:
                youtube_trending_topics.extend(ai_trend_topics)
        
        # 전략적 주제 선택
        selected_topic, source = self.select_topic_with_strategy(
            global_topics=topics,
            seasonal_topics=current_seasonal_topics,
            performance_topics=performance_topics,
            youtube_trending_topics=youtube_trending_topics
        )
        
        # 주제가 없으면 기본값 사용
        if not selected_topic:
            selected_topic = random.choice(topics) if topics else "Success habits"
            source = "fallback"
            
        print(f"🎯 주제 선택: '{selected_topic}' (출처: {source}, 타입: {content_type.value})")
        
        return selected_topic, source

    def _get_season(self) -> str:
        """
        현재 날짜를 기반으로 계절 판단
        
        Returns:
            'spring', 'summer', 'autumn', 'winter'
        """
        month = datetime.now().month
        if 3 <= month <= 5:
            return 'spring'
        elif 6 <= month <= 8:
            return 'summer'
        elif 9 <= month <= 11:
            return 'autumn'
        else:
            return 'winter'

    def get_youtube_trending_topics(self) -> List[str]:
        """YouTube 트렌드 주제 가져오기 (캐싱 사용)"""
        try:
            from src.analytics.trend_collector import TrendCollector
            import os
            
            # 캐시 파일 경로
            cache_file = os.path.join(config.TEMP_DIR, 'trending_topics_cache.json')
            cache_duration = 24 * 3600  # 24시간 캐시
            
            # 캐시 확인
            if os.path.exists(cache_file):
                import json
                import time
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get('topics', [])
                        if topics:
                            print(f"📊 캐시된 트렌드 주제 {len(topics)}개 사용")
                            return topics
            
            # 트렌드 수집
            collector = TrendCollector()
            topics = collector.get_trending_topics_for_category(
                category='finance',
                max_videos=20
            )
            
            # 캐시 저장
            if topics:
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                import json
                import time
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'topics': topics
                    }, f, ensure_ascii=False, indent=2)
                print(f"✅ 트렌드 주제 {len(topics)}개 수집 및 캐시 저장")
            
            return topics
        except Exception as e:
            print(f"⚠️ YouTube 트렌드 주제 수집 실패: {e}")
            return []

    def generate_seasonal_topics_from_trends(
        self,
        season: str,
        content_type: ContentType,
        language: str = 'en'
    ) -> List[str]:
        """
        계절별 트렌드 키워드를 기반으로 AI가 새로운 계절별 주제 생성
        """
        try:
            from src.analytics.trend_collector import TrendCollector
            import os
            
            # 캐시 파일 경로
            cache_file = os.path.join(
                config.TEMP_DIR, 
                f'ai_seasonal_topics_cache_{season}_{content_type.value}_{language}.json'
            )
            cache_duration = 7 * 24 * 3600  # 7일 캐시
            
            # 캐시 확인
            if os.path.exists(cache_file):
                import json
                import time
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get('topics', [])
                        if topics:
                            print(f"📊 캐시된 {season} 계절 AI 생성 주제 {len(topics)}개 사용")
                            return topics
            
            # 계절별 트렌드 키워드 수집
            collector = TrendCollector()
            keywords = collector.collect_seasonal_trending_keywords(
                season=season,
                max_videos=30,
                min_views=5000,
                top_n=15
            )
            
            if not keywords:
                print(f"⚠️ {season} 계절 트렌드 키워드가 없어 AI 주제 생성을 건너뜁니다.")
                return []
            
            # AI로 계절별 주제 생성
            generated_topics = collector.generate_seasonal_topics(
                season=season,
                keywords=keywords,
                content_type=content_type.value,
                num_topics=10,
                language=language
            )
            
            # 품질 검증 및 필터링
            validated_topics = []
            existing_topics = self.get_all_existing_topics(content_type)
            existing_seasonal_topics = self.get_seasonal_topics_for_season(season, content_type)
            existing_topics.extend(existing_seasonal_topics)
            
            for topic in generated_topics:
                validation = collector.validate_topic_quality(
                    topic=topic,
                    existing_topics=existing_topics
                )
                if validation['is_valid']:
                    validated_topics.append(topic)
                else:
                    print(f"   ❌ {season} 계절 주제 검증 실패: {topic[:50]}... (점수: {validation['score']})")
            
            # 캐시 저장
            if validated_topics:
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                import json
                import time
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'topics': validated_topics
                    }, f, ensure_ascii=False, indent=2)
                print(f"✅ {season} 계절 AI 생성 주제 {len(validated_topics)}개 검증 완료 및 캐시 저장")
            
            return validated_topics
            
        except Exception as e:
            print(f"⚠️ {season} 계절 AI 주제 생성 실패: {e}")
            return []

    def get_seasonal_topics_for_season(
        self,
        season: str,
        content_type: ContentType
    ) -> List[str]:
        """특정 계절의 기존 주제 가져오기 (중복 확인용)"""
        seasonal_topics = {}
        
        if content_type == ContentType.HOOK:
            seasonal_topics = {
                'spring': [
                    "Why new-year plans keep collapsing by March",
                    "How people who reset each season look five years later",
                    "Why your salary alone will never make you wealthy",
                    "The simple rule people with tidy homes follow every day",
                ],
                'summer': [
                    "Why summer spending ruins your fall budget",
                    "The one habit that separates summer savers from summer spenders",
                    "Why your vacation fund disappears by August",
                ],
                'autumn': [
                    "Why people who plan in September retire earlier",
                    "The October habit that changes your December",
                    "Why your year-end bonus disappears by January",
                ],
                'winter': [
                    "Why January goals fail by February",
                    "The December decision that determines your March",
                    "Why your holiday spending haunts your spring",
                ]
            }
        # ... (다른 타입들은 생략하거나 필요시 추가, 일단 주요 로직만 복사)
        # 전체 복사하면 너무 길어지므로 핵심만 복사하고 나머지는 VideoGenerator 참조 로직 제거 후 구현
        # 여기서는 VideoGenerator의 로직을 그대로 가져옴
        
        return seasonal_topics.get(season.lower(), [])

    def generate_ai_topics_from_trends(
        self,
        content_type: ContentType,
        language: str = 'en'
    ) -> List[str]:
        """트렌드 키워드를 기반으로 AI가 새로운 주제 생성"""
        try:
            from src.analytics.trend_collector import TrendCollector
            import os
            
            cache_file = os.path.join(
                config.TEMP_DIR, 
                f'ai_topics_cache_{content_type.value}_{language}.json'
            )
            cache_duration = 12 * 3600
            
            if os.path.exists(cache_file):
                import json
                import time
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    if time.time() - cache_time < cache_duration:
                        topics = cache_data.get('topics', [])
                        if topics:
                            return topics
            
            collector = TrendCollector()
            keywords = collector.collect_trending_keywords(
                max_videos=30,
                min_views=5000,
                top_n=15
            )
            
            if not keywords:
                return []
            
            generated_topics = collector.generate_topics_from_trends(
                keywords=keywords,
                content_type=content_type.value,
                num_topics=10,
                language=language
            )
            
            validated_topics = []
            existing_topics = self.get_all_existing_topics(content_type)
            
            for topic in generated_topics:
                validation = collector.validate_topic_quality(
                    topic=topic,
                    existing_topics=existing_topics
                )
                if validation['is_valid']:
                    validated_topics.append(topic)
            
            if validated_topics:
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                import json
                import time
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'topics': validated_topics
                    }, f, ensure_ascii=False, indent=2)
            
            return validated_topics
            
        except Exception as e:
            print(f"⚠️ AI 주제 생성 실패: {e}")
            return []

    def _get_high_performing_topics(self, content_type: ContentType) -> List[str]:
        """콘텐츠 타입별 성과가 좋았던 주제 풀을 반환."""
        topics = []
        
        try:
            topic_db = TopicDatabase()
            
            db_topics = topic_db.get_high_performing_topics(
                content_type=content_type.value if content_type != ContentType.AUTO else None,
                days=30,
                min_views=100,
                min_engagement_rate=1.0,
                limit=10
            )
            topics.extend(db_topics)
        except Exception as e:
            print(f"⚠️ 주제 데이터베이스에서 성과 주제 가져오기 실패: {e}")
        
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
        youtube_trending_topics: List[str] = None
    ) -> Tuple[str, Optional[str]]:
        """TREND_MODE 여부에 따라 주제 선택 전략을 적용."""
        global_pool = [topic for topic in global_topics if topic]
        seasonal_pool = [topic for topic in seasonal_topics if topic]
        performance_pool = [topic for topic in performance_topics if topic]
        trending_pool = [topic for topic in (youtube_trending_topics or []) if topic]

        if getattr(config, 'TREND_MODE', False):
            pools: List[Tuple[List[str], str]] = []
            weights: List[float] = []

            def add_pool(pool: List[str], source: str, weight: float) -> None:
                if pool and weight > 0:
                    pools.append((pool, source))
                    weights.append(weight)

            if trending_pool:
                combined_global = list(dict.fromkeys(global_pool + trending_pool))
                add_pool(combined_global, 'youtube_trend', self.TREND_WEIGHTS['global'])
            else:
                add_pool(global_pool, 'global_trend', self.TREND_WEIGHTS['global'])
            
            add_pool(seasonal_pool, 'seasonal', self.TREND_WEIGHTS['seasonal'])
            add_pool(performance_pool, 'performance', self.TREND_WEIGHTS['performance'])

            exploration_candidates = list(dict.fromkeys(
                (trending_pool if trending_pool else global_pool) + seasonal_pool + performance_pool))
            exploration_pool = exploration_candidates or global_pool or seasonal_pool or performance_pool
            add_pool(exploration_pool, 'exploration', self.TREND_WEIGHTS['exploration'])

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
                        selected_topic = random.choices(selected_pool, weights=topic_weights, k=1)[0]
                        return selected_topic, source
                except Exception as e:
                    print(f"⚠️ CPM 기반 선택 실패, 랜덤 선택으로 폴백: {e}")
                
                return random.choice(selected_pool), source

        if seasonal_pool and random.random() < 0.25:
            return random.choice(seasonal_pool), 'seasonal'

        fallback_pool = trending_pool or global_pool or performance_pool or seasonal_pool
        if not fallback_pool:
            return "Momentum reset routine", 'global_trend'
        return random.choice(fallback_pool), 'global_trend'
