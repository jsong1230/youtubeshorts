"""
시리즈 콘텐츠 생성 시스템
연속된 주제로 여러 영상을 생성하는 기능
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

from src.generators.video_generator import AIVideoGenerator
from src.generators.content_type import ContentType
from src.pipeline.topic_database import TopicDatabase, TopicSource
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SeriesType(Enum):
    """시리즈 타입"""
    SEQUENTIAL = "sequential"  # 순차적 시리즈 (1부, 2부, 3부...)
    THEMATIC = "thematic"  # 주제별 시리즈 (같은 주제, 다른 관점)
    TUTORIAL = "tutorial"  # 튜토리얼 시리즈 (단계별 가이드)
    CHALLENGE = "challenge"  # 챌린지 시리즈 (30일 챌린지 등)


class SeriesGenerator:
    """시리즈 콘텐츠 생성 클래스"""
    
    def __init__(self):
        self.video_generator = AIVideoGenerator()
        self.topic_db = TopicDatabase()
    
    def generate_series_topics(
        self,
        main_topic: str,
        series_type: SeriesType,
        num_episodes: int = 5,
        content_type: ContentType = ContentType.AUTO
    ) -> List[Dict]:
        """
        시리즈 주제 생성
        
        Args:
            main_topic: 메인 주제
            series_type: 시리즈 타입
            num_episodes: 에피소드 수
            content_type: 콘텐츠 타입
        
        Returns:
            시리즈 주제 리스트 (각 에피소드별 주제)
        """
        try:
            if series_type == SeriesType.SEQUENTIAL:
                return self._generate_sequential_series(main_topic, num_episodes, content_type)
            elif series_type == SeriesType.THEMATIC:
                return self._generate_thematic_series(main_topic, num_episodes, content_type)
            elif series_type == SeriesType.TUTORIAL:
                return self._generate_tutorial_series(main_topic, num_episodes, content_type)
            elif series_type == SeriesType.CHALLENGE:
                return self._generate_challenge_series(main_topic, num_episodes, content_type)
            else:
                return self._generate_sequential_series(main_topic, num_episodes, content_type)
        except Exception as e:
            logger.warning(f"⚠️ 시리즈 주제 생성 실패: {e}")
            return []
    
    def _generate_sequential_series(
        self,
        main_topic: str,
        num_episodes: int,
        content_type: ContentType
    ) -> List[Dict]:
        """순차적 시리즈 주제 생성 (1부, 2부, 3부...)"""
        try:
            # AI를 사용하여 시리즈 주제 생성
            if self.video_generator.openai_client:
                prompt = f"""Generate {num_episodes} sequential video topics for a YouTube Shorts series about: "{main_topic}"

Each episode should:
- Be a natural continuation of the previous episode
- Cover a specific aspect or step
- Be suitable for a 55-second YouTube Shorts video
- Be engaging and actionable
- Be numbered (Part 1, Part 2, etc.)

Format: Return only the topics, one per line, numbered.
Example:
1. [Topic for Part 1]
2. [Topic for Part 2]
3. [Topic for Part 3]

Main topic: {main_topic}
Number of episodes: {num_episodes}"""

                response = self.video_generator.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at creating engaging YouTube Shorts content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=500
                )
                
                topics_text = response.choices[0].message.content.strip()
                topics: List[Dict] = []
                
                for line in topics_text.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-')):
                        # 번호 제거
                        topic = line.split('.', 1)[-1].strip()
                        if topic:
                            topics.append({
                                'topic': topic,
                                'episode_number': len(topics) + 1,
                                'series_type': SeriesType.SEQUENTIAL.value,
                                'main_topic': main_topic
                            })
                
                # 요청한 수만큼 생성
                while len(topics) < num_episodes:
                    topics.append({
                        'topic': f"{main_topic} - Part {len(topics) + 1}",
                        'episode_number': len(topics) + 1,
                        'series_type': SeriesType.SEQUENTIAL.value,
                        'main_topic': main_topic
                    })
                
                return topics[:num_episodes]
            else:
                # AI 없으면 기본 시리즈 생성
                return [
                    {
                        'topic': f"{main_topic} - Part {i+1}",
                        'episode_number': i+1,
                        'series_type': SeriesType.SEQUENTIAL.value,
                        'main_topic': main_topic
                    }
                    for i in range(num_episodes)
                ]
        except Exception as e:
            logger.warning(f"⚠️ 순차적 시리즈 생성 실패: {e}")
            return [
                {
                    'topic': f"{main_topic} - Part {i+1}",
                    'episode_number': i+1,
                    'series_type': SeriesType.SEQUENTIAL.value,
                    'main_topic': main_topic
                }
                for i in range(num_episodes)
            ]
    
    def _generate_thematic_series(
        self,
        main_topic: str,
        num_episodes: int,
        content_type: ContentType
    ) -> List[Dict]:
        """주제별 시리즈 생성 (같은 주제, 다른 관점)"""
        try:
            if self.video_generator.openai_client:
                prompt = f"""Generate {num_episodes} different perspectives on the topic: "{main_topic}"

Each episode should:
- Explore a different angle or aspect of the main topic
- Be suitable for a 55-second YouTube Shorts video
- Be engaging and provide unique insights
- Not repeat the same information

Format: Return only the topics, one per line.
Example:
- [Perspective 1]
- [Perspective 2]
- [Perspective 3]

Main topic: {main_topic}
Number of episodes: {num_episodes}"""

                response = self.video_generator.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at creating engaging YouTube Shorts content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=500
                )
                
                topics_text = response.choices[0].message.content.strip()
                topics: List[Dict] = []
                
                for line in topics_text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•')):
                        topic = line.lstrip('- •').strip()
                        if topic:
                            topics.append({
                                'topic': topic,
                                'episode_number': len(topics) + 1,
                                'series_type': SeriesType.THEMATIC.value,
                                'main_topic': main_topic
                            })
                
                while len(topics) < num_episodes:
                    topics.append({
                        'topic': f"{main_topic}: {['Basics', 'Advanced', 'Tips', 'Mistakes', 'Success Stories'][len(topics) % 5]}",
                        'episode_number': len(topics) + 1,
                        'series_type': SeriesType.THEMATIC.value,
                        'main_topic': main_topic
                    })
                
                return topics[:num_episodes]
            else:
                perspectives = ['Basics', 'Advanced Tips', 'Common Mistakes', 'Success Stories', 'Expert Insights']
                return [
                    {
                        'topic': f"{main_topic}: {perspectives[i % len(perspectives)]}",
                        'episode_number': i+1,
                        'series_type': SeriesType.THEMATIC.value,
                        'main_topic': main_topic
                    }
                    for i in range(num_episodes)
                ]
        except Exception as e:
            logger.warning(f"⚠️ 주제별 시리즈 생성 실패: {e}")
            perspectives = ['Basics', 'Advanced Tips', 'Common Mistakes', 'Success Stories']
            return [
                {
                    'topic': f"{main_topic}: {perspectives[i % len(perspectives)]}",
                    'episode_number': i+1,
                    'series_type': SeriesType.THEMATIC.value,
                    'main_topic': main_topic
                }
                for i in range(num_episodes)
            ]
    
    def _generate_tutorial_series(
        self,
        main_topic: str,
        num_episodes: int,
        content_type: ContentType
    ) -> List[Dict]:
        """튜토리얼 시리즈 생성 (단계별 가이드)"""
        try:
            if self.video_generator.openai_client:
                prompt = f"""Generate {num_episodes} step-by-step tutorial topics for: "{main_topic}"

Each episode should:
- Be a specific step in a complete tutorial
- Build upon previous steps
- Be suitable for a 55-second YouTube Shorts video
- Be actionable and clear

Format: Return only the topics, one per line, numbered.
Example:
1. Step 1: [First step]
2. Step 2: [Second step]
3. Step 3: [Third step]

Main topic: {main_topic}
Number of episodes: {num_episodes}"""

                response = self.video_generator.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at creating step-by-step tutorials."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                topics_text = response.choices[0].message.content.strip()
                topics: List[Dict] = []
                
                for line in topics_text.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or 'Step' in line):
                        # 번호나 Step 제거
                        topic = line.split(':', 1)[-1].strip() if ':' in line else line
                        topic = topic.split('.', 1)[-1].strip() if '.' in topic else topic
                        if topic:
                            topics.append({
                                'topic': f"Step {len(topics) + 1}: {topic}",
                                'episode_number': len(topics) + 1,
                                'series_type': SeriesType.TUTORIAL.value,
                                'main_topic': main_topic
                            })
                
                while len(topics) < num_episodes:
                    topics.append({
                        'topic': f"Step {len(topics) + 1}: {main_topic}",
                        'episode_number': len(topics) + 1,
                        'series_type': SeriesType.TUTORIAL.value,
                        'main_topic': main_topic
                    })
                
                return topics[:num_episodes]
            else:
                return [
                    {
                        'topic': f"Step {i+1}: {main_topic}",
                        'episode_number': i+1,
                        'series_type': SeriesType.TUTORIAL.value,
                        'main_topic': main_topic
                    }
                    for i in range(num_episodes)
                ]
        except Exception as e:
            logger.warning(f"⚠️ 튜토리얼 시리즈 생성 실패: {e}")
            return [
                {
                    'topic': f"Step {i+1}: {main_topic}",
                    'episode_number': i+1,
                    'series_type': SeriesType.TUTORIAL.value,
                    'main_topic': main_topic
                }
                for i in range(num_episodes)
            ]
    
    def _generate_challenge_series(
        self,
        main_topic: str,
        num_episodes: int,
        content_type: ContentType
    ) -> List[Dict]:
        """챌린지 시리즈 생성 (30일 챌린지 등)"""
        try:
            if self.video_generator.openai_client:
                prompt = f"""Generate {num_episodes} daily challenge topics for: "{main_topic}"

Each episode should:
- Be a specific daily challenge or task
- Be suitable for a 55-second YouTube Shorts video
- Be actionable and motivating
- Show progress over time

Format: Return only the topics, one per line, numbered.
Example:
Day 1: [First challenge]
Day 2: [Second challenge]
Day 3: [Third challenge]

Main topic: {main_topic}
Number of episodes: {num_episodes}"""

                response = self.video_generator.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at creating engaging challenge content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,
                    max_tokens=500
                )
                
                topics_text = response.choices[0].message.content.strip()
                topics: List[Dict] = []
                
                for line in topics_text.split('\n'):
                    line = line.strip()
                    if line and ('Day' in line or line[0].isdigit()):
                        # Day나 번호 제거
                        topic = line.split(':', 1)[-1].strip() if ':' in line else line
                        topic = topic.split('.', 1)[-1].strip() if '.' in topic else topic
                        if topic:
                            topics.append({
                                'topic': f"Day {len(topics) + 1}: {topic}",
                                'episode_number': len(topics) + 1,
                                'series_type': SeriesType.CHALLENGE.value,
                                'main_topic': main_topic
                            })
                
                while len(topics) < num_episodes:
                    topics.append({
                        'topic': f"Day {len(topics) + 1}: {main_topic} Challenge",
                        'episode_number': len(topics) + 1,
                        'series_type': SeriesType.CHALLENGE.value,
                        'main_topic': main_topic
                    })
                
                return topics[:num_episodes]
            else:
                return [
                    {
                        'topic': f"Day {i+1}: {main_topic} Challenge",
                        'episode_number': i+1,
                        'series_type': SeriesType.CHALLENGE.value,
                        'main_topic': main_topic
                    }
                    for i in range(num_episodes)
                ]
        except Exception as e:
            logger.warning(f"⚠️ 챌린지 시리즈 생성 실패: {e}")
            return [
                {
                    'topic': f"Day {i+1}: {main_topic} Challenge",
                    'episode_number': i+1,
                    'series_type': SeriesType.CHALLENGE.value,
                    'main_topic': main_topic
                }
                for i in range(num_episodes)
            ]

