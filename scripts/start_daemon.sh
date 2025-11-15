#!/bin/bash
# YouTube Shorts 자동 업로드 봇 데몬 시작 스크립트

cd "$(dirname "$0")"
python3 main.py schedule

