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
        
        
        // 버스별 스캔 버튼들
        document.querySelectorAll('.scan-bus-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const busNumber = parseInt(e.target.dataset.bus);
                this.scanSingleBus(busNumber);
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
    
    // 스캔 결과 업데이트 (I2C + UART 센서 지원)
    updateScanResults(scanResult) {
        const tbody = document.getElementById('scan-results-body');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        const i2cDevices = scanResult.i2c_devices || [];
        const uartDevices = scanResult.uart_devices || [];
        const totalDevices = i2cDevices.length + uartDevices.length;
        
        if (totalDevices === 0) {
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
        
        // UART 디바이스 표시 (SPS30 등)
        uartDevices.forEach(device => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><span class="comm-badge uart">UART</span></td>
                <td>-</td>
                <td>-</td>
                <td>${device.port}</td>
                <td>${device.sensor_name}</td>
                <td>${device.sensor_type}</td>
                <td><span class="status-badge status-connected">${device.status}</span></td>
                <td>
                    <button class="action-btn test-btn" onclick="window.settings.testUARTDevice('${device.port}', '${device.sensor_type}')">
                        <i class="fas fa-vial"></i> 테스트
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        console.log(`✅ 스캔 결과 업데이트 완료: I2C ${i2cDevices.length}개, UART ${uartDevices.length}개`);
    }
    
    // 시스템 표시 업데이트
    updateSystemDisplay(systemData) {
        console.log('🔄 시스템 디스플레이 업데이트:', systemData);
        
        // 전체 시스템 통계 업데이트 (I2C + UART)
        const connectedCount = document.getElementById('connected-count');
        if (connectedCount) {
            const i2cSensors = systemData.i2c_devices ? systemData.i2c_devices.length : 0;
            const uartSensors = systemData.uart_devices ? systemData.uart_devices.length : 0;
            const totalSensors = i2cSensors + uartSensors;
            connectedCount.textContent = `${totalSensors}개 연결됨 (I2C: ${i2cSensors}, UART: ${uartSensors})`;
            this.connectedSensors = totalSensors;
        }
        
        // 모든 채널 카드 초기화
        this.clearAllChannelCards();
        
        // i2c_devices 배열을 통해 채널별 센서 정보 업데이트
        if (systemData.i2c_devices && systemData.i2c_devices.length > 0) {
            console.log('📡 I2C 디바이스 업데이트:', systemData.i2c_devices);
            systemData.i2c_devices.forEach(device => {
                this.updateChannelCardFromI2CDevice(device);
            });
        }
        
        // 채널별 센서 정보 업데이트 (기존 방식 유지)
        if (systemData.sensors) {
            systemData.sensors.forEach(sensor => {
                this.updateChannelCard(sensor);
            });
        }
        
        // 버스별 데이터가 있는 경우 처리
        if (systemData.buses) {
            Object.keys(systemData.buses).forEach(busNum => {
                const busData = systemData.buses[busNum];
                this.updateBusChannels(parseInt(busNum), busData);
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
    
    // 모든 채널 카드 초기화
    clearAllChannelCards() {
        document.querySelectorAll('.channel-card').forEach(card => {
            const sensorType = card.querySelector('.sensor-type');
            const sensorAddress = card.querySelector('.sensor-address');
            const sensorStatus = card.querySelector('.sensor-status');
            
            if (sensorType) sensorType.textContent = '--';
            if (sensorAddress) sensorAddress.textContent = '--';
            if (sensorStatus) {
                sensorStatus.textContent = '미연결';
                sensorStatus.className = 'sensor-status disconnected';
            }
        });
    }
    
    // 버스별 채널 업데이트
    updateBusChannels(busNumber, busData) {
        console.log(`🔄 Bus ${busNumber} 채널 업데이트:`, busData);
        
        if (busData.channels) {
            // TCA9548A가 감지된 경우 - 채널별 데이터
            Object.keys(busData.channels).forEach(channelNum => {
                const channelSensors = busData.channels[channelNum];
                if (channelSensors && channelSensors.length > 0) {
                    const sensor = channelSensors[0]; // 첫 번째 센서 사용
                    this.updateChannelCardByPosition(busNumber, parseInt(channelNum), sensor);
                }
            });
        } else if (busData.direct_devices) {
            // TCA9548A가 없는 경우 - 직접 연결된 센서들
            busData.direct_devices.forEach((sensor, index) => {
                this.updateChannelCardByPosition(busNumber, index, sensor);
            });
        }
    }
    
    // I2C 디바이스 데이터로 채널 카드 업데이트
    updateChannelCardFromI2CDevice(device) {
        console.log('📡 I2C 디바이스 처리:', device);
        
        const channelCard = document.querySelector(
            `[data-bus="${device.bus}"][data-channel="${device.mux_channel}"]`
        );
        
        if (channelCard) {
            const sensorType = channelCard.querySelector('.sensor-type');
            const sensorAddress = channelCard.querySelector('.sensor-address');
            const sensorStatus = channelCard.querySelector('.sensor-status');
            
            if (sensorType) sensorType.textContent = device.sensor_type || device.sensor_name || 'Unknown';
            if (sensorAddress) sensorAddress.textContent = device.address || '--';
            
            if (sensorStatus) {
                // I2C 디바이스가 스캔되었다면 연결된 것으로 간주
                sensorStatus.textContent = '연결됨';
                sensorStatus.className = 'sensor-status connected';
            }
            
            console.log(`✅ Ch ${device.mux_channel + 1} 업데이트 완료: ${device.sensor_name}`);
        } else {
            console.warn(`⚠️ 채널 카드를 찾을 수 없음: Bus ${device.bus}, Channel ${device.mux_channel}`);
        }
    }
    
    // 채널 카드 업데이트 (위치 기반)
    updateChannelCardByPosition(busNumber, channelIndex, sensor) {
        const channelCard = document.querySelector(
            `[data-bus="${busNumber}"][data-channel="${channelIndex}"]`
        );
        
        if (channelCard) {
            const sensorType = channelCard.querySelector('.sensor-type');
            const sensorAddress = channelCard.querySelector('.sensor-address');
            const sensorStatus = channelCard.querySelector('.sensor-status');
            
            if (sensorType) sensorType.textContent = sensor.sensor_type || sensor.sensor_name || 'Unknown';
            if (sensorAddress) sensorAddress.textContent = sensor.address || '--';
            
            if (sensorStatus) {
                const isConnected = sensor.status === 'connected' || sensor.status === '연결됨';
                sensorStatus.textContent = isConnected ? '연결됨' : '미연결';
                sensorStatus.className = `sensor-status ${isConnected ? 'connected' : 'disconnected'}`;
            }
        }
    }
    
    // 채널 카드 업데이트 (기존 함수 - 호환성 유지)
    updateChannelCard(sensor) {
        if (sensor.mux_channel !== null && sensor.mux_channel !== undefined) {
            // TCA9548A를 통한 센서
            this.updateChannelCardByPosition(sensor.bus, sensor.mux_channel, sensor);
        }
    }
    
    // 센서 테스트
    async testSensor(busNumber, channel, address = null) {
        try {
            console.log(`🧪 센서 테스트: Bus ${busNumber}, Channel ${channel}, Address ${address}`);
            
            // 주소를 숫자로 변환
            const addressNum = typeof address === 'string' && address.startsWith('0x') 
                ? parseInt(address, 16) 
                : parseInt(address);
            
            // 센서 타입 식별
            const sensorType = this.sensorTypeMap[addressNum];
            console.log(`🔍 감지된 센서 타입: ${sensorType} (주소: ${address})`);
            
            let apiEndpoint;
            let testResult;
            
            // 센서 타입별 전용 API 호출
            switch (sensorType) {
                case 'SHT40':
                    apiEndpoint = `${this.API_URL}/sensors/sht40/test`;
                    break;
                case 'SDP810':
                    apiEndpoint = `${this.API_URL}/sensors/sdp810/test`;
                    break;
                case 'BME688':
                    // BME688은 기본 테스트 API 사용
                    apiEndpoint = `${this.API_URL}/sensors/test`;
                    break;
                case 'BH1750':
                    // BH1750은 기본 테스트 API 사용
                    apiEndpoint = `${this.API_URL}/sensors/test`;
                    break;
                default:
                    // 알 수 없는 센서는 기본 테스트 API 사용
                    apiEndpoint = `${this.API_URL}/sensors/test`;
                    break;
            }
            
            // 센서별 특화 테스트 또는 일반 테스트 실행
            if (sensorType === 'SHT40' || sensorType === 'SDP810') {
                // 센서별 전용 테스트 API 호출
                console.log(`📡 ${sensorType} 전용 테스트 API 호출: ${apiEndpoint}`);
                
                const response = await fetch(apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                testResult = await response.json();
                
                // 결과를 표준 형식으로 변환
                if (testResult.success) {
                    testResult.data = {
                        sensor_type: sensorType,
                        bus: busNumber,
                        channel: channel,
                        address: address,
                        test_details: testResult[`${sensorType.toLowerCase()}_devices`] || testResult.data,
                        message: `${sensorType} 센서 테스트 완료`
                    };
                }
            } else {
                // 일반 I2C 센서 테스트
                console.log(`📡 일반 I2C 테스트 API 호출: ${apiEndpoint}`);
                
                const response = await fetch(apiEndpoint, {
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
                
                testResult = await response.json();
                
                // 결과에 센서 타입 정보 추가
                if (testResult.success && testResult.data) {
                    testResult.data.sensor_type = sensorType || 'Unknown';
                    testResult.data.detected_address = address;
                }
            }
            
            console.log(`✅ ${sensorType} 센서 테스트 결과:`, testResult);
            this.showSensorTestModal(testResult, sensorType);
            
        } catch (error) {
            console.error('센서 테스트 실패:', error);
            this.showToast('error', `센서 테스트 실패: ${error.message}`);
        }
    }
    
    // I2C 디바이스 테스트 (테이블에서 호출)
    async testI2CDevice(bus, channel, address) {
        await this.testSensor(bus, channel, address);
    }
    
    // UART 디바이스 테스트 (SPS30 등)
    async testUARTDevice(port, sensorType) {
        try {
            console.log(`🧪 UART 센서 테스트: ${sensorType} on ${port}`);
            
            const response = await fetch(`${this.API_URL}/sensors/test-uart`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    port: port,
                    sensor_type: sensorType
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showSensorTestModal(result);
            
        } catch (error) {
            console.error('UART 센서 테스트 실패:', error);
            this.showToast('error', `UART 센서 테스트 실패: ${error.message}`);
        }
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
    showSensorTestModal(result, sensorType = 'Unknown') {
        let testDetails = '';
        
        if (result.success) {
            // 센서 타입별 상세 정보 표시
            switch (sensorType) {
                case 'SHT40':
                    const sht40Devices = result.sht40_devices || [];
                    if (sht40Devices.length > 0) {
                        testDetails = `
                            <div class="sensor-details">
                                <h5>🌡️ SHT40 온습도 센서</h5>
                                <p><strong>발견된 센서:</strong> ${sht40Devices.length}개</p>
                                ${sht40Devices.map((device, index) => `
                                    <div class="device-info">
                                        <p><strong>센서 ${index + 1}:</strong></p>
                                        <ul>
                                            <li>위치: Bus ${device.bus} Channel ${device.mux_channel}</li>
                                            <li>주소: ${device.address}</li>
                                            <li>상태: ${device.status}</li>
                                            <li>측정값: ${device.test_result || '테스트 결과 없음'}</li>
                                        </ul>
                                    </div>
                                `).join('')}
                            </div>
                        `;
                    } else {
                        testDetails = '<p>SHT40 센서를 찾을 수 없습니다.</p>';
                    }
                    break;
                    
                case 'SDP810':
                    const sdp810Devices = result.sdp810_devices || [];
                    if (sdp810Devices.length > 0) {
                        testDetails = `
                            <div class="sensor-details">
                                <h5>🌬️ SDP810 차압센서</h5>
                                <p><strong>발견된 센서:</strong> ${sdp810Devices.length}개</p>
                                ${sdp810Devices.map((device, index) => `
                                    <div class="device-info">
                                        <p><strong>센서 ${index + 1}:</strong></p>
                                        <ul>
                                            <li>위치: Bus ${device.bus} Channel ${device.mux_channel}</li>
                                            <li>주소: ${device.address}</li>
                                            <li>상태: ${device.status}</li>
                                            <li>측정값: ${device.test_result || '테스트 결과 없음'}</li>
                                        </ul>
                                    </div>
                                `).join('')}
                            </div>
                        `;
                    } else {
                        testDetails = '<p>SDP810 센서를 찾을 수 없습니다.</p>';
                    }
                    break;
                    
                default:
                    // 일반 센서 또는 BME688, BH1750 등
                    if (result.data) {
                        testDetails = `
                            <div class="sensor-details">
                                <h5>📊 ${sensorType} 센서</h5>
                                <div class="device-info">
                                    <ul>
                                        <li>센서 타입: ${result.data.sensor_type || sensorType}</li>
                                        <li>버스: ${result.data.bus || 'Unknown'}</li>
                                        <li>채널: ${result.data.channel || 'Unknown'}</li>
                                        <li>주소: ${result.data.detected_address || result.data.address || 'Unknown'}</li>
                                        <li>메시지: ${result.data.message || '테스트 완료'}</li>
                                    </ul>
                                </div>
                            </div>
                        `;
                        
                        // 추가 데이터가 있으면 표시
                        if (result.data.test_value !== undefined) {
                            testDetails += `<p><strong>측정값:</strong> ${result.data.test_value}</p>`;
                        }
                    } else {
                        testDetails = '<p>센서 테스트가 완료되었습니다.</p>';
                    }
                    break;
            }
        } else {
            // 실패한 경우 오류 정보 표시
            testDetails = `
                <div class="error-details">
                    <p><strong>오류 메시지:</strong> ${result.error || result.message || '알 수 없는 오류'}</p>
                    ${result.data ? `<pre>${JSON.stringify(result.data, null, 2)}</pre>` : ''}
                </div>
            `;
        }
        
        const modalHtml = `
            <div class="modal-overlay" id="test-result-modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🧪 센서 테스트 결과</h3>
                        <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="test-result ${result.success ? 'success' : 'error'}">
                            <h4>${result.success ? '✅ 테스트 성공' : '❌ 테스트 실패'}</h4>
                            ${testDetails}
                            
                            <!-- 디버그 정보 (접을 수 있는 형태) -->
                            <details style="margin-top: 20px;">
                                <summary style="cursor: pointer; font-weight: bold;">🔧 상세 디버그 정보</summary>
                                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px;">${JSON.stringify(result, null, 2)}</pre>
                            </details>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 모달이 표시된 후 자동으로 스크롤을 맨 위로
        const modal = document.getElementById('test-result-modal');
        if (modal) {
            modal.scrollTop = 0;
        }
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