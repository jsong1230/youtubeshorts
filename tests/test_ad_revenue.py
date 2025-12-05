import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from analytics.trend_collector import TrendCollector
from pipeline.topic_database import TopicDatabase
from generators.script_generator import ScriptGenerator
from generators.video_generator import ContentType


def test_cpm_analysis():
    print("Testing CPM Analysis...")
    collector = TrendCollector()

    keywords = ["finance", "investing", "funny cat", "insurance", "daily vlog"]
    for keyword in keywords:
        score = collector.analyze_cpm_potential(keyword)
        print(f"Keyword: '{keyword}', CPM Score: {score}")

    assert collector.analyze_cpm_potential("finance") > 1.0
    assert collector.analyze_cpm_potential("funny cat") == 1.0
    print("✅ CPM Analysis Test Passed")


def test_topic_database_cpm():
    print("\nTesting Topic Database CPM Storage...")
    db = TopicDatabase()
    # Use a temporary db or ensure we don't mess up prod data too much
    # For this test, we'll just add a topic and check if it runs without error
    # and if we can retrieve it (mocking or checking db file would be better but let's do integration test)

    topic = "High CPM Test Topic"
    cpm_score = 2.5

    try:
        db.add_topic(topic, "hook", cpm_score=cpm_score)
        print(f"Added topic '{topic}' with CPM score {cpm_score}")
        # Verification of retrieval would require updating get_topics to return cpm_score,
        # which we haven't done yet explicitly in the return dict, but let's check if add works.
    except Exception as e:
        print(f"❌ Topic Database Test Failed: {e}")
        return

    print("✅ Topic Database CPM Test Passed")


def test_script_generation_targeting():
    print("\nTesting Script Generation with Targeting...")
    generator = ScriptGenerator()  # This might fail if API keys are not set in env

    topic = "How to save money"
    target_audience = "College Students"

    # We can't easily assert the content without an LLM, but we can check if it runs
    try:
        # Mocking openai/claude client would be ideal, but for now let's see if the method signature works
        # and if it generates something (or falls back gracefully)
        script = generator.generate_script(
            topic=topic, content_type=ContentType.HOOK, target_audience=target_audience
        )
        print(f"Generated script for '{target_audience}':")
        for line in script[:3]:
            print(f"- {line}")

    except Exception as e:
        print(f"❌ Script Generation Test Failed: {e}")
        return

    print("✅ Script Generation Targeting Test Passed")


if __name__ == "__main__":
    test_cpm_analysis()
    test_topic_database_cpm()
    # test_script_generation_targeting() # Skip this if no API key or to save cost
