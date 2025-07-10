# 개발자 가이드 - EG-ICON V2

## 📚 목차
1. [프로젝트 구조](#프로젝트-구조)
2. [개발 환경 설정](#개발-환경-설정)
3. [버전 관리 전략](#버전-관리-전략)
4. [개발 워크플로우](#개발-워크플로우)
5. [코드 구조 및 아키텍처](#코드-구조-및-아키텍처)
6. [API 개발 가이드](#api-개발-가이드)
7. [프런트엔드 개발 가이드](#프런트엔드-개발-가이드)
8. [테스팅 가이드](#테스팅-가이드)
9. [배포 가이드](#배포-가이드)
10. [트러블슈팅](#트러블슈팅)

## 🏗️ 프로젝트 구조

### 전체 디렉토리 구조
```
egicon_web/
├── v1/                           # V1 레거시 코드 (유지보수만)
├── v2/                           # V2 현재 개발 버전
│   ├── main_prototype.py         # FastAPI 메인 서버
│   ├── mock_data_generator.py    # Mock 데이터 생성기
│   ├── websocket_simulator.py    # WebSocket 시뮬레이터
│   ├── requirements_prototype.txt # Python 의존성
│   ├── frontend/                 # 프런트엔드 파일들
│   │   ├── dashboard.html        # 메인 대시보드
│   │   ├── css/
│   │   │   └── modern-dashboard.css
│   │   ├── js/
│   │   │   └── dashboard.js
│   │   ├── analytics.html        # 상세 분석 페이지
│   │   ├── settings.html         # 설정 관리 페이지
│   │   ├── users.html           # 사용자 관리 페이지
│   │   ├── logs.html            # 로그 검색 페이지
│   │   └── process_*.html       # 공정별 상세 페이지
│   ├── docs/                    # 문서
│   └── static/                  # 정적 파일 (이미지, 아이콘)
└── README.md                    # 프로젝트 개요
```

### 핵심 파일 설명

#### Backend Files
- `main_prototype.py`: FastAPI 메인 애플리케이션
- `mock_data_generator.py`: 개발용 가짜 데이터 생성
- `websocket_simulator.py`: 실시간 데이터 시뮬레이션

#### Frontend Files
- `dashboard.html`: React 스타일의 모던 대시보드
- `modern-dashboard.css`: Tailwind → CSS 변환된 스타일시트
- `dashboard.js`: 실시간 업데이트 및 WebSocket 통신

#### Process Pages
- `process_deposition.html`: 실장공정 (6개 센서)
- `process_photo.html`: 라미공정 (4개 센서)
- `process_etch.html`: 조립공정 (8개 센서)
- `process_encapsulation.html`: 검사공정 (3개 센서)

## ⚙️ 개발 환경 설정

### 1. 초기 설정

#### Mac/Linux 환경
```bash
# 1. 프로젝트 클론
git clone <repository-url>
cd egicon_web

# 2. Python 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate

# 3. V2 디렉토리로 이동
cd v2

# 4. 의존성 설치
pip install -r requirements_prototype.txt

# 5. 개발 서버 실행
python main_prototype.py
```

#### Windows 환경
```cmd
# 1. 프로젝트 클론
git clone <repository-url>
cd egicon_web

# 2. Python 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 3. V2 디렉토리로 이동
cd v2

# 4. 의존성 설치
pip install -r requirements_prototype.txt

# 5. 개발 서버 실행
python main_prototype.py
```

### 2. 개발 도구 설정

#### VS Code 설정 (권장)
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "files.associations": {
        "*.html": "html"
    },
    "emmet.includeLanguages": {
        "html": "html"
    }
}
```

#### 필수 VS Code 확장
- Python
- HTML CSS Support
- Live Server (프런트엔드 테스트용)
- GitLens (Git 히스토리 관리)

### 3. 환경별 포트 설정

| 환경 | 포트 | 용도 |
|------|------|------|
| 개발 (Mac/PC) | 8002 | FastAPI 서버 |
| 라즈베리파이 | 8002 | 프로덕션 서버 |
| 테스트 | 8003 | 테스트 서버 |

## 🌳 버전 관리 전략

### Git 브랜치 전략

```
main (프로덕션 준비)
├── v2 (현재 개발 브랜치)
│   ├── feature/ui-improvements
│   ├── feature/new-sensors
│   └── bugfix/websocket-connection
├── v2-backup-YYYYMMDD (안전 백업)
└── v1 (레거시, 유지보수만)
```

### 브랜치 명명 규칙
- `feature/기능명`: 새로운 기능 개발
- `bugfix/이슈명`: 버그 수정
- `hotfix/긴급수정`: 긴급 수정
- `v2-backup-날짜`: 안전 백업

### 커밋 메시지 규칙
```
type(scope): subject

feat(dashboard): 새로운 KPI 지표 추가
fix(websocket): 연결 끊김 문제 해결
style(css): 대시보드 레이아웃 개선
docs(readme): 설치 가이드 업데이트
refactor(js): dashboard.js 클래스 구조 개선
```

## 🔄 개발 워크플로우

### 1. 새로운 기능 개발

```bash
# 1. 최신 코드 동기화
git checkout v2
git pull origin v2

# 2. 백업 브랜치 생성 (중요!)
git branch v2-backup-$(date +%Y%m%d_%H%M)

# 3. 기능 브랜치 생성
git checkout -b feature/new-dashboard-widget

# 4. 개발 진행
# 파일 수정...

# 5. 로컬 테스트
python main_prototype.py
# 브라우저에서 http://localhost:8002/dashboard 확인

# 6. 커밋
git add .
git commit -m "feat(dashboard): 새로운 위젯 추가"

# 7. 푸시
git push origin feature/new-dashboard-widget

# 8. v2 브랜치에 병합
git checkout v2
git merge feature/new-dashboard-widget

# 9. 기능 브랜치 삭제
git branch -d feature/new-dashboard-widget
```

### 2. 버그 수정 워크플로우

```bash
# 1. 버그 재현
python main_prototype.py
# 브라우저에서 문제 확인

# 2. 버그픽스 브랜치 생성
git checkout -b bugfix/websocket-reconnection

# 3. 수정 작업
# 코드 수정...

# 4. 테스트
python main_prototype.py
# 문제 해결 확인

# 5. 커밋 및 병합
git add .
git commit -m "fix(websocket): 자동 재연결 로직 개선"
git checkout v2
git merge bugfix/websocket-reconnection
```

### 3. 라즈베리파이 배포 워크플로우

```bash
# 1. v2 브랜치가 안정적인지 확인
git checkout v2
python main_prototype.py  # 로컬 테스트

# 2. 라즈베리파이에 코드 전송
scp -r v2/ pi@<raspberry-pi-ip>:~/egicon_web/

# 3. SSH 접속 후 배포
ssh pi@<raspberry-pi-ip>
cd ~/egicon_web/v2
pip install -r requirements_prototype.txt --break-system-packages
python main_prototype.py

# 4. 서비스 등록 (선택사항)
sudo systemctl restart egicon-v2
```

## 🏛️ 코드 구조 및 아키텍처

### Backend 아키텍처

#### main_prototype.py 구조
```python
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 메인 페이지 라우트
@app.get("/dashboard")
async def dashboard():
    return FileResponse("frontend/dashboard.html")

# 공정별 페이지 라우트
@app.get("/process/{process_id}")
async def process_detail(process_id: str):
    return FileResponse(f"frontend/process_{process_id}.html")

# WebSocket 엔드포인트
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    # 실시간 데이터 스트리밍
```

### Frontend 아키텍처

#### dashboard.js 클래스 구조
```javascript
class FactoryDashboard {
    constructor() {
        this.ws = null;
        this.processes = [...];  // 공정 데이터
        this.kpiData = {...};    // KPI 데이터
    }
    
    // 초기화
    init() { ... }
    
    // UI 업데이트
    renderProcesses() { ... }
    updateKPI() { ... }
    updateAlertSummary() { ... }
    
    // WebSocket 통신
    connectWebSocket() { ... }
    
    // 데이터 시뮬레이션
    simulateDataUpdate() { ... }
}
```

#### CSS 아키텍처 (modern-dashboard.css)
```css
/* 1. CSS Reset */
* { margin: 0; padding: 0; box-sizing: border-box; }

/* 2. CSS Variables (색상, 간격, 그림자) */
:root {
    --color-gray-50: #f9fafb;
    --color-blue-600: #2563eb;
    /* ... */
}

/* 3. Base Styles */
body { font-family: system-ui; background: var(--color-gray-50); }

/* 4. Layout Components */
.container { width: 90%; margin: 0 auto; }
.header { background: white; box-shadow: var(--shadow-sm); }

/* 5. UI Components */
.kpi-card { background: white; border-radius: var(--rounded-lg); }
.badge { padding: 0.25rem 0.75rem; border-radius: var(--rounded); }

/* 6. Utility Classes */
.hidden { display: none; }
.updating { animation: pulse 1s infinite; }
```

## 🔌 API 개발 가이드

### 1. 새로운 엔드포인트 추가

```python
# main_prototype.py에 추가

@app.get("/api/sensors/{sensor_id}")
async def get_sensor_data(sensor_id: str):
    """특정 센서 데이터 조회"""
    # Mock 데이터 반환 또는 실제 센서 연동
    return {
        "sensor_id": sensor_id,
        "value": 23.5,
        "unit": "°C",
        "timestamp": "2025-07-10T10:30:00Z",
        "status": "normal"
    }

@app.post("/api/settings/threshold")
async def update_threshold(threshold_data: dict):
    """센서 임계값 설정"""
    # 임계값 업데이트 로직
    return {"status": "success", "message": "임계값이 업데이트되었습니다"}
```

### 2. WebSocket 메시지 형식

```javascript
// 클라이언트 → 서버
{
    "type": "ping",
    "timestamp": "2025-07-10T10:30:00Z"
}

// 서버 → 클라이언트
{
    "type": "realtime_update",
    "data": {
        "factory_kpi": {
            "production_efficiency": {"value": 94.2, "trend": "up"},
            "equipment_utilization": {"value": 87.8, "trend": "up"}
        },
        "processes": [
            {"id": "deposition", "status": "normal", "alerts": 0}
        ]
    }
}
```

### 3. 에러 핸들링

```python
from fastapi import HTTPException

@app.get("/api/process/{process_id}")
async def get_process_data(process_id: str):
    if process_id not in VALID_PROCESSES:
        raise HTTPException(status_code=404, detail="공정을 찾을 수 없습니다")
    
    try:
        data = get_process_sensor_data(process_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 조회 실패: {str(e)}")
```

## 🎨 프런트엔드 개발 가이드

### 1. 새로운 페이지 추가

#### HTML 구조
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>새로운 페이지 - 디스플레이 제조공장</title>
    <link rel="stylesheet" href="/static/css/modern-dashboard.css">
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="container">
            <div class="header-content">
                <div class="header-left">
                    <img src="/static/a.png" alt="Factory Icon" class="factory-icon" />
                    <div>
                        <h1 class="header-title">페이지 제목</h1>
                        <p class="header-subtitle">Page Subtitle</p>
                    </div>
                </div>
                <div class="header-right">
                    <div class="header-time">
                        <p class="date" id="current-date">2025년 7월 10일</p>
                        <p class="time" id="current-time">오후 2:30:45</p>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="container" style="padding-top: 2rem; padding-bottom: 2rem;">
        <!-- 페이지 컨텐츠 -->
    </main>

    <script>
        // 시간 업데이트 로직
        function updateTime() {
            const now = new Date();
            const dateStr = now.toLocaleDateString('ko-KR', {
                year: 'numeric', month: 'long', day: 'numeric'
            });
            const timeStr = now.toLocaleTimeString('ko-KR');
            
            document.getElementById('current-date').textContent = dateStr;
            document.getElementById('current-time').textContent = timeStr;
        }
        
        updateTime();
        setInterval(updateTime, 1000);
    </script>
</body>
</html>
```

#### FastAPI 라우트 추가
```python
@app.get("/새로운페이지")
async def new_page():
    return FileResponse("frontend/new_page.html")
```

### 2. 스타일 가이드

#### 색상 시스템
```css
/* 기본 색상 (modern-dashboard.css에서 사용) */
--color-gray-50: #f9fafb;     /* 배경색 */
--color-gray-900: #111827;    /* 텍스트 */
--color-blue-600: #2563eb;    /* 액센트 */
--color-green-600: #16a34a;   /* 성공 */
--color-yellow-600: #ca8a04;  /* 경고 */
--color-red-600: #dc2626;     /* 위험 */
```

#### 컴포넌트 스타일링
```css
/* 카드 컴포넌트 */
.card {
    background: white;
    border-radius: var(--rounded-lg);
    box-shadow: var(--shadow);
    border: 1px solid var(--color-gray-200);
    padding: var(--space-6);
}

/* 배지 컴포넌트 */
.badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-3);
    border-radius: var(--rounded);
    font-size: 0.875rem;
    font-weight: 500;
}

.badge-normal { background: var(--color-green-100); color: var(--color-green-800); }
.badge-warning { background: var(--color-yellow-100); color: var(--color-yellow-800); }
.badge-danger { background: var(--color-red-100); color: var(--color-red-800); }
```

### 3. JavaScript 개발 패턴

#### 클래스 기반 구조
```javascript
class NewPageController {
    constructor() {
        this.data = {};
        this.ws = null;
        this.init();
    }
    
    init() {
        this.loadData();
        this.setupEventListeners();
        this.connectWebSocket();
    }
    
    loadData() {
        // 데이터 로드 로직
    }
    
    setupEventListeners() {
        // 이벤트 리스너 설정
    }
    
    connectWebSocket() {
        // WebSocket 연결
    }
    
    updateUI(data) {
        // UI 업데이트
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    const pageController = new NewPageController();
    window.pageController = pageController; // 디버깅용
});
```

## 🧪 테스팅 가이드

### 1. 로컬 테스트

#### 기본 기능 테스트
```bash
# 1. 서버 시작
python main_prototype.py

# 2. 브라우저 테스트
# - http://localhost:8002/dashboard (메인 대시보드)
# - http://localhost:8002/process/deposition (공정 페이지)
# - 각 링크 및 버튼 동작 확인

# 3. WebSocket 연결 테스트
# 브라우저 개발자 도구 → 네트워크 → WS 탭에서 연결 상태 확인
```

#### 반응형 테스트
```bash
# 브라우저 개발자 도구에서 다양한 화면 크기 테스트
# - Desktop: 1920x1080
# - Tablet: 768x1024
# - Mobile: 375x667
```

### 2. 라즈베리파이 테스트

```bash
# 1. SSH 접속
ssh pi@<raspberry-pi-ip>

# 2. 서버 실행
cd ~/egicon_web/v2
python main_prototype.py

# 3. 로컬 네트워크에서 접속 테스트
# http://<raspberry-pi-ip>:8002/dashboard
```

### 3. 부하 테스트 (선택사항)

```python
# load_test.py
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8002/ws/realtime"
    try:
        async with websockets.connect(uri) as websocket:
            # 연결 테스트
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            print(f"응답: {response}")
    except Exception as e:
        print(f"WebSocket 연결 실패: {e}")

asyncio.run(test_websocket())
```

## 🚀 배포 가이드

### 1. 라즈베리파이 초기 설정

```bash
# 1. 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 2. Python 및 pip 설치
sudo apt install python3 python3-pip python3-venv -y

# 3. Git 설치
sudo apt install git -y

# 4. 프로젝트 클론
git clone <repository-url>
cd egicon_web/v2

# 5. 가상환경 설정 (권장)
python3 -m venv venv
source venv/bin/activate

# 6. 의존성 설치
pip install -r requirements_prototype.txt
```

### 2. systemd 서비스 설정

```bash
# 1. 서비스 파일 생성
sudo nano /etc/systemd/system/egicon-v2.service
```

```ini
[Unit]
Description=EG-ICON V2 Digital Twin Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/egicon_web/v2
ExecStart=/home/pi/egicon_web/v2/venv/bin/python main_prototype.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 2. 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable egicon-v2
sudo systemctl start egicon-v2

# 3. 서비스 상태 확인
sudo systemctl status egicon-v2
```

### 3. 네트워크 설정

```bash
# 1. 방화벽 설정
sudo ufw allow 8002
sudo ufw enable

# 2. 고정 IP 설정 (선택사항)
sudo nano /etc/dhcpcd.conf
# interface eth0
# static ip_address=192.168.1.100/24
# static routers=192.168.1.1
# static domain_name_servers=8.8.8.8

# 3. 재부팅
sudo reboot
```

### 4. 자동 업데이트 스크립트

```bash
# update_v2.sh
#!/bin/bash
cd /home/pi/egicon_web
git pull origin v2
cd v2
source venv/bin/activate
pip install -r requirements_prototype.txt --upgrade
sudo systemctl restart egicon-v2
echo "V2 업데이트 완료: $(date)"
```

```bash
# 실행 권한 부여
chmod +x update_v2.sh

# cron으로 자동 업데이트 설정 (선택사항)
crontab -e
# 매일 새벽 3시에 업데이트
0 3 * * * /home/pi/egicon_web/update_v2.sh >> /home/pi/update.log 2>&1
```

## 🔧 트러블슈팅

### 1. 일반적인 문제들

#### 포트 충돌
```bash
# 문제: Port 8002 already in use
# 해결:
lsof -i :8002  # 포트 사용 프로세스 확인
kill -9 <PID>  # 프로세스 종료

# 또는 다른 포트 사용
# main_prototype.py에서 포트 변경
uvicorn.run(app, host="0.0.0.0", port=8003)
```

#### WebSocket 연결 실패
```bash
# 문제: WebSocket connection failed
# 해결:
1. 방화벽 확인: sudo ufw status
2. 포트 허용: sudo ufw allow 8002
3. 서버 재시작: sudo systemctl restart egicon-v2
```

#### 정적 파일 로드 실패
```python
# 문제: CSS/JS 파일이 로드되지 않음
# 해결: main_prototype.py에서 정적 파일 경로 확인
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# HTML에서 올바른 경로 사용
<link rel="stylesheet" href="/static/css/modern-dashboard.css">
```

### 2. 라즈베리파이 특화 문제

#### pip 설치 권한 오류
```bash
# 문제: pip install 권한 거부
# 해결:
pip install --break-system-packages -r requirements_prototype.txt

# 또는 가상환경 사용
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_prototype.txt
```

#### 메모리 부족
```bash
# 문제: 라즈베리파이 메모리 부족
# 해결:
1. 스왑 파일 크기 증가
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=1024

2. 서비스 재시작
sudo systemctl restart dphys-swapfile

3. 메모리 사용량 모니터링
htop
```

### 3. 개발 환경 문제

#### 가상환경 활성화 문제
```bash
# 문제: venv 활성화 안됨
# 해결:
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

#### 브라우저 캐시 문제
```bash
# 문제: CSS/JS 변경사항이 반영되지 않음
# 해결:
1. 브라우저 강력 새로고침: Ctrl+Shift+R (Cmd+Shift+R)
2. 개발자 도구에서 캐시 비활성화
3. 시크릿 모드에서 테스트
```

## 📞 지원 및 문의

### 개발 관련 문의
- **GitHub Issues**: 버그 리포트 및 기능 요청
- **개발자 이메일**: [연락처]
- **개발 문서**: `/docs` 폴더 참조

### 긴급 지원
1. **서버 다운**: `sudo systemctl status egicon-v2`로 상태 확인
2. **WebSocket 연결 불가**: 방화벽 및 네트워크 설정 확인
3. **데이터 손실**: V1 백업 파일에서 복구

---

**마지막 업데이트**: 2025-07-10  
**작성자**: ShinHoTechnology  
**버전**: V2.1