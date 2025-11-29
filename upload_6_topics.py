#!/usr/bin/env python3
"""6개 주제로 영상 생성 및 업로드"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline.bot import ShortsBot

topics = [
    'Emergency Fund Challenge: How to Save $1,000 in 90 Days Without a Second Job',
    'The Hidden Tax Deduction That Could Save You $500 This Year',
    'Why Smart Investors Buy Index Funds in December',
    'The Subscription Trap: How I Saved $2,400 by Canceling These 5 Services',
    '401k vs Roth IRA: The One Choice That Determines Your Retirement',
    'The 30-Day No-Spend Challenge That Changed My Relationship With Money'
]

bot = ShortsBot()
results = []

for i, topic in enumerate(topics, 1):
    print(f'\n\n{"="*80}')
    print(f'영상 {i}/6: {topic[:60]}...')
    print(f'{"="*80}\n')
    try:
        result = bot.create_and_upload(topic=topic, force=True)
        # result는 video_id (문자열) 또는 딕셔너리일 수 있음
        if isinstance(result, dict):
            video_id = result.get('video_id')
        else:
            video_id = result
        
        if video_id:
            results.append({'success': True, 'video_id': video_id, 'topic': topic})
            print(f'\n✅ 영상 {i}/6 업로드 완료!')
            print(f'   영상 ID: {video_id}')
            print(f'   링크: https://www.youtube.com/watch?v={video_id}')
        else:
            results.append({'success': False, 'topic': topic, 'error': 'No video_id'})
            print(f'\n❌ 영상 {i}/6 업로드 실패')
    except Exception as e:
        results.append({'success': False, 'topic': topic, 'error': str(e)})
        print(f'\n❌ 영상 {i}/6 오류: {e}')
        import traceback
        traceback.print_exc()

print(f'\n\n{"="*80}')
print('최종 결과')
print(f'{"="*80}')
success = sum(1 for r in results if r['success'])
print(f'✅ 성공: {success}개')
print(f'❌ 실패: {len(results) - success}개')
if success > 0:
    print('\n업로드된 영상:')
    for r in results:
        if r['success']:
            print(f"  - {r['topic'][:60]}...")
            print(f"    https://www.youtube.com/watch?v={r['video_id']}")

