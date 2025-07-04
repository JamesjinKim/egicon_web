/**
 * EG-ICON Dashboard 설정 관리자
 * ================================
 * 이중 TCA9548A 멀티플렉서 시스템 관리
 * egicon_dash 기반 스캔 기능 구현
 */

class EGIconSettings {
    constructor() {
        // 전역 변수
        this.currentScanResult = null;
        this.currentSensorStatus = null;
        this.isScanning = false;
        this.connectedSensors = 0;
        
        // API 설정
        this.API_URL = window.location.origin + '/api';
        
        // 센서 타입 매핑 (egicon_dash 기준)
        this.sensorTypeMap = {
            0x44: "SHT40", 0x45: "SHT40",
            0x76: "BME688", 0x77: "BME688", 
            0x23: "BH1750", 0x5C: "BH1750",
            0x25: "SDP810",
            0x29: "VL53L0X"
        };
        
        this.init();
    }
    
    init() {
        console.log('🔧 EG-ICON 설정 관리자 초기화 시작');
        this.hideLoading();
        this.initEventListeners();
        this.initSidebarEvents();
        this.loadInitialData();
        console.log('✅ EG-ICON 설정 관리자 초기화 완료');
    }
    
    // 이벤트 리스너 초기화
    initEventListeners() {
        // 전체 시스템 스캔
        const scanAllBtn = document.getElementById('scan-all-system');
        if (scanAllBtn) {
            scanAllBtn.addEventListener('click', () => this.scanEntireSystem());
        }
        
        // 메인 스캔 버튼
        const scanBtn = document.getElementById('scan-button');
        if (scanBtn) {
            scanBtn.addEventListener('click', () => this.startScan());
        }
        
        // 버스별 스캔 버튼들
        document.querySelectorAll('.scan-bus-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const busNumber = parseInt(e.target.dataset.bus);
                this.scanSingleBus(busNumber);
            });
        });
        
        // 센서별 테스트 버튼들
        document.querySelectorAll('.test-sensor-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const card = e.target.closest('.channel-card');
                const bus = parseInt(card.dataset.bus);
                const channel = parseInt(card.dataset.channel);
                this.testSensor(bus, channel);
            });
        });
    }
    
    // 사이드바 이벤트 초기화
    initSidebarEvents() {
        const toggleBtn = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('expanded');
                mainContent.classList.toggle('sidebar-expanded');
            });
        }
        
        // 메뉴 아이템 클릭 이벤트 (설정 페이지에서)
        document.querySelectorAll('.menu-item[data-menu]').forEach(item => {
            item.addEventListener('click', (e) => {
                const menu = item.getAttribute('data-menu');
                
                // 대시보드나 다른 센서 메뉴는 메인 페이지로 이동
                if (menu === 'home' || menu === 'temperature' || menu === 'humidity' || 
                    menu === 'light' || menu === 'pressure' || menu === 'vibration') {
                    window.location.href = '/';
                    return;
                }
                
                // 설정 메뉴는 현재 페이지 유지
                if (menu === 'settings') {
                    e.preventDefault();
                    return;
                }
            });
        });
        
        // 데이터 갱신 버튼
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.loadInitialData();
                this.showToast('info', '데이터를 갱신했습니다.');
            });
        }
    }
    
    // 초기 데이터 로드
    async loadInitialData() {
        try {
            await this.loadSensorStatus();
            await this.loadSystemStats();
        } catch (error) {
            console.error('초기 데이터 로드 실패:', error);
            this.showToast('error', '초기 데이터 로드에 실패했습니다.');
        }
    }
    
    // 전체 시스템 스캔 (egicon_dash 스타일)
    async scanEntireSystem() {
        if (this.isScanning) return;
        
        console.log('🔍 전체 시스템 스캔 시작');
        this.isScanning = true;
        
        const scanBtn = document.getElementById('scan-all-system');
        const originalText = scanBtn.innerHTML;
        
        try {
            // UI 업데이트
            scanBtn.disabled = true;
            scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 스캔 중...';
            
            // API 호출
            const response = await fetch(`${this.API_URL}/sensors/scan-dual-mux`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.currentScanResult = result;
                this.updateSystemDisplay(result);
                this.updateScanResults(result);
                this.showToast('success', `전체 스캔 완료: ${result.sensors.length}개 센서 발견`);
                console.log('✅ 전체 시스템 스캔 완료:', result);
            } else {
                throw new Error(result.message || '스캔 실패');
            }
            
        } catch (error) {
            console.error('전체 시스템 스캔 오류:', error);
            this.showToast('error', `전체 스캔 실패: ${error.message}`);
        } finally {
            // UI 복원
            this.isScanning = false;
            scanBtn.disabled = false;
            scanBtn.innerHTML = originalText;
        }
    }
    
    // 센서 스캔 시작 (egicon_dash 기반)
    async startScan() {
        if (this.isScanning) return;
        
        console.log('🔍 센서 스캔 시작');
        this.isScanning = true;
        
        const scanButton = document.getElementById('scan-button');
        const progressContainer = document.getElementById('scan-progress-container');
        const progressFill = document.getElementById('scan-progress-fill');
        const progressText = document.getElementById('scan-progress-text');
        
        try {
            // UI 업데이트
            scanButton.disabled = true;
            scanButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 스캔 중...';
            progressContainer.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = '스캔 준비 중...';
            
            // 진행률 애니메이션
            this.animateProgress(progressFill, progressText);
            
            // 통합 센서 검색 요청
            const response = await fetch(`${this.API_URL}/sensors/scan-all`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.currentScanResult = result;
                this.updateScanResults(result);
                this.updateSensorConnectionStatus();
                this.showToast('success', '통합 센서 검색이 완료되었습니다.');
                console.log('✅ 센서 스캔 완료:', result);
            } else {
                throw new Error(result.message || '스캔 실패');
            }
            
        } catch (error) {
            console.error('센서 스캔 오류:', error);
            this.showToast('error', `스캔 오류: ${error.message}`);
        } finally {
            // UI 복원
            this.isScanning = false;
            scanButton.disabled = false;
            scanButton.innerHTML = '<i class="fas fa-sync-alt"></i> 스캔 시작';
            progressFill.style.width = '100%';
            progressText.textContent = '스캔 완료';
            
            // 3초 후 진행률 숨기기
            setTimeout(() => {
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
            }, 3000);
        }
    }
    
    // 진행률 애니메이션
    animateProgress(progressFill, progressText) {
        const steps = [
            { width: '20%', text: 'CH1 스캔 중...' },
            { width: '50%', text: 'CH2 스캔 중...' },
            { width: '80%', text: '센서 분석 중...' },
            { width: '95%', text: '결과 처리 중...' }
        ];
        
        let currentStep = 0;
        const interval = setInterval(() => {
            if (currentStep < steps.length && this.isScanning) {
                const step = steps[currentStep];
                progressFill.style.width = step.width;
                progressText.textContent = step.text;
                currentStep++;
            } else {
                clearInterval(interval);
            }
        }, 800);
    }
    
    // 단일 버스 스캔
    async scanSingleBus(busNumber) {
        try {
            console.log(`🔍 CH${busNumber + 1} 스캔 시작`);
            
            const response = await fetch(`${this.API_URL}/sensors/scan-bus/${busNumber}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.updateBusDisplay(busNumber, result.sensors);
                this.showToast('success', `CH${busNumber + 1}: ${result.sensors.length}개 센서 발견`);
                console.log(`✅ CH${busNumber + 1} 스캔 완료:`, result);
            } else {
                throw new Error(result.message || '버스 스캔 실패');
            }
            
        } catch (error) {
            console.error(`CH${busNumber + 1} 스캔 실패:`, error);
            this.showToast('error', `CH${busNumber + 1} 스캔 실패: ${error.message}`);
        }
    }
    
    // 스캔 결과 업데이트 (egicon_dash 스타일)
    updateScanResults(scanResult) {
        const tbody = document.getElementById('scan-results-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        const i2cDevices = scanResult.i2c_devices || [];
        
        if (i2cDevices.length === 0) {
            const row = document.createElement('tr');
            row.className = 'no-results';
            row.innerHTML = `
                <td colspan="8">스캔 결과가 없습니다. 센서 연결을 확인해주세요.</td>
            `;
            tbody.appendChild(row);
            return;
        }
        
        // I2C 디바이스 표시 (버스별 구분)
        i2cDevices.forEach(device => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><span class="comm-badge i2c">I2C</span></td>
                <td>Ch ${device.bus + 1} (Bus ${device.bus})</td>
                <td>Ch ${device.mux_channel}</td>
                <td>${device.address}</td>
                <td>${device.sensor_name}</td>
                <td>${device.sensor_type}</td>
                <td><span class="status-badge status-connected">${device.status}</span></td>
                <td>
                    <button class="action-btn test-btn" onclick="window.settings.testI2CDevice(${device.bus}, ${device.mux_channel}, '${device.address}')">
                        <i class="fas fa-vial"></i> 테스트
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    }
    
    // 시스템 표시 업데이트
    updateSystemDisplay(systemData) {
        // 전체 시스템 통계 업데이트
        const connectedCount = document.getElementById('connected-count');
        if (connectedCount) {
            const totalSensors = systemData.sensors ? systemData.sensors.length : 0;
            connectedCount.textContent = `${totalSensors}개 연결됨`;
            this.connectedSensors = totalSensors;
        }
        
        // 채널별 센서 정보 업데이트
        if (systemData.sensors) {
            systemData.sensors.forEach(sensor => {
                this.updateChannelCard(sensor);
            });
        }
    }
    
    // 버스 표시 업데이트
    updateBusDisplay(busNumber, sensors) {
        sensors.forEach(sensor => {
            if (sensor.bus === busNumber) {
                this.updateChannelCard(sensor);
            }
        });
    }
    
    // 채널 카드 업데이트
    updateChannelCard(sensor) {
        const channelCard = document.querySelector(
            `[data-bus="${sensor.bus}"][data-channel="${sensor.mux_channel}"]`
        );
        
        if (channelCard) {
            const sensorType = channelCard.querySelector('.sensor-type');
            const sensorAddress = channelCard.querySelector('.sensor-address');
            const sensorStatus = channelCard.querySelector('.sensor-status');
            const testBtn = channelCard.querySelector('.test-sensor-btn');
            
            if (sensorType) sensorType.textContent = sensor.sensor_name || 'Unknown';
            if (sensorAddress) sensorAddress.textContent = sensor.address || '--';
            
            if (sensorStatus) {
                sensorStatus.textContent = sensor.status || '연결됨';
                sensorStatus.className = `sensor-status ${sensor.status === '연결됨' ? 'connected' : 'disconnected'}`;
            }
            
            if (testBtn) {
                testBtn.style.display = sensor.status === '연결됨' ? 'block' : 'none';
            }
        }
    }
    
    // 센서 테스트
    async testSensor(busNumber, channel, address = null) {
        try {
            console.log(`🧪 센서 테스트: CH${busNumber + 1}, MUX Ch ${channel}`);
            
            const response = await fetch(`${this.API_URL}/sensors/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    i2c_bus: busNumber,
                    mux_channel: channel,
                    address: address
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showSensorTestModal(result);
            
        } catch (error) {
            console.error('센서 테스트 실패:', error);
            this.showToast('error', `센서 테스트 실패: ${error.message}`);
        }
    }
    
    // I2C 디바이스 테스트 (테이블에서 호출)
    async testI2CDevice(bus, channel, address) {
        await this.testSensor(bus, channel, address);
    }
    
    // 센서 상태 로드
    async loadSensorStatus() {
        try {
            const response = await fetch(`${this.API_URL}/sensors/status`);
            if (response.ok) {
                this.currentSensorStatus = await response.json();
                console.log('📊 센서 상태 로드 완료:', this.currentSensorStatus);
            }
        } catch (error) {
            console.warn('센서 상태 로드 실패:', error);
        }
    }
    
    // 시스템 통계 로드
    async loadSystemStats() {
        try {
            const response = await fetch(`${this.API_URL}/sensors`);
            if (response.ok) {
                const sensors = await response.json();
                const connectedCount = sensors.filter(s => s.status === 'connected').length;
                
                const connectedElement = document.getElementById('connected-count');
                if (connectedElement) {
                    connectedElement.textContent = `${connectedCount}개 연결됨`;
                }
                
                console.log('📈 시스템 통계 로드 완료');
            }
        } catch (error) {
            console.warn('시스템 통계 로드 실패:', error);
        }
    }
    
    // 센서 연결 상태 업데이트
    updateSensorConnectionStatus() {
        if (this.currentScanResult && this.currentScanResult.i2c_devices) {
            const connectedCount = this.currentScanResult.i2c_devices.length;
            const connectedElement = document.getElementById('connected-count');
            if (connectedElement) {
                connectedElement.textContent = `${connectedCount}개 연결됨`;
            }
        }
    }
    
    // 센서 테스트 결과 모달 표시
    showSensorTestModal(result) {
        const modalHtml = `
            <div class="modal-overlay" id="test-result-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>센서 테스트 결과</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="test-result ${result.success ? 'success' : 'error'}">
                            <h4>${result.success ? '✅ 테스트 성공' : '❌ 테스트 실패'}</h4>
                            <pre>${JSON.stringify(result.data, null, 2)}</pre>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }
    
    // 토스트 알림 표시 (egicon_dash 스타일)
    showToast(type, message) {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            console.warn('토스트 컨테이너를 찾을 수 없습니다.');
            return;
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                ${this.getToastIcon(type)} ${message}
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // 3초 후 자동 제거
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 3000);
        
        console.log(`📢 토스트 [${type}]: ${message}`);
    }
    
    // 토스트 아이콘 반환
    getToastIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }
    
    // 로딩 오버레이 숨김
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            setTimeout(() => {
                overlay.style.opacity = '0';
                setTimeout(() => {
                    if (overlay.parentNode) {
                        overlay.parentNode.removeChild(overlay);
                    }
                }, 300);
            }, 500);
        }
    }
}

// 전역 인스턴스 생성
let settings = null;

// 문서 로드 완료 후 초기화
document.addEventListener('DOMContentLoaded', () => {
    settings = new EGIconSettings();
    window.settings = settings; // 전역 접근 가능하도록
    
    console.log('🚀 EG-ICON 설정 페이지 로드 완료');
});

// 페이지 언로드 시 리소스 정리
window.addEventListener('beforeunload', () => {
    if (settings) {
        console.log('🔧 설정 페이지 리소스 정리');
        // 필요시 정리 작업 추가
    }
});