# EG-ICON V2 디지털 트윈 대시보드

## 📋 프로젝트 개요

OLED 제조공장을 위한 **모던 디지털 트윈 대시보드 시스템**입니다. V1.1의 센서 모니터링을 발전시켜 공정 중심의 실시간 모니터링과 AI 기반 예지보전 기능을 제공합니다.

### 🎯 주요 특징
- **실시간 공정 모니터링**: 7개 제조공정 실시간 상태 추적
- **AI 예지보전**: 머신러닝 기반 설비 이상 예측
- **모던 UI/UX**: React 디자인 패턴을 Flask 환경에 구현
- **오프라인 지원**: 라즈베리파이 독립 실행 환경
- **반응형 디자인**: 다양한 화면 크기 지원

## 🚀 빠른 시작

### 시스템 요구사항
- Python 3.7+
- FastAPI, Uvicorn
- 모던 웹 브라우저 (Chrome, Firefox, Safari)

### 설치 및 실행

1. **의존성 설치**:
```bash
cd v2
pip install -r requirements_prototype.txt
```

2. **개발 서버 실행**:
```bash
python main_prototype.py
```

3. **브라우저 접속**:
```
http://localhost:8002/dashboard
```

## 🏗️ 시스템 아키텍처

### 디렉토리 구조
```
v2/
├── main_prototype.py              # FastAPI 메인 서버
├── mock_data_generator.py         # Mock 데이터 생성기
├── websocket_simulator.py         # WebSocket 시뮬레이터
├── requirements_prototype.txt     # Python 의존성
├── frontend/
│   ├── dashboard.html             # 메인 대시보드 (새로운 UI)
│   ├── css/
│   │   └── modern-dashboard.css   # 모던 스타일시트
│   ├── js/
│   │   └── dashboard.js           # 실시간 업데이트 로직
│   ├── analytics.html             # 상세 분석 (개발 중)
│   ├── settings.html              # 설정 관리 (개발 중)
│   ├── users.html                 # 사용자 관리 (개발 중)
│   ├── logs.html                  # 로그 검색 (개발 중)
│   └── process_*.html             # 공정별 상세 페이지
└── docs/
    ├── README.md                  # 프로젝트 개요
    ├── DEVELOPER_GUIDE.md         # 개발자 가이드
    └── USER_GUIDE.md              # 사용자 가이드
```

### 기술 스택
- **Backend**: FastAPI, WebSocket, Python 3.7+
- **Frontend**: HTML5, CSS3 (Grid/Flexbox), Vanilla JavaScript
- **Real-time**: WebSocket 기반 실시간 데이터 업데이트
- **Data**: Mock 데이터 생성기 (개발용)

## 🌐 주요 페이지 및 기능

### 1. 메인 대시보드 (`/dashboard`)
- **KPI 지표**: 생산효율, 장비가동률, 품질지표, 에너지소비, AI 예측정확도
- **공정 현황**: 7개 공정 실시간 상태 모니터링
- **예지보전**: AI 기반 설비 이상 예측
- **알림 시스템**: 위험/주의 상태 실시간 알림

### 2. 공정별 상세 페이지
| 공정 | URL | 센서 수 | 주요 모니터링 |
|------|-----|---------|---------------|
| 실장공정 | `/process/deposition` | 6개 | 온도, 습도, 진동, 가스, 전력, 진공도 |
| 라미공정 | `/process/photo` | 4개 | 조도(상부/하부), 온도, 미세먼지 |
| 조립공정 | `/process/etch` | 8개 | 챔버온도x4, 가스농도x2, 미세먼지, 진동 |
| 검사공정 | `/process/encapsulation` | 3개 | 습도, 경화온도, 차압 |

### 3. 관리 페이지 (개발 중)
- **상세 분석** (`/analytics`): 데이터 분석 및 트렌드
- **설정 관리** (`/settings`): 시스템 설정
- **사용자 관리** (`/users`): 계정 및 권한 관리
- **로그 검색** (`/logs`): 시스템 로그 검색

## 🔧 개발 환경 설정

### 환경별 접근 방법

#### 1. 개발 환경 (Mac/PC)
```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd egicon_web/v2

# 2. Python 가상환경 설정
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 3. 의존성 설치
pip install -r requirements_prototype.txt

# 4. 개발 서버 실행
python main_prototype.py

# 5. 브라우저에서 확인
open http://localhost:8002/dashboard
```

#### 2. 라즈베리파이 배포
```bash
# 1. 프로젝트 복사
scp -r v2/ pi@<raspberry-pi-ip>:~/egicon_web/

# 2. SSH 접속
ssh pi@<raspberry-pi-ip>

# 3. 의존성 설치
cd ~/egicon_web/v2
pip install -r requirements_prototype.txt --break-system-packages

# 4. 자동 시작 설정 (선택사항)
sudo nano /etc/systemd/system/egicon-v2.service

# 5. 서비스 실행
sudo systemctl enable egicon-v2
sudo systemctl start egicon-v2
```

## 📊 V2 주요 개선사항

### UI/UX 개선
- **모던 디자인**: React 스타일 카드 기반 레이아웃
- **일관된 컬러 시스템**: 색상 팔레트 통일
- **반응형 레이아웃**: 90% 화면 너비 활용
- **타이포그래피**: 18px 기본 폰트, 계층적 텍스트 크기
- **아이콘 시스템**: 의미있는 아이콘으로 통일

### 기능 개선
- **실시간 알림**: 위험/주의 상태별 배지 표시
- **예지보전**: AI 예측 정확도 및 위험 예측
- **공정 연동**: 클릭으로 공정별 상세 페이지 이동
- **데이터 시각화**: 프로그레스 바, 트렌드 표시

### 기술적 개선
- **CSS 모듈화**: Tailwind 패턴을 순수 CSS로 변환
- **JavaScript 리팩토링**: 클래스 기반 구조
- **WebSocket 안정성**: 자동 재연결 및 에러 처리
- **코드 구조**: 컴포넌트 단위 개발

## 🔄 개발 워크플로우

### 새로운 기능 개발 시
```bash
# 1. 백업 브랜치 생성
git checkout main
git branch v2-backup-$(date +%Y%m%d)

# 2. 기능 브랜치 생성
git checkout -b feature/new-feature

# 3. 개발 진행
# 파일 수정...

# 4. 테스트
python main_prototype.py
# 브라우저에서 기능 확인

# 5. 커밋 및 푸시
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin feature/new-feature
```

### 스타일 수정 시
```bash
# CSS 파일 수정
vim frontend/css/modern-dashboard.css

# 실시간 확인 (브라우저 새로고침)
# http://localhost:8002/dashboard

# 변경사항 커밋
git add frontend/css/modern-dashboard.css
git commit -m "style: CSS 스타일 개선"
```

## 📱 브라우저 지원

| 브라우저 | 버전 | 지원 상태 |
|----------|------|-----------|
| Chrome | 80+ | ✅ 완전 지원 |
| Firefox | 75+ | ✅ 완전 지원 |
| Safari | 13+ | ✅ 완전 지원 |
| Edge | 80+ | ✅ 완전 지원 |

## 🚨 트러블슈팅

### 자주 발생하는 문제

1. **포트 충돌 (8002 포트 사용 중)**
```bash
# 포트 사용 프로세스 확인
lsof -i :8002

# 프로세스 종료
kill -9 <PID>
```

2. **WebSocket 연결 실패**
```bash
# 방화벽 설정 확인
sudo ufw status

# 포트 허용
sudo ufw allow 8002
```

3. **라즈베리파이 권한 오류**
```bash
# pip 설치 시 권한 오류
pip install --break-system-packages

# 또는 가상환경 사용
python -m venv venv
source venv/bin/activate
```

## 📞 지원 및 연락처

- **개발자**: ShinHoTechnology
- **이메일**: [연락처 정보]
- **GitHub**: [리포지토리 URL]
- **문서**: `/docs` 폴더 참조

## 📄 라이선스

[라이선스 정보]

---

**마지막 업데이트**: 2025-07-10  
**버전**: V2.1  
**상태**: 프로덕션 준비 완료