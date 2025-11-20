#!/usr/bin/env python3
"""
Instagram Long-lived Token 생성 및 .env 파일 업데이트 스크립트
"""
import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

def get_token_app_id(access_token):
    """토큰에서 앱 ID 자동 감지"""
    api_version = "v19.0"
    url = f"https://graph.facebook.com/{api_version}/debug_token"
    params = {
        "input_token": access_token,
        "access_token": access_token
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json().get('data', {})
            return str(data.get('app_id'))
    except Exception as e:
        print(f"❌ 토큰 정보 조회 실패: {e}")
    return None

def generate_long_lived_token(short_token, app_id, app_secret):
    """Long-lived Token 생성"""
    api_version = "v19.0"
    url = f"https://graph.facebook.com/{api_version}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token'), data.get('expires_in', 0)
        else:
            error = response.json().get('error', {})
            raise Exception(f"코드 {error.get('code')}: {error.get('message', 'N/A')}")
    except Exception as e:
        raise Exception(f"Long-lived Token 생성 실패: {e}")

def update_env_file(env_path, long_token, app_id):
    """.env 파일 업데이트"""
    if not env_path.exists():
        print(f"❌ .env 파일을 찾을 수 없습니다: {env_path}")
        return False
    
    # .env 파일 읽기
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # INSTAGRAM_ACCESS_TOKEN 업데이트
    pattern_token = r'^INSTAGRAM_ACCESS_TOKEN=.*$'
    replacement_token = f'INSTAGRAM_ACCESS_TOKEN={long_token}'
    
    if re.search(pattern_token, content, re.MULTILINE):
        content = re.sub(pattern_token, replacement_token, content, flags=re.MULTILINE)
        print("✅ INSTAGRAM_ACCESS_TOKEN 업데이트됨")
    else:
        content += f"\nINSTAGRAM_ACCESS_TOKEN={long_token}\n"
        print("✅ INSTAGRAM_ACCESS_TOKEN 추가됨")
    
    # INSTAGRAM_APP_ID 업데이트
    if app_id:
        pattern_app_id = r'^INSTAGRAM_APP_ID=.*$'
        replacement_app_id = f'INSTAGRAM_APP_ID={app_id}'
        
        if re.search(pattern_app_id, content, re.MULTILINE):
            content = re.sub(pattern_app_id, replacement_app_id, content, flags=re.MULTILINE)
            print("✅ INSTAGRAM_APP_ID 업데이트됨")
        else:
            content += f"\nINSTAGRAM_APP_ID={app_id}\n"
            print("✅ INSTAGRAM_APP_ID 추가됨")
    
    # .env 파일 쓰기
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    print("=" * 60)
    print("Instagram Long-lived Token 생성 및 .env 업데이트")
    print("=" * 60)
    
    # 프로젝트 루트 디렉토리 찾기
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    env_path = project_root / '.env'
    
    # .env 파일 로드
    load_dotenv(dotenv_path=env_path)
    
    short_token = os.getenv('INSTAGRAM_ACCESS_TOKEN', '').strip()
    app_secret = os.getenv('INSTAGRAM_APP_SECRET', '').strip()
    
    if not short_token:
        print("❌ INSTAGRAM_ACCESS_TOKEN이 설정되지 않았습니다.")
        return
    
    if not app_secret:
        print("❌ INSTAGRAM_APP_SECRET이 설정되지 않았습니다.")
        return
    
    print(f"\n1. 토큰에서 앱 ID 자동 감지...")
    app_id = get_token_app_id(short_token)
    if not app_id:
        print("❌ 앱 ID를 찾을 수 없습니다.")
        return
    
    print(f"   ✅ 앱 ID: {app_id}")
    
    print(f"\n2. Long-lived Token 생성 중...")
    try:
        long_token, expires_in = generate_long_lived_token(short_token, app_id, app_secret)
        expires_in_days = expires_in // 86400
        
        print(f"   ✅ Long-lived Token 생성 성공!")
        print(f"   유효 기간: {expires_in_days}일")
        
        # 만료일 계산
        from datetime import datetime, timedelta
        expires_date = datetime.now() + timedelta(seconds=expires_in)
        print(f"   만료일: {expires_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n3. .env 파일 업데이트 중...")
        if update_env_file(env_path, long_token, app_id):
            print(f"   ✅ .env 파일 업데이트 완료!")
            print(f"\n" + "=" * 60)
            print(f"✅ 완료!")
            print(f"   Long-lived Token이 .env 파일에 저장되었습니다.")
            print(f"   유효 기간: {expires_in_days}일 (만료일: {expires_date.strftime('%Y-%m-%d')})")
            print(f"=" * 60)
        else:
            print(f"   ❌ .env 파일 업데이트 실패")
            
    except Exception as e:
        print(f"   ❌ 오류: {e}")

if __name__ == '__main__':
    main()

