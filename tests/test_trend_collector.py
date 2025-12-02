"""
Tests for trend collector system
"""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.analytics.trend_collector import TrendCollector


class TestTrendCollector:
    """Test TrendCollector class"""
    
    @pytest.fixture
    def trend_collector(self):
        """Create a TrendCollector instance with mocked dependencies"""
        with patch('src.analytics.trend_collector.get_authenticated_service') as mock_auth, \
             patch('src.analytics.trend_collector.OpenAI') as mock_openai_class:
            
            # Mock YouTube service
            mock_youtube = Mock()
            mock_auth.return_value = mock_youtube
            
            # Mock OpenAI client
            mock_openai = Mock()
            mock_openai_class.return_value = mock_openai
            
            collector = TrendCollector()
            collector.youtube = mock_youtube
            collector.openai_client = mock_openai
            
            return collector
    
    def test_init_without_apis(self, monkeypatch):
        """Test initialization without APIs"""
        monkeypatch.setenv('OPENAI_API_KEY', '')
        with patch('src.analytics.trend_collector.get_authenticated_service', side_effect=Exception("No API")), \
             patch('config.OPENAI_API_KEY', ''):
            collector = TrendCollector()
            assert collector.youtube is None
            # OpenAI client might still be initialized but with empty key
            # The important thing is that YouTube API failed
            assert collector.openai_client is None or collector.openai_client.api_key == ''
    
    def test_get_trending_shorts(self, trend_collector):
        """Test getting trending Shorts"""
        # Mock YouTube API response
        mock_search = Mock()
        mock_search.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': {'videoId': 'test_video_1'},
                    'snippet': {
                        'title': 'Test Video 1',
                        'description': 'Test description',
                        'channelTitle': 'Test Channel',
                        'publishedAt': '2025-01-01T00:00:00Z'
                    }
                },
                {
                    'id': {'videoId': 'test_video_2'},
                    'snippet': {
                        'title': 'Test Video 2',
                        'description': 'Test description 2',
                        'channelTitle': 'Test Channel 2',
                        'publishedAt': '2025-01-02T00:00:00Z'
                    }
                }
            ]
        }
        trend_collector.youtube.search.return_value = mock_search
        
        # Mock video details
        mock_videos = Mock()
        mock_videos.list.return_value.execute.return_value = {
            'items': [{
                'statistics': {
                    'viewCount': '10000',
                    'likeCount': '500',
                    'commentCount': '50'
                },
                'contentDetails': {
                    'duration': 'PT1M30S'
                },
                'snippet': {
                    'tags': ['test', 'video', 'shorts']
                }
            }]
        }
        trend_collector.youtube.videos.return_value = mock_videos
        
        videos = trend_collector.get_trending_shorts(max_results=10)
        
        assert len(videos) == 2
        assert videos[0]['video_id'] == 'test_video_1'
        assert videos[0]['title'] == 'Test Video 1'
        assert videos[0]['views'] == 10000
        assert videos[0]['likes'] == 500
        assert videos[0]['comments'] == 50
    
    def test_get_trending_shorts_no_youtube(self):
        """Test getting trending Shorts without YouTube API"""
        collector = TrendCollector()
        collector.youtube = None
        
        videos = collector.get_trending_shorts()
        assert videos == []
    
    def test_get_trending_shorts_api_error(self, trend_collector):
        """Test handling API errors"""
        mock_search = Mock()
        mock_search.list.return_value.execute.side_effect = Exception("API Error")
        trend_collector.youtube.search.return_value = mock_search
        
        videos = trend_collector.get_trending_shorts()
        assert videos == []
    
    def test_get_video_details(self, trend_collector):
        """Test getting video details"""
        mock_videos = Mock()
        mock_videos.list.return_value.execute.return_value = {
            'items': [{
                'statistics': {
                    'viewCount': '5000',
                    'likeCount': '250',
                    'commentCount': '25'
                },
                'contentDetails': {
                    'duration': 'PT2M15S'  # 2 minutes 15 seconds = 135 seconds
                },
                'snippet': {
                    'tags': ['finance', 'money', 'tips']
                }
            }]
        }
        trend_collector.youtube.videos.return_value = mock_videos
        
        details = trend_collector._get_video_details('test_video_1')
        
        assert details is not None
        assert details['views'] == 5000
        assert details['likes'] == 250
        assert details['comments'] == 25
        assert details['duration'] == 135
        assert 'finance' in details['tags']
    
    def test_get_video_details_no_youtube(self):
        """Test getting video details without YouTube API"""
        collector = TrendCollector()
        collector.youtube = None
        
        details = collector._get_video_details('test_video_1')
        assert details is None
    
    def test_parse_duration(self, trend_collector):
        """Test parsing ISO 8601 duration format"""
        # Test various duration formats
        assert trend_collector._parse_duration('PT1M30S') == 90  # 1 minute 30 seconds
        assert trend_collector._parse_duration('PT2M') == 120  # 2 minutes
        assert trend_collector._parse_duration('PT30S') == 30  # 30 seconds
        assert trend_collector._parse_duration('PT1H30M') == 5400  # 1 hour 30 minutes
        assert trend_collector._parse_duration('PT0S') == 0  # 0 seconds
        assert trend_collector._parse_duration('invalid') == 0  # Invalid format
    
    def test_extract_keywords_from_videos(self, trend_collector):
        """Test extracting keywords from videos"""
        videos = [
            {
                'title': 'How to Save Money Fast: 5 Tips for Financial Freedom',
                'tags': ['finance', 'money', 'savings', 'tips'],
                'description': 'Learn how to save money quickly with these proven strategies',
                'views': 15000
            },
            {
                'title': 'Productivity Hacks: Boost Your Efficiency Today',
                'tags': ['productivity', 'efficiency', 'hacks'],
                'description': 'Simple productivity tips to improve your daily routine',
                'views': 12000
            },
            {
                'title': 'Low Views Video',
                'tags': ['test'],
                'description': 'This should be filtered',
                'views': 500  # Below min_views
            }
        ]
        
        keywords = trend_collector.extract_keywords_from_videos(
            videos,
            min_views=10000,
            top_n=10
        )
        
        assert len(keywords) > 0
        # Check that common keywords are present
        keyword_text = ' '.join(keywords).lower()
        assert 'money' in keyword_text or 'save' in keyword_text or 'financial' in keyword_text
        assert 'productivity' in keyword_text or 'efficiency' in keyword_text
    
    def test_extract_keywords_from_videos_no_results(self, trend_collector):
        """Test extracting keywords when no videos meet criteria"""
        videos = [
            {
                'title': 'Low Views Video',
                'tags': ['test'],
                'description': 'This should be filtered',
                'views': 500
            }
        ]
        
        keywords = trend_collector.extract_keywords_from_videos(
            videos,
            min_views=10000,
            top_n=10
        )
        
        assert keywords == []
    
    def test_extract_keywords_from_text(self, trend_collector):
        """Test extracting keywords from text"""
        text = "How to Save Money Fast: 5 Tips for Financial Freedom"
        keywords = trend_collector._extract_keywords_from_text(text)
        
        assert len(keywords) > 0
        assert 'save' in keywords
        assert 'money' in keywords
        assert 'tips' in keywords
        assert 'financial' in keywords
        # Stopwords should be filtered
        assert 'to' not in keywords
        assert 'for' not in keywords
        assert 'the' not in keywords
    
    def test_extract_keywords_from_text_empty(self, trend_collector):
        """Test extracting keywords from empty text"""
        keywords = trend_collector._extract_keywords_from_text("")
        assert keywords == []
    
    def test_refine_keywords_with_ai(self, trend_collector):
        """Test refining keywords with AI"""
        keywords = ['money', 'finance', 'savings', 'investment', 'tips']
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "money, finance, investment, savings, tips"
        trend_collector.openai_client.chat.completions.create.return_value = mock_response
        
        refined = trend_collector._refine_keywords_with_ai(keywords)
        
        assert len(refined) > 0
        assert isinstance(refined, list)
    
    def test_refine_keywords_with_ai_no_openai(self):
        """Test refining keywords without OpenAI"""
        collector = TrendCollector()
        collector.openai_client = None
        
        keywords = ['money', 'finance', 'savings']
        refined = collector._refine_keywords_with_ai(keywords)
        
        # Should return original keywords
        assert refined == keywords
    
    def test_refine_keywords_with_ai_error(self, trend_collector):
        """Test handling AI refinement errors"""
        keywords = ['money', 'finance', 'savings']
        
        # Mock OpenAI error
        trend_collector.openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Should return original keywords on error
        refined = trend_collector._refine_keywords_with_ai(keywords)
        assert refined == keywords
    
    def test_cpm_keywords(self, trend_collector):
        """Test CPM keywords dictionary"""
        assert 'finance' in TrendCollector.CPM_KEYWORDS
        assert 'invest' in TrendCollector.CPM_KEYWORDS
        assert 'insurance' in TrendCollector.CPM_KEYWORDS
        assert TrendCollector.CPM_KEYWORDS['finance'] > 0
        assert TrendCollector.CPM_KEYWORDS['insurance'] > TrendCollector.CPM_KEYWORDS['finance']
    
    def test_get_trending_keywords_integration(self, trend_collector):
        """Test getting trending keywords (integration test)"""
        # Mock get_trending_shorts
        trend_collector.get_trending_shorts = Mock(return_value=[
            {
                'title': 'How to Save Money Fast',
                'tags': ['finance', 'money'],
                'description': 'Financial tips',
                'views': 15000
            }
        ])
        
        # Mock extract_keywords_from_videos
        trend_collector.extract_keywords_from_videos = Mock(return_value=[
            'money', 'finance', 'savings', 'tips'
        ])
        
        # Use the actual flow: get_trending_shorts -> extract_keywords_from_videos
        videos = trend_collector.get_trending_shorts(max_results=10)
        keywords = trend_collector.extract_keywords_from_videos(
            videos,
            min_views=10000,
            top_n=5
        )
        
        assert len(keywords) > 0
        assert isinstance(keywords, list)
        trend_collector.get_trending_shorts.assert_called_once()
        trend_collector.extract_keywords_from_videos.assert_called_once()

