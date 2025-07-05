/**
 * EG-ICON Dashboard - 센서 그룹핑 시스템
 * ==========================================
 * egicon_dash 기반 + 센서 그룹별 관리
 * 성능 최적화: 메모리 > 실시간성 > 응답속도
 */

class EGIconDashboard {
    constructor() {
        // 성능 최적화 설정
        this.config = {
            maxDataPoints: 100,       // 메모리 최적화: 차트 데이터 포인트 제한 확대 (450Pa 급변 감지용)
            updateInterval: 2000,     // 안정성 우선: 2초 간격 업데이트 (CRC 오류 최소화, 75% 성공률)
            batchSize: 4,            // 응답속도: 배치 처리 크기
            enableAnimations: true,   // 모던 차트 애니메이션
        };

        // 센서 그룹 정의 (통합보기 기준)
        this.sensorGroups = {
            "temp-humidity": {
                title: "온습도 센서",
                icon: "🌡️💧", 
                metrics: ["temperature", "humidity"],
                sensors: {
                    // BME688 센서 7개 (CH2 채널 0-6)
                    bme688: ["bme688_1_0", "bme688_1_1", "bme688_1_2", "bme688_1_3", "bme688_1_4", "bme688_1_5", "bme688_1_6"]
                },
                totalSensors: 7,
                containerId: "temp-humidity-widgets"
            },
            "sht40": {
                title: "SHT40 온습도 센서",
                icon: "🌡️💧",
                metrics: ["temperature", "humidity"],
                sensors: {
                    // SHT40 센서 (Bus 0 CH1, Bus 1 CH2)
                    sht40: ["sht40_0_1_44", "sht40_1_2_44"]  // Mock 센서 (Bus 0 CH1, Bus 1 CH2)
                },
                totalSensors: 2,
                containerId: "sht40-widgets"
            },
            "sdp810": {
                title: "SDP810 차압센서",
                icon: "🌬️",
                metrics: ["pressure"],
                sensors: {
                    // SDP810 센서 (동적으로 발견됨)
                    sdp810: ["sdp810_1_0_25"]  // Mock 센서 (Bus 1 CH0)
                },
                totalSensors: 1,
                containerId: "sdp810-widgets"
            },
            "pressure": {
                title: "압력 센서",
                icon: "📏",
                metrics: ["pressure", "airquality"],
                sensors: {
                    // BME688 센서 6개에서 압력 데이터 (메인 대시보드에서 제거됨)
                    bme688: []
                },
                totalSensors: 0,
                containerId: "pressure-widgets",
                disabled: true  // 메인 대시보드에서 비활성화
            },
            "light": {
                title: "조도 센서",
                icon: "☀️",
                metrics: ["light"],
                sensors: {
                    // BH1750 센서 (동적으로 업데이트됨)
                    bh1750: []
                },
                totalSensors: 0,
                containerId: "light-widgets"
            },
            "vibration": {
                title: "진동 센서",
                icon: "〜",
                metrics: ["vibration"],
                sensors: {
                    // 진동센서 준비 중
                },
                totalSensors: 0,
                containerId: "vibration-widgets"
            }
        };

        // 센서 설정
        this.sensorTypes = {
            temperature: {
                label: '온도',
                icon: '🌡️',
                unit: '°C',
                color: '#ff6384',
                min: -10,
                max: 50
            },
            humidity: {
                label: '습도',
                icon: '💧',
                unit: '%',
                color: '#36a2eb',
                min: 0,
                max: 100
            },
            pressure: {
                label: '압력',
                icon: '📏',
                unit: 'hPa',
                color: '#4bc0c0',
                min: 950,
                max: 1050
            },
            light: {
                label: '조도',
                icon: '☀️',
                unit: 'lux',
                color: '#ffce56',
                min: 0,
                max: 2000
            },
            vibration: {
                label: '진동',
                icon: '〜',
                unit: 'Hz',
                color: '#9966ff',
                min: 0,
                max: 100
            },
            airquality: {
                label: '공기질',
                icon: '🍃',
                unit: '/100',
                color: '#00d084',
                min: 0,
                max: 100
            }
        };

        // 데이터 저장소 (메모리 최적화)
        this.sensorData = {};
        this.charts = {};
        this.connectedSensors = new Set();
        
        // WebSocket 연결
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        // Mock 데이터 인터벌
        this.mockDataInterval = null;

        this.init();
    }

    async init() {
        this.hideLoading();
        this.initSensorData();
        
        // 동적 센서 그룹 로드 (새로운 기능)
        await this.loadSensorGroups();
        
        this.initSidebarEvents();
        this.initCharts();
        
        // 실제 센서 데이터 로드 (WebSocket 연결 전)
        await this.loadRealSensorData();
        
        this.startRealtimeConnection();
        this.updateStatusBar();
        
        console.log('🚀 EG-ICON Dashboard 초기화 완료');
    }

    // 센서 데이터 초기화
    initSensorData() {
        Object.keys(this.sensorTypes).forEach(type => {
            this.sensorData[type] = [];
        });
    }

    // 동적 센서 그룹 로드
    async loadSensorGroups() {
        try {
            console.log('🔍 동적 센서 그룹 로딩 중...');
            
            const response = await fetch('http://192.168.0.39:8001/api/sensors/groups');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const dynamicGroups = await response.json();
            console.log('📡 동적 센서 그룹 데이터:', dynamicGroups);
            
            // 기존 하드코딩된 그룹을 동적 그룹으로 교체
            this.updateSensorGroupsFromAPI(dynamicGroups);
            
            // HTML 구조 동적 업데이트
            this.buildDynamicSensorGroups(dynamicGroups);
            
            // SPS30 센서 특별 처리
            this.processSPS30SensorData(dynamicGroups);
            
            console.log('✅ 동적 센서 그룹 로딩 완료');
            
        } catch (error) {
            console.warn('⚠️ 동적 센서 그룹 로딩 실패, 하드코딩 모드 사용:', error);
            // 실패 시 기존 하드코딩된 그룹 사용
            this.generateMockSensors();
        }
    }

    // SPS30 센서 데이터 특별 처리
    processSPS30SensorData(apiResponse) {
        try {
            console.log('🌪️ SPS30 센서 데이터 처리 시작:', apiResponse);
            
            const groups = apiResponse.groups || apiResponse;
            const airQualityGroup = groups['air-quality'];
            
            if (airQualityGroup && airQualityGroup.sensors && airQualityGroup.sensors.length > 0) {
                // SPS30 센서 찾기
                const sps30Sensors = airQualityGroup.sensors.filter(sensor => 
                    sensor.sensor_type === 'SPS30' && sensor.interface === 'UART'
                );
                
                if (sps30Sensors.length > 0) {
                    const sps30Sensor = sps30Sensors[0];
                    console.log('📊 SPS30 센서 발견:', sps30Sensor);
                    this.updateSPS30Status(sps30Sensor);
                } else {
                    console.log('⚠️ SPS30 센서가 air-quality 그룹에서 발견되지 않음');
                    this.setSPS30StatusDisconnected();
                }
            } else {
                console.log('⚠️ air-quality 그룹이 비어있거나 존재하지 않음');
                this.setSPS30StatusDisconnected();
            }
            
        } catch (error) {
            console.error('❌ SPS30 센서 데이터 처리 실패:', error);
            this.setSPS30StatusDisconnected();
        }
    }

    // SPS30 연결 해제 상태 설정
    setSPS30StatusDisconnected() {
        const statusElement = document.getElementById('sps30-status');
        if (statusElement) {
            statusElement.textContent = '연결 확인 중...';
            statusElement.className = 'sensor-group-status offline';
            console.log('⚠️ SPS30 상태를 연결 확인 중으로 설정');
        }
        
        const modelElement = document.getElementById('sps30-model');
        if (modelElement) {
            modelElement.textContent = 'SPS30 UART';
            console.log('📊 SPS30 모델 정보를 기본값으로 설정');
        }
    }

    // API에서 받은 그룹 데이터로 sensorGroups 업데이트
    updateSensorGroupsFromAPI(apiResponse) {
        console.log('🔍 API 응답 구조 확인:', apiResponse);
        
        // API 응답에서 groups 데이터 추출
        const dynamicGroups = apiResponse.groups || apiResponse;
        
        if (!dynamicGroups || typeof dynamicGroups !== 'object') {
            console.error('❌ 잘못된 API 응답 구조:', apiResponse);
            return;
        }
        
        Object.entries(dynamicGroups).forEach(([groupName, groupData]) => {
            if (this.sensorGroups[groupName] && groupData.sensors) {
                // 실제 센서 수 계산
                const actualSensorCount = Array.isArray(groupData.sensors) ? groupData.sensors.length : 0;
                
                // 기존 그룹 구조 유지하되 동적 데이터로 업데이트
                this.sensorGroups[groupName] = {
                    ...this.sensorGroups[groupName],
                    totalSensors: actualSensorCount,
                    sensors: this.extractSensorIds(groupData.sensors),
                    dynamicConfig: {
                        statusText: `${actualSensorCount}개 연결됨`,
                        typesSummary: this.generateTypesSummary(groupData.sensors),
                        isOnline: actualSensorCount > 0
                    }
                };
                
                // 연결된 센서 목록 업데이트
                if (Array.isArray(groupData.sensors)) {
                    groupData.sensors.forEach(sensor => {
                        const sensorId = sensor.sensor_name || sensor.sensor_type || 'unknown';
                        this.connectedSensors.add(`${sensorId}_${sensor.bus}_${sensor.mux_channel}`);
                    });
                }
                
                console.log(`📊 그룹 ${groupName} 업데이트: ${actualSensorCount}개 센서 (실제 연결)`, groupData.sensors);
            }
        });
        
        console.log('📊 센서 그룹 업데이트 완료:', this.sensorGroups);
    }

    // 센서 데이터에서 센서 ID 목록 추출
    extractSensorIds(sensors) {
        const sensorIds = {};
        
        if (!Array.isArray(sensors)) {
            console.warn('⚠️ sensors가 배열이 아닙니다:', sensors);
            return sensorIds;
        }
        
        sensors.forEach(sensor => {
            const sensorType = (sensor.sensor_type || sensor.type || 'unknown').toLowerCase();
            if (!sensorIds[sensorType]) {
                sensorIds[sensorType] = [];
            }
            
            // 센서 ID 생성 (센서명_버스_채널)
            const sensorId = `${sensorType}_${sensor.bus}_${sensor.mux_channel}`;
            sensorIds[sensorType].push(sensorId);
        });
        
        return sensorIds;
    }
    
    // 센서 타입 요약 생성
    generateTypesSummary(sensors) {
        if (!Array.isArray(sensors)) {
            return "센서 없음";
        }
        
        const typeCounts = {};
        sensors.forEach(sensor => {
            const type = sensor.sensor_type || sensor.type || 'Unknown';
            typeCounts[type] = (typeCounts[type] || 0) + 1;
        });
        
        return Object.entries(typeCounts)
            .map(([type, count]) => `${type}×${count}`)
            .join(' + ');
    }

    // HTML 구조를 동적으로 업데이트
    buildDynamicSensorGroups(apiResponse) {
        console.log('🏗️ HTML 구조 동적 업데이트 시작:', apiResponse);
        
        // API 응답에서 groups 데이터 추출
        const dynamicGroups = apiResponse.groups || apiResponse;
        
        if (!dynamicGroups || typeof dynamicGroups !== 'object') {
            console.error('❌ buildDynamicSensorGroups: 잘못된 데이터 구조');
            return;
        }
        
        Object.entries(dynamicGroups).forEach(([groupName, groupData]) => {
            if (!groupData || !groupData.sensors) {
                console.warn(`⚠️ 그룹 ${groupName}에 센서 데이터가 없습니다`);
                return;
            }
            this.updateGroupHeader(groupName, groupData);
            this.updateGroupCharts(groupName, groupData);
            
            // 초기 센서 상태 설정 (한 번만 실행)
            this.initializeSensorStatus(groupName, groupData);
            
            // 그룹 헤더 업데이트 (조도 센서 특별 처리)
            this.updateGroupHeaderElements(groupName, groupData);
        });
    }

    // 그룹 헤더 요소 업데이트 (조도 센서 등)
    updateGroupHeaderElements(groupName, groupData) {
        const actualSensorCount = Array.isArray(groupData.sensors) ? groupData.sensors.length : 0;
        
        if (groupName === 'light') {
            // 조도 센서 그룹 상태 업데이트
            const statusElement = document.getElementById('light-group-status');
            if (statusElement) {
                if (actualSensorCount > 0) {
                    statusElement.textContent = `${actualSensorCount}개 연결됨`;
                    statusElement.className = 'sensor-group-status online';
                } else {
                    statusElement.textContent = '센서 없음';
                    statusElement.className = 'sensor-group-status offline';
                }
            }
            
            // 조도 센서 그룹 요약 업데이트
            const summaryElement = document.getElementById('light-group-summary');
            if (summaryElement) {
                if (actualSensorCount > 0) {
                    summaryElement.textContent = `BH1750×${actualSensorCount}`;
                } else {
                    summaryElement.textContent = '센서 없음';
                }
            }
            
            // 조도 센서 차트 제목 업데이트
            const chartTitleElement = document.getElementById('light-chart-title');
            if (chartTitleElement) {
                chartTitleElement.textContent = `조도 센서 통합 차트 (${actualSensorCount}개)`;
            }
            
            console.log(`✅ 조도 센서 그룹 헤더 업데이트: ${actualSensorCount}개 센서`);
        }
    }

    // 초기 센서 상태 설정
    initializeSensorStatus(groupName, groupData) {
        console.log(`🔧 초기 센서 상태 설정: ${groupName} - ${groupData.total_count}개 센서`);
        
        // 그룹별 상태 엘리먼트 업데이트
        if (groupName === 'temp-humidity') {
            const groupStatusElement = document.getElementById('temp-humidity-status');
            if (groupStatusElement) {
                const activeCount = groupData.active_count || groupData.total_count;
                const totalCount = groupData.total_count;
                groupStatusElement.textContent = `${activeCount}/${totalCount} 활성`;
                console.log(`✅ 온습도 그룹 상태 초기 설정: ${activeCount}/${totalCount} 활성`);
            }
        } else if (groupName === 'pressure') {
            const groupStatusElement = document.getElementById('pressure-status');
            if (groupStatusElement) {
                const activeCount = groupData.active_count || groupData.total_count;
                const totalCount = groupData.total_count;
                groupStatusElement.textContent = `${activeCount}/${totalCount} 활성`;
                console.log(`✅ 압력 그룹 상태 초기 설정: ${activeCount}/${totalCount} 활성`);
            }
        } else if (groupName === 'light') {
            const groupStatusElement = document.getElementById('light-status');
            if (groupStatusElement) {
                const activeCount = groupData.active_count || groupData.total_count;
                const totalCount = groupData.total_count;
                groupStatusElement.textContent = `${activeCount}/${totalCount} 활성`;
                console.log(`✅ 조도 그룹 상태 초기 설정: ${activeCount}/${totalCount} 활성`);
            }
        }
    }

    // 그룹 헤더 정보 업데이트
    updateGroupHeader(groupName, groupData) {
        const groupElement = document.querySelector(`[data-group="${groupName}"]`);
        if (!groupElement) {
            // 그룹 엘리먼트가 없으면 기존 방식으로 찾기
            return this.updateGroupHeaderByClass(groupName, groupData);
        }
        
        // 상태 텍스트 업데이트
        const statusElement = groupElement.querySelector('.sensor-group-status');
        if (statusElement) {
            statusElement.textContent = groupData.status_text;
            statusElement.className = `sensor-group-status ${groupData.status}`;
        }
        
        // 타입 요약 업데이트
        const summaryElement = groupElement.querySelector('.summary-item');
        if (summaryElement) {
            summaryElement.textContent = groupData.types_summary;
        }
    }

    // 클래스 기반으로 그룹 헤더 업데이트 (폴백)
    updateGroupHeaderByClass(groupName, groupData) {
        // 온습도 센서 그룹
        if (groupName === 'temp-humidity') {
            const statusElement = document.querySelector('.sensor-group .sensor-group-status');
            if (statusElement) {
                statusElement.textContent = groupData.status_text;
                statusElement.className = `sensor-group-status ${groupData.status}`;
            }
            
            const summaryElement = document.querySelector('.sensor-group .summary-item');
            if (summaryElement) {
                summaryElement.textContent = groupData.types_summary;
            }
        }
        
        // 다른 그룹들도 필요시 추가
    }

    // 그룹별 차트 라벨 동적 업데이트
    updateGroupCharts(groupName, groupData) {
        console.log(`🔄 그룹 ${groupName} 차트 업데이트:`, groupData);
        
        if (!groupData.sensors || !Array.isArray(groupData.sensors)) {
            console.warn(`⚠️ 그룹 ${groupName}의 센서 데이터가 배열이 아닙니다:`, groupData.sensors);
            return;
        }
        
        // 센서 라벨 생성
        const sensorLabels = groupData.sensors.map(sensor => {
            const busLabel = sensor.bus === 0 ? 'CH1' : 'CH2';
            const sensorType = sensor.sensor_type || sensor.type || 'Unknown';
            const channel = sensor.mux_channel !== undefined ? sensor.mux_channel : sensor.channel;
            return `${sensorType} ${busLabel}-Ch${channel}`;
        });
        
        // 해당 그룹의 메트릭별로 차트 업데이트
        const group = this.sensorGroups[groupName];
        if (group && group.metrics) {
            group.metrics.forEach(metric => {
                const chartId = `${metric}-multi-chart`;
                if (this.charts[chartId]) {
                    this.updateChartLabels(chartId, sensorLabels);
                }
            });
        }
    }

    // 차트 라벨 동적 업데이트
    updateChartLabels(chartId, newLabels) {
        const chart = this.charts[chartId];
        if (!chart) return;
        
        // 기존 데이터셋 수와 새 라벨 수가 다르면 차트 재생성
        if (chart.data.datasets.length !== newLabels.length) {
            console.log(`🔄 차트 ${chartId} 재생성 중 (${chart.data.datasets.length} -> ${newLabels.length})`);
            this.recreateChart(chartId, newLabels);
        } else {
            // 라벨만 업데이트
            chart.data.datasets.forEach((dataset, index) => {
                if (newLabels[index]) {
                    dataset.label = newLabels[index];
                }
            });
            chart.update();
        }
    }

    // 차트 재생성
    recreateChart(chartId, sensorLabels) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        
        // 기존 차트 삭제
        if (this.charts[chartId]) {
            this.charts[chartId].destroy();
            delete this.charts[chartId];
        }
        
        // 센서 타입 추출 (차트 ID에서)
        const sensorType = chartId.replace('-multi-chart', '');
        
        // 새 차트 생성
        this.createMultiSensorChart(chartId, sensorType, sensorLabels);
    }

    // Mock 센서 생성 (그룹 기준)
    generateMockSensors() {
        console.log('🔧 Mock 센서 생성 중...');
        
        // 각 그룹의 센서들을 connectedSensors에 추가
        Object.values(this.sensorGroups).forEach(group => {
            if (group.sensors && typeof group.sensors === 'object') {
                // sensors가 객체인 경우 (센서 타입별로 분류된 경우)
                Object.values(group.sensors).forEach(sensorArray => {
                    if (Array.isArray(sensorArray)) {
                        sensorArray.forEach(sensorId => {
                            this.connectedSensors.add(sensorId);
                        });
                    }
                });
            } else if (Array.isArray(group.sensors)) {
                // sensors가 배열인 경우
                group.sensors.forEach(sensorId => {
                    this.connectedSensors.add(sensorId);
                });
            }
        });
        
        console.log('✅ Mock 센서 생성 완료:', this.connectedSensors.size, '개');
    }

    // 사이드바 이벤트 초기화
    initSidebarEvents() {
        // 사이드바 토글
        const toggleBtn = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('expanded');
                mainContent.classList.toggle('sidebar-expanded');
            });
        }

        // 메뉴 아이템 클릭 이벤트
        document.querySelectorAll('.menu-item[data-menu]').forEach(item => {
            item.addEventListener('click', (e) => {
                const menu = item.getAttribute('data-menu');
                
                // 설정 메뉴와 미세먼지센서 메뉴는 페이지 이동을 허용
                if (menu === 'settings' || menu === 'dustsensor') {
                    return; // preventDefault 하지 않고 기본 링크 동작 허용
                }
                
                e.preventDefault();
                
                // 활성 메뉴 변경
                document.querySelectorAll('.menu-item').forEach(menu => {
                    menu.classList.remove('active');
                });
                item.classList.add('active');
                
                // 헤더 제목 변경
                const titles = {
                    'home': 'EG-icon 센서 대시보드',
                    'temperature': '온도 센서 모니터링',
                    'humidity': '습도 센서 모니터링',
                    'light': '조도 센서 모니터링',
                    'pressure': '압력 센서 모니터링',
                    'vibration': '진동 센서 모니터링',
                    'settings': '시스템 설정'
                };
                
                const headerTitle = document.getElementById('header-title');
                if (headerTitle) {
                    headerTitle.textContent = titles[menu] || 'EG-icon 센서 대시보드';
                }
            });
        });

        // 데이터 갱신 버튼
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.updateStatusBar();
                console.log('📊 데이터 갱신됨');
            });
        }
    }

    // 차트 초기화 (동적 센서 그룹 지원)
    initCharts() {
        // 동적 센서 그룹이 로드된 후 차트 생성
        this.createChartsFromSensorGroups();
        
        // SHT40 전용 차트 생성
        this.createSHT40Charts();
        
        // SDP810 전용 차트 생성
        this.createSDP810Charts();
    }

    // 센서 그룹 기반 차트 생성
    createChartsFromSensorGroups() {
        Object.entries(this.sensorGroups).forEach(([groupName, group]) => {
            // 비활성화된 그룹은 건너뛰기
            if (group.disabled) {
                console.log(`📊 그룹 ${groupName}은 비활성화되어 차트 생성 스킵`);
                return;
            }
            
            if (group.totalSensors > 0) {
                // 각 메트릭별로 차트 생성
                group.metrics.forEach(metric => {
                    const chartId = `${metric}-multi-chart`;
                    const sensorLabels = this.generateSensorLabels(group, metric);
                    
                    if (sensorLabels.length > 1) {
                        // 멀티 센서 차트
                        this.createMultiSensorChart(chartId, metric, sensorLabels);
                        console.log(`📊 멀티 센서 차트 생성: ${chartId} (${sensorLabels.length}개 센서)`);
                    } else if (sensorLabels.length === 1) {
                        // 단일 센서 차트
                        this.createMultiSensorChart(chartId, metric, sensorLabels); // 단일 센서도 멀티 차트로 처리
                        console.log(`📊 단일 센서 차트 생성: ${chartId} (1개 센서)`);
                    } else {
                        console.log(`⚠️ ${metric} 센서가 없어 차트 생성 스킵: ${chartId}`);
                    }
                });
            } else {
                console.log(`📊 그룹 ${groupName}은 센서가 없어 차트 생성 스킵 (${group.totalSensors}개)`);
            }
        });
    }

    // 센서 그룹에서 라벨 생성
    generateSensorLabels(group, metric) {
        const labels = [];
        
        // 동적 구성이 있으면 사용
        if (group.dynamicConfig && group.sensors) {
            Object.values(group.sensors).forEach(sensorList => {
                if (Array.isArray(sensorList)) {
                    sensorList.forEach((sensorId, index) => {
                        // 센서 ID에서 타입과 채널 정보 추출
                        const parts = sensorId.split('_');
                        if (parts.length >= 3) {
                            const sensorType = parts[0].toUpperCase();
                            const bus = parseInt(parts[1]);
                            const channel = parseInt(parts[2]);
                            const busLabel = bus === 0 ? 'CH1' : 'CH2';
                            labels.push(`${sensorType} ${busLabel}-Ch${channel}`);
                        } else {
                            // 폴백: 기본 라벨
                            labels.push(`${group.title} ${index + 1}`);
                        }
                    });
                }
            });
        } else {
            // 기존 하드코딩 방식 (폴백)
            return this.generateFallbackLabels(group, metric);
        }
        
        return labels;
    }

    // 폴백 라벨 생성 (동적 센서 구성 기반)
    generateFallbackLabels(group, metric) {
        const labels = [];
        
        // 동적 센서 구성이 있으면 사용
        if (group.sensors && typeof group.sensors === 'object') {
            // 센서 타입별로 분류된 경우
            Object.entries(group.sensors).forEach(([sensorType, sensorList]) => {
                if (Array.isArray(sensorList)) {
                    sensorList.forEach((sensorId) => {
                        // 센서 ID에서 라벨 생성 (예: bme688_1_0 -> BME688 CH2-Ch0)
                        const parts = sensorId.split('_');
                        if (parts.length >= 3) {
                            const type = parts[0].toUpperCase();
                            const bus = parseInt(parts[1]);
                            const channel = parseInt(parts[2]);
                            const busLabel = bus === 0 ? 'CH1' : 'CH2';
                            labels.push(`${type} ${busLabel}-Ch${channel}`);
                        } else {
                            labels.push(`${sensorType.toUpperCase()} 센서`);
                        }
                    });
                }
            });
        }
        
        // 동적 구성이 없거나 비어있으면 기본 라벨
        if (labels.length === 0) {
            switch (metric) {
                case 'temperature':
                case 'humidity':
                    return ['온습도 센서 1', '온습도 센서 2', '온습도 센서 3'];
                case 'pressure':
                case 'airquality':
                    return ['압력 센서 1', '압력 센서 2'];
                case 'light':
                    return ['조도 센서 1', '조도 센서 2'];
                case 'vibration':
                    return ['진동 센서'];
                default:
                    return [`${group.title} 센서`];
            }
        }
        
        return labels;
    }

    // 그룹 차트 생성
    createGroupChart(canvasId, sensorType, title) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const sensorConfig = this.sensorTypes[sensorType];
        
        // 그라데이션 생성
        const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 200);
        gradient.addColorStop(0, sensorConfig.color + '40');
        gradient.addColorStop(1, sensorConfig.color + '10');

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: title,
                    data: [],
                    borderColor: sensorConfig.color,
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: sensorConfig.color,
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#333',
                        bodyColor: '#666',
                        borderColor: sensorConfig.color,
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                return `${title}: ${context.parsed.y.toFixed(1)}${sensorConfig.unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            maxTicksLimit: 6,
                            color: '#666',
                            font: {
                                size: 10
                            }
                        }
                    },
                    y: {
                        display: true,
                        min: sensorConfig.min,
                        max: sensorConfig.max,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            color: '#666',
                            font: {
                                size: 10
                            },
                            callback: function(value) {
                                return value.toFixed(0) + sensorConfig.unit;
                            }
                        }
                    }
                },
                animation: {
                    duration: 500
                }
            }
        });
    }

    // Multi-line 차트 생성 (복수 센서 통합)
    createMultiSensorChart(canvasId, sensorType, sensorLabels) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const sensorConfig = this.sensorTypes[sensorType];
        
        // 색상 팔레트 정의 (센서별 구분)
        const colorPalette = [
            '#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', 
            '#9966ff', '#ffcd56', '#c9cbcf', '#ff6384'
        ];
        
        // 각 센서별 데이터셋 생성
        const datasets = sensorLabels.map((label, index) => {
            const color = colorPalette[index % colorPalette.length];
            return {
                label: label,
                data: [],
                borderColor: color,
                backgroundColor: color + '20',
                borderWidth: 2,
                fill: false,
                tension: 0.4,
                pointRadius: 2,
                pointHoverRadius: 5,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: color,
                pointBorderWidth: 2
            };
        });

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            boxWidth: 20,
                            padding: 15,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#333',
                        bodyColor: '#666',
                        borderColor: '#ddd',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}${sensorConfig.unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            maxTicksLimit: 8,
                            color: '#666',
                            font: {
                                size: 10
                            }
                        }
                    },
                    y: {
                        display: true,
                        min: sensorConfig.min,
                        max: sensorConfig.max,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            color: '#666',
                            font: {
                                size: 10
                            },
                            callback: function(value) {
                                return value.toFixed(0) + sensorConfig.unit;
                            }
                        }
                    }
                },
                animation: {
                    duration: 300
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    // SHT40 전용 차트 생성
    createSHT40Charts() {
        // SHT40 온도 차트 생성
        this.createSHT40Chart('sht40-temperature-chart', 'temperature', 'SHT40 온도', '°C', '#ff6384', -10, 50);
        
        // SHT40 습도 차트 생성
        this.createSHT40Chart('sht40-humidity-chart', 'humidity', 'SHT40 습도', '%', '#36a2eb', 0, 100);
        
        console.log('📊 SHT40 전용 차트 생성 완료');
    }

    // SHT40 개별 차트 생성
    createSHT40Chart(canvasId, metric, title, unit, color, min, max) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`⚠️ SHT40 차트 캔버스 찾을 수 없음: ${canvasId}`);
            return;
        }

        const ctx = canvas.getContext('2d');
        
        // 기존 차트가 있으면 제거
        const existingChart = Chart.getChart(canvasId);
        if (existingChart) {
            existingChart.destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [] // 동적으로 추가됨
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        },
                        title: {
                            display: true,
                            text: '시간'
                        }
                    },
                    y: {
                        min: min,
                        max: max,
                        title: {
                            display: true,
                            text: `${title} (${unit})`
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}${unit}`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 300
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
        
        console.log(`📊 SHT40 ${metric} 차트 생성 완료: ${canvasId}`);
    }

    // SDP810 전용 차트 생성
    createSDP810Charts() {
        // SDP810 차압 차트 생성 (±500 Pa 범위 - 450Pa 스파이크 감지용 확장 범위)
        this.createSDP810Chart('sdp810-pressure-chart', 'pressure', 'SDP810 차압', 'Pa', '#4bc0c0', -500, 500);
        
        console.log('📊 SDP810 전용 차트 생성 완료');
    }

    // SDP810 개별 차트 생성
    createSDP810Chart(canvasId, metric, title, unit, color, min, max) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`⚠️ SDP810 차트 캔버스 찾을 수 없음: ${canvasId}`);
            return;
        }

        const ctx = canvas.getContext('2d');
        
        // 기존 차트가 있으면 제거
        const existingChart = Chart.getChart(canvasId);
        if (existingChart) {
            existingChart.destroy();
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [] // 동적으로 추가됨
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                millisecond: 'HH:mm:ss.SSS',
                                second: 'HH:mm:ss',
                                minute: 'HH:mm',
                                hour: 'HH:mm'
                            }
                        },
                        title: {
                            display: true,
                            text: '시간'
                        }
                    },
                    y: {
                        min: min,
                        max: max,
                        title: {
                            display: true,
                            text: `${title} (${unit})`
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: `${title} 실시간 모니터링`
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                elements: {
                    point: {
                        radius: 3,
                        hoverRadius: 5
                    }
                }
            }
        });
        
        console.log(`📊 SDP810 ${metric} 차트 생성 완료: ${canvasId}`);
    }

    // 색상 팔레트 반환
    getColorPalette(index) {
        const colors = [
            '#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', 
            '#9966ff', '#ffcd56', '#c9cbcf', '#ff6384'
        ];
        return colors[index % colors.length];
    }

    // 실시간 연결 시작
    startRealtimeConnection() {
        // 먼저 로컬 Mock 데이터로 시작
        this.startLocalMockData();
        
        // 그 다음 WebSocket 연결 시도
        setTimeout(() => {
            this.connectWebSocket();
        }, 1000);
    }

    // WebSocket 연결
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('🔗 WebSocket 연결 시도:', wsUrl);
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('📡 WebSocket 연결됨');
            this.reconnectAttempts = 0;
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (message.type === 'sensor_data') {
                    // 실시간 데이터 처리 전에 차트 상태 확인
                    if (this.areChartsReady()) {
                        this.handleRealtimeData(message.data);
                    } else {
                        console.warn('⚠️ 차트가 아직 준비되지 않아 데이터 업데이트 스킵');
                        // 1초 후 재시도
                        setTimeout(() => {
                            if (this.areChartsReady()) {
                                this.handleRealtimeData(message.data);
                            }
                        }, 1000);
                    }
                }
            } catch (error) {
                console.error('WebSocket 메시지 파싱 오류:', error);
                console.error('원본 메시지:', event.data);
            }
        };
        
        this.ws.onclose = () => {
            console.log('📡 WebSocket 연결 종료됨');
            this.attemptReconnect();
        };
        
        this.ws.onerror = (error) => {
            console.error('📡 WebSocket 연결 오류:', {
                url: wsUrl,
                error: error,
                readyState: this.ws.readyState
            });
            this.attemptReconnect();
        };
    }

    // 실시간 데이터 처리 (BME688 세분화 센서 지원)
    handleRealtimeData(sensorData) {
        const now = new Date();
        
        // 센서 타입별 데이터 그룹화
        const groupedData = {
            temperature: [],
            humidity: [],
            pressure: [],
            light: []
        };
        
        // sensorData가 배열인지 객체인지 확인
        let dataArray = [];
        if (Array.isArray(sensorData)) {
            dataArray = sensorData;
        } else if (typeof sensorData === 'object') {
            dataArray = Object.entries(sensorData).map(([id, data]) => ({
                sensorId: id,
                ...data
            }));
        }
        
        // WebSocket 데이터 처리 및 그룹화
        dataArray.forEach((data) => {
            // SPS30 센서 데이터 처리
            if (data.sensor_type === 'SPS30' && data.interface === 'UART') {
                this.updateSPS30Data(data);
                return;
            }
            
            // SHT40 센서 데이터 처리
            if (data.sensor_type === 'SHT40') {
                this.updateSHT40Data(data);
                return;
            }
            
            // SDP810 센서 데이터 처리
            if (data.sensor_type === 'SDP810') {
                this.updateSDP810Data(data);
                return;
            }
            
            // 기존 I2C 센서 데이터 처리
            const sensorId = data.sensorId || data.sensor_id;
            if (sensorId) {
                this.connectedSensors.add(sensorId);
                
                // 서버에서 오는 데이터 구조 처리
                // 각 센서 타입별로 개별 메트릭을 추출
                ['temperature', 'humidity', 'pressure', 'light'].forEach(metric => {
                    if (data[metric] !== undefined) {
                        const sensorIndex = this.extractSensorIndex(sensorId);
                        
                        groupedData[metric].push({
                            sensorId: sensorId,
                            value: data[metric],
                            sensorIndex: sensorIndex,
                            timestamp: now
                        });
                        
                        console.log(`📊 실시간 데이터: ${sensorId} ${metric} = ${data[metric]} (인덱스: ${sensorIndex})`);
                    }
                });
            }
        });
        
        // 그룹별 차트 및 위젯 업데이트
        Object.entries(groupedData).forEach(([metric, sensorDataArray]) => {
            if (sensorDataArray.length > 0) {
                console.log(`🔍 그룹 데이터 처리: ${metric} - ${sensorDataArray.length}개 센서`);
                
                // Multi-line 차트 업데이트
                this.updateMultiSensorChartRealtime(metric, sensorDataArray, now);
                
                // 센서 타입에 맞는 그룹 매핑
                const groupName = this.getGroupNameForMetric(metric);
                if (groupName) {
                    console.log(`📋 그룹 매핑: ${metric} → ${groupName}`);
                    // 실시간 업데이트에서는 상태 업데이트 건너뛰기 (skipStatusUpdate = true)
                    this.updateSummaryWidgets(groupName, metric, sensorDataArray, true);
                } else {
                    console.warn(`⚠️ 그룹 매핑 실패: ${metric}`);
                }
            }
        });
        
        this.updateStatusBar();
    }

    // 실제 센서 데이터 가져오기
    async loadRealSensorData() {
        try {
            console.log('🔍 실제 센서 데이터 로딩 중...');
            
            const response = await fetch('/api/sensors');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const sensors = await response.json();
            console.log('📡 실제 센서 데이터:', sensors);
            
            if (sensors && Array.isArray(sensors) && sensors.length > 0) {
                // 실제 센서 데이터가 있으면 Mock 데이터와 병합
                this.mergeRealSensorData(sensors);
                console.log(`✅ 실제 센서 ${sensors.length}개 연결됨`);
            } else {
                console.log('⚠️ 실제 센서 데이터 없음, Mock 데이터 사용');
            }
            
        } catch (error) {
            console.error('❌ 실제 센서 데이터 로딩 실패:', error);
        }
    }

    // 실제 센서 데이터와 Mock 데이터 병합
    mergeRealSensorData(sensors) {
        if (!Array.isArray(sensors)) {
            console.error('❌ 센서 데이터가 배열이 아닙니다:', sensors);
            return;
        }
        
        sensors.forEach((sensor) => {
            // BH1750 조도 센서의 경우 light_1 위젯 교체
            if (sensor.sensor_type === 'BH1750') {
                const sensorId = `${sensor.sensor_type.toLowerCase()}_${sensor.bus}_${sensor.mux_channel || 0}`;
                
                // 기존 light_1 Mock 센서를 실제 센서로 교체
                this.replaceMockSensor('light_1', sensorId, sensor);
                
                // 위젯 제목 업데이트
                const widget = document.querySelector('[data-sensor="light_1"]');
                if (widget) {
                    const titleElement = widget.querySelector('.widget-title');
                    if (titleElement) {
                        titleElement.textContent = `BH1750 조도 (Bus${sensor.bus}:Ch${sensor.mux_channel})`;
                    }
                    // 실제 센서 ID로 data 속성 변경
                    widget.setAttribute('data-sensor', sensorId);
                    widget.setAttribute('data-real-sensor', 'true');
                }
            }
            
            // SDP810 차압 센서 처리
            if (sensor.sensor_type === 'SDP810') {
                const sensorId = `${sensor.sensor_type.toLowerCase()}_${sensor.bus}_${sensor.mux_channel || 0}_25`;
                console.log('📊 SDP810 차압 센서 발견:', sensor, '→', sensorId);
                
                // SDP810 센서 그룹 업데이트
                this.updateSDP810SensorFromRealData(sensor, sensorId);
            }
            
            // SPS30 공기질 센서 처리
            if (sensor.sensor_type === 'SPS30' && sensor.interface === 'UART') {
                console.log('📊 SPS30 공기질 센서 발견:', sensor);
                this.updateSPS30Status(sensor);
            }
        });
    }

    // SDP810 실제 센서 데이터 업데이트
    updateSDP810SensorFromRealData(sensor, sensorId) {
        console.log('📊 SDP810 실제 센서 연결:', sensor, sensorId);
        
        // SDP810 센서 그룹의 센서 목록 업데이트
        if (this.sensorGroups.sdp810) {
            this.sensorGroups.sdp810.sensors.sdp810 = [sensorId];
            this.sensorGroups.sdp810.totalSensors = 1;
        }
        
        // 센서 상태 업데이트
        const statusElement = document.getElementById('sdp810-status');
        if (statusElement) {
            statusElement.textContent = '1/1 활성';
            statusElement.className = 'sensor-group-status online';
        }
        
        // 센서 그룹 요약 업데이트
        const summaryElement = document.querySelector('[data-group="sdp810"] .sensor-group-summary .summary-item');
        if (summaryElement) {
            summaryElement.textContent = `SDP810×1 (Bus${sensor.bus}:Ch${sensor.mux_channel})`;
        }
        
        // 실제 센서 데이터 요청 시작
        this.startSDP810DataPolling(sensorId, sensor);
        
        console.log(`✅ SDP810 센서 연결 완료: ${sensorId}`);
    }

    // SDP810 데이터 폴링 시작
    startSDP810DataPolling(sensorId, sensor) {
        console.log(`🔄 SDP810 데이터 폴링 시작: ${sensorId}`, sensor);
        console.log(`⏰ 폴링 간격: ${this.config.updateInterval}ms`);
        
        // 즉시 한 번 실행
        this.fetchSDP810Data(sensor);
        
        // 주기적 업데이트 설정
        const intervalId = setInterval(() => {
            console.log(`⏰ SDP810 정기 폴링 실행: ${new Date().toLocaleTimeString()}`);
            this.fetchSDP810Data(sensor);
        }, this.config.updateInterval);
        
        // 인터벌 ID 저장 (필요시 정리용)
        this.sdp810PollingInterval = intervalId;
        console.log(`✅ SDP810 폴링 설정 완료: interval ID ${intervalId}`);
    }

    // SDP810 센서 데이터 가져오기 (라즈베리파이 실제 데이터)
    async fetchSDP810Data(sensor) {
        const apiUrl = `http://192.168.0.39:8001/api/sensors/sdp810/${sensor.bus}/${sensor.mux_channel}`;
        console.log(`📡 SDP810 실제 라즈베리파이 API 호출: ${apiUrl}`);
        
        try {
            const response = await fetch(apiUrl);
            console.log(`📡 SDP810 API 응답: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            console.log(`📊 SDP810 API 결과:`, result);
            
            if (result.success && result.data) {
                // 데이터를 표준 형식으로 변환
                const sensorData = {
                    sensor_id: result.data.sensor_id,
                    sensor_type: 'SDP810',
                    data: {
                        differential_pressure: result.data.data.differential_pressure
                    },
                    timestamp: result.data.timestamp
                };
                
                console.log(`🔄 SDP810 변환된 데이터:`, sensorData);
                
                // SDP810 데이터 업데이트
                this.updateSDP810Data(sensorData);
            } else {
                console.warn(`⚠️ SDP810 API 응답 이상:`, result);
            }
        } catch (error) {
            console.error(`❌ SDP810 데이터 가져오기 실패 (Bus${sensor.bus}:Ch${sensor.mux_channel}):`, error);
            
            // 연결 오류 상태 표시
            const statusElement = document.getElementById('sdp810-status');
            if (statusElement) {
                statusElement.textContent = '센서 오류';
                statusElement.className = 'sensor-group-status offline';
            }
        }
    }

    // SPS30 센서 상태 업데이트
    updateSPS30Status(sensor) {
        console.log('📊 SPS30 센서 상태 업데이트:', sensor);
        
        const statusElement = document.getElementById('sps30-status');
        if (statusElement) {
            if (sensor.status === 'connected' || sensor.interface === 'UART') {
                statusElement.textContent = '연결 활성중';
                statusElement.className = 'sensor-group-status online';
                console.log('✅ SPS30 상태 업데이트: 연결 활성중');
            } else {
                statusElement.textContent = '연결 확인 중...';
                statusElement.className = 'sensor-group-status offline';
                console.log('⚠️ SPS30 상태 업데이트: 연결 확인 중');
            }
        } else {
            console.warn('⚠️ sps30-status 엘리먼트를 찾을 수 없음');
        }

        const modelElement = document.getElementById('sps30-model');
        if (modelElement) {
            const serialDisplay = sensor.serial_number ? 
                sensor.serial_number.substring(0, 8) : 'UART';
            modelElement.textContent = `SPS30 ${serialDisplay}`;
            console.log(`✅ SPS30 모델 정보 업데이트: SPS30 ${serialDisplay}`);
        } else {
            console.warn('⚠️ sps30-model 엘리먼트를 찾을 수 없음');
        }
    }

    // SPS30 실시간 데이터 처리
    updateSPS30Data(sensorData) {
        if (sensorData.sensor_type === 'SPS30' && sensorData.values) {
            const values = sensorData.values;
            
            // PM2.5 위젯 업데이트
            const pm25Element = document.getElementById('pm25-value');
            if (pm25Element) {
                pm25Element.textContent = `${values.pm25?.toFixed(1) || '--'} μg/m³`;
            }
            
            const pm25LevelElement = document.getElementById('pm25-level');
            if (pm25LevelElement) {
                pm25LevelElement.textContent = this.getAirQualityLevel(values.pm25);
            }

            // PM10 위젯 업데이트
            const pm10Element = document.getElementById('pm10-value');
            if (pm10Element) {
                pm10Element.textContent = `${values.pm10?.toFixed(1) || '--'} μg/m³`;
            }
            
            const pm10LevelElement = document.getElementById('pm10-level');
            if (pm10LevelElement) {
                pm10LevelElement.textContent = this.getAirQualityLevel(values.pm10);
            }

            // 공기질 등급 업데이트
            const qualityElement = document.getElementById('air-quality-grade');
            const descElement = document.getElementById('air-quality-desc');
            
            if (qualityElement && descElement) {
                const { grade, description } = this.getAirQualityInfo(values.pm25);
                qualityElement.textContent = grade;
                descElement.textContent = description;
            }

            // 메인 차트 업데이트 (있다면)
            this.updateSPS30MainChart(values);
            
            console.log('📊 SPS30 메인 위젯 업데이트:', values);
        }
    }

    // 공기질 등급 계산
    getAirQualityLevel(pmValue) {
        if (pmValue <= 15) return '좋음';
        else if (pmValue <= 35) return '보통';
        else if (pmValue <= 75) return '나쁨';
        else return '매우나쁨';
    }

    // 공기질 정보 반환
    getAirQualityInfo(pm25Value) {
        if (pm25Value <= 15) {
            return { grade: '좋음', description: '공기질이 좋습니다' };
        } else if (pm25Value <= 35) {
            return { grade: '보통', description: '민감한 사람은 주의하세요' };
        } else if (pm25Value <= 75) {
            return { grade: '나쁨', description: '외출 시 마스크 착용' };
        } else {
            return { grade: '매우나쁨', description: '외출을 자제하세요' };
        }
    }

    // SPS30 메인 차트 업데이트
    updateSPS30MainChart(values) {
        // 간단한 메인 차트가 있다면 업데이트
        const chart = Chart.getChart('sps30-main-chart');
        if (chart) {
            // 차트 데이터 업데이트 로직 구현
            console.log('📊 SPS30 메인 차트 업데이트');
        }
    }

    // SHT40 센서 데이터 업데이트
    updateSHT40Data(sensorData) {
        console.log('📊 SHT40 센서 데이터 업데이트:', sensorData);
        
        if (sensorData.sensor_type === 'SHT40' && sensorData.data) {
            const data = sensorData.data;
            const timestamp = new Date();
            
            // 센서 개수 업데이트
            this.updateSHT40SensorCount();
            
            // 온도 데이터 처리
            if (data.temperature !== undefined) {
                this.updateSHT40TemperatureData({
                    sensorId: sensorData.sensor_id,
                    value: data.temperature,
                    timestamp: timestamp
                });
            }
            
            // 습도 데이터 처리
            if (data.humidity !== undefined) {
                this.updateSHT40HumidityData({
                    sensorId: sensorData.sensor_id,
                    value: data.humidity,
                    timestamp: timestamp
                });
            }
            
            // 상태 업데이트
            this.updateSHT40Status(sensorData.sensor_id, 'connected');
            
            console.log(`📊 SHT40 데이터 업데이트 완료: ${sensorData.sensor_id} T=${data.temperature}°C H=${data.humidity}%`);
        }
    }

    // SHT40 센서 개수 업데이트
    updateSHT40SensorCount() {
        const sht40Group = this.sensorGroups['sht40'];
        if (sht40Group) {
            const count = sht40Group.sensors.sht40.length;
            
            // 상태 텍스트 업데이트
            const statusElement = document.getElementById('sht40-group-status');
            if (statusElement) {
                statusElement.textContent = count > 0 ? `${count}개 연결됨` : '센서 검색 중...';
                statusElement.className = count > 0 ? 'sensor-group-status online' : 'sensor-group-status offline';
            }
            
            // 요약 텍스트 업데이트
            const summaryElement = document.getElementById('sht40-group-summary');
            if (summaryElement) {
                summaryElement.textContent = count > 0 ? `SHT40×${count}` : '센서 검색 중';
            }
            
            // 차트 제목 업데이트
            const tempChartTitle = document.getElementById('sht40-temp-chart-title');
            if (tempChartTitle) {
                tempChartTitle.textContent = `SHT40 온도 센서 차트 (${count}개)`;
            }
            
            const humidityChartTitle = document.getElementById('sht40-humidity-chart-title');
            if (humidityChartTitle) {
                humidityChartTitle.textContent = `SHT40 습도 센서 차트 (${count}개)`;
            }
        }
    }

    // SHT40 온도 데이터 업데이트
    updateSHT40TemperatureData(sensorData) {
        // 온도 차트 업데이트
        const tempChart = Chart.getChart('sht40-temperature-chart');
        if (tempChart) {
            this.updateSHT40Chart(tempChart, sensorData, 'temperature');
        }
        
        // 온도 요약 위젯 업데이트
        this.updateSHT40TemperatureSummary(sensorData);
    }

    // SHT40 습도 데이터 업데이트
    updateSHT40HumidityData(sensorData) {
        // 습도 차트 업데이트
        const humidityChart = Chart.getChart('sht40-humidity-chart');
        if (humidityChart) {
            this.updateSHT40Chart(humidityChart, sensorData, 'humidity');
        }
        
        // 습도 요약 위젯 업데이트
        this.updateSHT40HumiditySummary(sensorData);
    }

    // SHT40 차트 업데이트
    updateSHT40Chart(chart, sensorData, metric) {
        if (!chart || !sensorData) return;
        
        const { sensorId, value, timestamp } = sensorData;
        const color = metric === 'temperature' ? '#ff6384' : '#36a2eb';
        
        // 데이터셋 찾기 또는 생성
        let dataset = chart.data.datasets.find(ds => ds.label.includes(sensorId));
        if (!dataset) {
            // 새 데이터셋 생성
            dataset = {
                label: `SHT40 ${sensorId}`,
                data: [],
                borderColor: color,
                backgroundColor: color + '20',
                fill: false,
                tension: 0.1
            };
            chart.data.datasets.push(dataset);
        }
        
        // 데이터 추가
        dataset.data.push({
            x: timestamp,
            y: value
        });
        
        // 데이터 포인트 제한
        if (dataset.data.length > this.config.maxDataPoints) {
            dataset.data.shift();
        }
        
        chart.update('none');
    }

    // SHT40 온도 요약 업데이트
    updateSHT40TemperatureSummary(sensorData) {
        // 현재 값 저장
        if (!this.sht40Data) this.sht40Data = { temperature: [], humidity: [] };
        
        const existingIndex = this.sht40Data.temperature.findIndex(d => d.sensorId === sensorData.sensorId);
        if (existingIndex >= 0) {
            this.sht40Data.temperature[existingIndex] = sensorData;
        } else {
            this.sht40Data.temperature.push(sensorData);
        }
        
        // 평균 및 범위 계산
        const temps = this.sht40Data.temperature.map(d => d.value);
        const avgTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
        const minTemp = Math.min(...temps);
        const maxTemp = Math.max(...temps);
        
        // 위젯 업데이트
        const avgElement = document.getElementById('sht40-temperature-average');
        if (avgElement) {
            avgElement.textContent = `${avgTemp.toFixed(1)}°C`;
        }
        
        const rangeElement = document.getElementById('sht40-temperature-range');
        if (rangeElement) {
            rangeElement.textContent = `${minTemp.toFixed(1)} ~ ${maxTemp.toFixed(1)}°C`;
        }
    }

    // SHT40 습도 요약 업데이트
    updateSHT40HumiditySummary(sensorData) {
        // 현재 값 저장
        if (!this.sht40Data) this.sht40Data = { temperature: [], humidity: [] };
        
        const existingIndex = this.sht40Data.humidity.findIndex(d => d.sensorId === sensorData.sensorId);
        if (existingIndex >= 0) {
            this.sht40Data.humidity[existingIndex] = sensorData;
        } else {
            this.sht40Data.humidity.push(sensorData);
        }
        
        // 평균 및 범위 계산
        const humidities = this.sht40Data.humidity.map(d => d.value);
        const avgHumidity = humidities.reduce((a, b) => a + b, 0) / humidities.length;
        const minHumidity = Math.min(...humidities);
        const maxHumidity = Math.max(...humidities);
        
        // 위젯 업데이트
        const avgElement = document.getElementById('sht40-humidity-average');
        if (avgElement) {
            avgElement.textContent = `${avgHumidity.toFixed(1)}%`;
        }
        
        const rangeElement = document.getElementById('sht40-humidity-range');
        if (rangeElement) {
            rangeElement.textContent = `${minHumidity.toFixed(1)} ~ ${maxHumidity.toFixed(1)}%`;
        }
    }

    // SHT40 상태 업데이트
    updateSHT40Status(sensorId, status) {
        const statusElement = document.getElementById('sht40-sensor-status');
        if (statusElement) {
            const sht40Group = this.sensorGroups['sht40'];
            const totalSensors = sht40Group ? sht40Group.sensors.sht40.length : 0;
            const activeSensors = totalSensors; // 간단히 연결된 센서는 모두 활성으로 간주
            
            statusElement.textContent = `${activeSensors}/${totalSensors} 활성`;
            
            const rangeElement = statusElement.nextElementSibling;
            if (rangeElement) {
                rangeElement.textContent = activeSensors === totalSensors ? '모든 센서 정상' : '일부 센서 비활성';
            }
        }
    }

    // SDP810 센서 데이터 업데이트
    updateSDP810Data(sensorData) {
        console.log('📊 SDP810 센서 데이터 업데이트:', sensorData);
        
        if (sensorData.sensor_type === 'SDP810') {
            const timestamp = new Date();
            let pressureValue = null;
            
            // 데이터 구조 분석 및 값 추출
            if (sensorData.data && sensorData.data.differential_pressure !== undefined) {
                // API 응답 형식: { data: { differential_pressure: value } }
                pressureValue = sensorData.data.differential_pressure;
                console.log('📊 SDP810 데이터 구조 A: data.differential_pressure =', pressureValue);
            } else if (sensorData.value !== undefined) {
                // 실시간 데이터 형식: { value: pressureValue }
                pressureValue = sensorData.value;
                console.log('📊 SDP810 데이터 구조 B: value =', pressureValue);
            } else {
                console.warn('⚠️ SDP810 데이터 구조를 인식할 수 없음:', sensorData);
                return;
            }
            
            // 센서 개수 업데이트
            this.updateSDP810SensorCount();
            
            // 차압 데이터 처리
            if (pressureValue !== null && pressureValue !== undefined) {
                console.log('🔄 SDP810 차압 데이터 처리 시작:', pressureValue);
                this.updateSDP810PressureData({
                    sensorId: sensorData.sensor_id,
                    value: pressureValue,
                    timestamp: timestamp
                });
            }
            
            // 상태 업데이트
            this.updateSDP810Status(sensorData.sensor_id, 'connected');
            
            console.log(`📊 SDP810 데이터 업데이트 완료: ${sensorData.sensor_id} P=${pressureValue}Pa`);
        } else {
            console.warn('⚠️ SDP810이 아닌 센서 데이터:', sensorData);
        }
    }

    // SDP810 센서 개수 업데이트
    updateSDP810SensorCount() {
        const sdp810Group = this.sensorGroups['sdp810'];
        if (sdp810Group) {
            const count = sdp810Group.sensors.sdp810 ? sdp810Group.sensors.sdp810.length : 0;
            
            // 상태 텍스트 업데이트
            const statusElement = document.getElementById('sdp810-group-status');
            if (statusElement) {
                statusElement.textContent = count > 0 ? `${count}개 연결됨` : '센서 검색 중...';
                statusElement.className = count > 0 ? 'sensor-group-status online' : 'sensor-group-status offline';
            }
            
            // 요약 텍스트 업데이트
            const summaryElement = document.getElementById('sdp810-group-summary');
            if (summaryElement) {
                summaryElement.textContent = count > 0 ? `SDP810×${count}` : '센서 검색 중';
            }
            
            // 차트 제목 업데이트
            const chartTitle = document.getElementById('sdp810-chart-title');
            if (chartTitle) {
                chartTitle.textContent = `SDP810 차압 센서 차트 (${count}개)`;
            }
        }
    }

    // SDP810 차압 데이터 업데이트
    updateSDP810PressureData(sensorData) {
        console.log('🔄 SDP810 차압 데이터 업데이트 시작:', sensorData);
        
        // 차압 차트 업데이트
        const pressureChart = Chart.getChart('sdp810-pressure-chart');
        console.log('📊 SDP810 차트 객체:', pressureChart);
        
        if (pressureChart) {
            this.updateSDP810Chart(pressureChart, sensorData, 'pressure');
            console.log('✅ SDP810 차트 업데이트 완료');
        } else {
            console.warn('⚠️ SDP810 차트를 찾을 수 없음, 차트 재생성 시도');
            // 차트가 없으면 생성 시도
            this.createSDP810Charts();
            
            // 잠시 후 다시 시도
            setTimeout(() => {
                const retryChart = Chart.getChart('sdp810-pressure-chart');
                if (retryChart) {
                    this.updateSDP810Chart(retryChart, sensorData, 'pressure');
                    console.log('✅ SDP810 차트 재생성 후 업데이트 완료');
                } else {
                    console.error('❌ SDP810 차트 재생성 실패');
                }
            }, 100);
        }
        
        // 차압 요약 위젯 업데이트
        this.updateSDP810PressureSummary(sensorData);
        console.log('✅ SDP810 차압 요약 업데이트 완료');
    }

    // SDP810 차트 업데이트
    updateSDP810Chart(chart, sensorData, metric) {
        if (!chart || !sensorData) {
            console.error('❌ SDP810 차트 업데이트 실패: 차트 또는 데이터 누락', { chart, sensorData });
            return;
        }
        
        const { sensorId, value, timestamp } = sensorData;
        const color = '#4bc0c0'; // 청록색 (차압용)
        
        console.log(`📊 SDP810 차트 데이터 추가: ${sensorId} = ${value} Pa @ ${timestamp}`);
        
        // 센서 ID에 따른 명칭 결정 (현장 요청에 따라 배기 차압으로 변경)
        const getSensorDisplayName = (sensorId) => {
            // 현장의 요청에 따라 기본적으로 배기 차압으로 표시
            if (sensorId.includes('unknown') || sensorId.includes('_0_') || sensorId.includes('_ch0_')) {
                return '배기';
            } else if (sensorId.includes('_1_') || sensorId.includes('_ch1_')) {
                return '흡기';
            } else {
                // 기본적으로 첫 번째는 배기, 두 번째는 흡기로 처리
                const datasetCount = chart.data.datasets.length;
                return datasetCount === 0 ? '배기' : '흡기';
            }
        };
        
        const displayName = getSensorDisplayName(sensorId);
        console.log(`📊 SDP810 센서 명칭 결정: ${sensorId} → ${displayName}`);
        
        // 데이터셋 찾기 또는 생성 (센서 ID 또는 표시명으로 검색)
        let dataset = chart.data.datasets.find(ds => 
            ds.label.includes(sensorId) || ds.label.includes(displayName)
        );
        
        if (!dataset) {
            console.log(`📊 SDP810 새 데이터셋 생성: ${displayName} (${sensorId})`);
            
            // 흡기/배기에 따른 색상 구분
            const datasetColor = displayName === '배기' ? '#ff6384' : '#4bc0c0'; // 배기: 빨간색, 흡기: 청록색
            
            dataset = {
                label: `${displayName} 차압`,
                data: [],
                borderColor: datasetColor,
                backgroundColor: datasetColor + '20',
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 5,
                sensorId: sensorId // 센서 ID 저장
            };
            chart.data.datasets.push(dataset);
        }
        
        // 새 데이터 포인트 추가
        const dataPoint = {
            x: timestamp,
            y: value
        };
        
        // 급격한 변화 감지 및 경고 (450Pa 스파이크 감지 최적화)
        if (dataset.data.length > 0) {
            const lastValue = dataset.data[dataset.data.length - 1].y;
            const change = Math.abs(value - lastValue);
            
            // 변화량별 로깅
            if (change > 100) { // 100 Pa 이상 변화 시 긴급 경고
                console.error(`🚨🚨 SDP810 극심한 변화 감지 (${displayName}): ${lastValue.toFixed(2)} → ${value.toFixed(2)} Pa (변화: ${change.toFixed(2)} Pa)`);
            } else if (change > 50) { // 50 Pa 이상 변화 시 경고
                console.warn(`🚨 SDP810 급격한 변화 감지 (${displayName}): ${lastValue.toFixed(2)} → ${value.toFixed(2)} Pa (변화: ${change.toFixed(2)} Pa)`);
            } else if (change > 20) { // 20 Pa 이상 변화 시 정보
                console.info(`📈 SDP810 중간 변화 감지 (${displayName}): ${lastValue.toFixed(2)} → ${value.toFixed(2)} Pa (변화: ${change.toFixed(2)} Pa)`);
            }
            
            // 450Pa 근처 값 특별 모니터링
            if (Math.abs(value) > 400) {
                console.error(`🚨🚨 SDP810 고압 감지 (${displayName}): ${value.toFixed(2)} Pa - 450Pa 스파이크 영역!`);
            }
        }
        
        dataset.data.push(dataPoint);
        console.log(`📊 SDP810 데이터 포인트 추가:`, dataPoint, `총 ${dataset.data.length}개`);
        
        // 데이터 포인트 제한 (최근 100개로 확대 - 빠른 변화 추적)
        if (dataset.data.length > 100) {
            dataset.data.shift();
            console.log('📊 SDP810 차트 데이터 제한: 100개로 축소');
        }
        
        chart.update('none');
        console.log('✅ SDP810 차트 업데이트 완료');
    }

    // SDP810 차압 요약 업데이트
    updateSDP810PressureSummary(sensorData) {
        // 현재 값 저장
        if (!this.sdp810Data) this.sdp810Data = { pressure: [] };
        
        const existingIndex = this.sdp810Data.pressure.findIndex(d => d.sensorId === sensorData.sensorId);
        if (existingIndex >= 0) {
            this.sdp810Data.pressure[existingIndex] = sensorData;
        } else {
            this.sdp810Data.pressure.push(sensorData);
        }
        
        // 평균 및 범위 계산
        const pressures = this.sdp810Data.pressure.map(d => d.value);
        const avgPressure = pressures.reduce((a, b) => a + b, 0) / pressures.length;
        const minPressure = Math.min(...pressures);
        const maxPressure = Math.max(...pressures);
        
        // 위젯 업데이트
        const avgElement = document.getElementById('sdp810-pressure-average');
        if (avgElement) {
            avgElement.textContent = `${avgPressure.toFixed(2)} Pa`;
        }
        
        const rangeElement = document.getElementById('sdp810-pressure-range');
        if (rangeElement) {
            rangeElement.textContent = `${minPressure.toFixed(2)} ~ ${maxPressure.toFixed(2)} Pa`;
        }
    }

    // SDP810 상태 업데이트
    updateSDP810Status(sensorId, status) {
        const statusElement = document.getElementById('sdp810-sensor-status');
        if (statusElement) {
            const sdp810Group = this.sensorGroups['sdp810'];
            const totalSensors = sdp810Group && sdp810Group.sensors.sdp810 ? sdp810Group.sensors.sdp810.length : 0;
            const activeSensors = totalSensors; // 간단히 연결된 센서는 모두 활성으로 간주
            
            statusElement.textContent = `${activeSensors}/${totalSensors} 활성`;
            
            const rangeElement = statusElement.nextElementSibling;
            if (rangeElement) {
                rangeElement.textContent = activeSensors === totalSensors ? '모든 센서 정상' : '일부 센서 비활성';
            }
        }
    }

    // Mock 센서를 실제 센서로 교체
    replaceMockSensor(mockSensorId, realSensorId, realSensorData) {
        // 연결된 센서 목록에서 교체
        this.connectedSensors.delete(mockSensorId);
        this.connectedSensors.add(realSensorId);
        
        // 센서 그룹에서 교체 (sensors는 객체이므로 센서 타입별로 검색)
        Object.values(this.sensorGroups).forEach(group => {
            if (group.sensors && typeof group.sensors === 'object') {
                Object.keys(group.sensors).forEach(sensorType => {
                    if (Array.isArray(group.sensors[sensorType])) {
                        const index = group.sensors[sensorType].indexOf(mockSensorId);
                        if (index !== -1) {
                            group.sensors[sensorType][index] = realSensorId;
                            console.log(`✅ ${sensorType} 그룹에서 ${mockSensorId} → ${realSensorId} 교체 완료`);
                        }
                    }
                });
            }
        });
        
        // 차트 데이터에서 교체
        if (this.charts[realSensorData.type]) {
            this.charts[realSensorData.type].data.datasets.forEach(dataset => {
                if (dataset.label.includes(mockSensorId)) {
                    dataset.label = `BH1750 조도 (Ch${realSensorData.channel + 1})`;
                }
            });
        }
        
        console.log(`🔄 Mock 센서 ${mockSensorId}를 실제 센서 ${realSensorId}로 교체됨`);
    }

    // WebSocket 재연결
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = 1000 * this.reconnectAttempts;
            console.log(`🔄 WebSocket 재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts} (${delay}ms 후)`);
            
            setTimeout(() => {
                console.log('🔗 WebSocket 재연결 실행 중...');
                this.connectWebSocket();
            }, delay);
        } else {
            console.error('❌ WebSocket 재연결 포기, 로컬 Mock 데이터로 전환');
            console.log('📊 서버 연결 없이 Mock 데이터 모드로 동작합니다');
            this.startLocalMockData();
        }
    }

    // 로컬 Mock 데이터 시작
    startLocalMockData() {
        if (this.mockDataInterval) return;
        
        console.log('🔄 로컬 Mock 데이터 모드로 전환');
        
        // 첫 번째 데이터 즉시 업데이트
        this.updateMockData();
        
        // 주기적 업데이트 시작
        this.mockDataInterval = setInterval(() => {
            this.updateMockData();
        }, this.config.updateInterval);
    }

    // Mock 데이터 업데이트 (Multi-line 차트 지원)
    updateMockData() {
        const now = new Date();
        
        // 센서 그룹별 데이터 생성 및 업데이트
        this.updateSensorGroupData('temp-humidity', now);
        this.updateSensorGroupData('sht40', now);
        this.updateSensorGroupData('sdp810', now);
        this.updateSensorGroupData('pressure', now);
        this.updateSensorGroupData('light', now);
        this.updateSensorGroupData('vibration', now);

        this.updateStatusBar();
    }

    // 센서 그룹별 데이터 업데이트 (동적 센서 지원)
    updateSensorGroupData(groupName, timestamp) {
        const group = this.sensorGroups[groupName];
        if (!group) return;

        group.metrics.forEach(metric => {
            const sensorData = [];
            let sensorIndex = 0;

            // 동적 센서 구성 지원
            if (group.sensors && typeof group.sensors === 'object') {
                // 각 센서 타입별로 Mock 데이터 생성
                Object.values(group.sensors).forEach(sensorList => {
                    if (Array.isArray(sensorList)) {
                        sensorList.forEach(sensorId => {
                            const mockValue = this.generateMockValueForSensor(metric, sensorIndex, timestamp);
                            sensorData.push({
                                sensorId: sensorId,
                                value: mockValue,
                                sensorIndex: sensorIndex
                            });
                            sensorIndex++;
                        });
                    }
                });
            } else {
                // 폴백: 기본 센서 수 사용
                const defaultSensorCount = group.totalSensors || 1;
                for (let i = 0; i < defaultSensorCount; i++) {
                    const mockValue = this.generateMockValueForSensor(metric, i, timestamp);
                    sensorData.push({
                        sensorId: `${metric}_${i}`,
                        value: mockValue,
                        sensorIndex: i
                    });
                }
            }

            // 센서 데이터가 있을 때만 업데이트
            if (sensorData.length > 0) {
                // Multi-line 차트 업데이트
                this.updateMultiSensorChart(groupName, metric, sensorData, timestamp);
                
                // 요약 위젯 업데이트
                this.updateSummaryWidgets(groupName, metric, sensorData);
            }
        });
    }

    // 센서별 고유 Mock 값 생성
    generateMockValueForSensor(sensorType, sensorIndex, timestamp) {
        const timeMs = timestamp.getTime();
        const baseOffset = sensorIndex * 0.5; // 센서별 오프셋
        const phaseOffset = sensorIndex * Math.PI / 4; // 위상 차이
        
        switch (sensorType) {
            case 'temperature':
                return 22 + baseOffset + 3 * Math.sin(timeMs / 60000 + phaseOffset) + (Math.random() - 0.5) * 1;
            case 'humidity':
                return 60 + baseOffset * 2 + 10 * Math.sin(timeMs / 80000 + phaseOffset) + (Math.random() - 0.5) * 2;
            case 'pressure':
                return 1013 + baseOffset + 5 * Math.sin(timeMs / 120000 + phaseOffset) + (Math.random() - 0.5) * 1;
            case 'light':
                const hour = timestamp.getHours();
                const daylight = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
                return daylight * 1000 + baseOffset * 100 + Math.random() * 100;
            case 'airquality':
                return 80 + baseOffset * 3 + 20 * Math.sin(timeMs / 180000 + phaseOffset) + (Math.random() - 0.5) * 10;
            case 'vibration':
                return Math.random() * 15 + (Math.random() > 0.9 ? Math.random() * 20 : 0);
            default:
                return Math.random() * 100;
        }
    }

    // 센서별 Mock 값 생성
    generateMockValue(sensorType, timestamp) {
        const timeMs = timestamp.getTime();
        
        switch (sensorType) {
            case 'temperature':
                return 20 + 10 * Math.sin(timeMs / 60000) + (Math.random() - 0.5) * 3;
            case 'humidity':
                return 50 + 20 * Math.sin(timeMs / 80000 + 1) + (Math.random() - 0.5) * 5;
            case 'pressure':
                return 1013 + 10 * Math.sin(timeMs / 120000 + 2) + (Math.random() - 0.5) * 2;
            case 'light':
                const hour = timestamp.getHours();
                const daylight = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
                return daylight * 1500 + Math.random() * 200;
            case 'vibration':
                return Math.random() * 20 + (Math.random() > 0.9 ? Math.random() * 30 : 0);
            case 'airquality':
                return 100 + 50 * Math.sin(timeMs / 180000 + 3) + (Math.random() - 0.5) * 20;
            default:
                return Math.random() * 100;
        }
    }

    // 센서 위젯 업데이트
    updateSensorWidget(sensorId, value) {
        // 센서 ID에 따라 해당 위젯 찾기
        let sensorType = this.getSensorTypeFromId(sensorId);
        
        if (!this.sensorTypes[sensorType]) {
            console.warn(`알 수 없는 센서 타입: ${sensorType} (ID: ${sensorId})`);
            return;
        }
        
        const unit = this.sensorTypes[sensorType].unit;
        
        // data-sensor 속성으로 특정 위젯 찾기 (더 정확한 매칭)
        const specificWidget = document.querySelector(`[data-sensor="${sensorId}"] .widget-value`);
        if (specificWidget) {
            specificWidget.innerHTML = `${value.toFixed(1)}<span class="widget-unit">${unit}</span>`;
            return;
        }
        
        // 타입별 위젯 찾기 (폴백)
        const widgets = document.querySelectorAll(`.sensor-widget.${sensorType} .widget-value`);
        widgets.forEach(widget => {
            widget.innerHTML = `${value.toFixed(1)}<span class="widget-unit">${unit}</span>`;
        });
    }

    // 센서 ID에서 센서 타입 추출 (BME688 세분화 지원)
    getSensorTypeFromId(sensorId) {
        // BME688 세분화 센서 처리
        if (sensorId.includes('_temp')) {
            return 'temperature';
        }
        if (sensorId.includes('_humidity')) {
            return 'humidity';
        }
        if (sensorId.includes('_pressure')) {
            return 'pressure';
        }
        
        // 기타 센서 타입
        if (sensorId.startsWith('bh1750_')) {
            return 'light';
        }
        if (sensorId.startsWith('sht40_')) {
            return 'temperature'; // SHT40은 기본적으로 온도
        }
        if (sensorId.startsWith('bme688_')) {
            return 'temperature'; // 기본값
        }
        
        // Mock 센서 ID (기존 방식)
        const [type] = sensorId.split('_');
        return type;
    }

    // 센서 ID에서 인덱스 추출 (차트 라인 매핑용)
    extractSensorIndex(sensorId) {
        // 동적 센서 구성에서 실제 센서 순서를 기반으로 인덱스 결정
        // 하드코딩된 채널 매핑 대신 실제 스캔된 센서 순서 사용
        
        // 현재 그룹의 센서 목록에서 해당 센서의 위치 찾기
        for (const [groupName, groupData] of Object.entries(this.sensorGroups)) {
            if (groupData.sensors && Array.isArray(groupData.sensors)) {
                const sensorIndex = groupData.sensors.findIndex(sensor => 
                    sensor === sensorId || sensor.sensor_id === sensorId
                );
                if (sensorIndex !== -1) {
                    return sensorIndex;
                }
            } else if (groupData.sensors && typeof groupData.sensors === 'object') {
                // 센서 타입별로 분류된 경우
                let globalIndex = 0;
                for (const [sensorType, sensorList] of Object.entries(groupData.sensors)) {
                    if (Array.isArray(sensorList)) {
                        const typeIndex = sensorList.indexOf(sensorId);
                        if (typeIndex !== -1) {
                            return globalIndex + typeIndex;
                        }
                        globalIndex += sensorList.length;
                    }
                }
            }
        }
        
        // 폴백: 센서 ID에서 채널 번호 사용 (기존 방식)
        const parts = sensorId.split('_');
        if (parts.length >= 3) {
            return parseInt(parts[2]);
        }
        
        return 0; // 기본값
    }

    // 센서 타입에서 그룹명 매핑
    getGroupNameForMetric(metric) {
        const metricToGroup = {
            'temperature': 'temp-humidity',
            'humidity': 'temp-humidity',
            'pressure': 'pressure',
            'light': 'light',
            'vibration': 'vibration',
            'airquality': 'pressure'
        };
        
        return metricToGroup[metric] || null;
    }

    // 실시간 Multi-line 차트 업데이트
    updateMultiSensorChartRealtime(metric, sensorDataArray, timestamp) {
        const chartId = `${metric}-multi-chart`;
        const chart = this.charts[chartId];
        
        if (!chart) {
            // pressure와 airquality는 메인 대시보드에서 제거되었으므로 경고 억제
            if (metric === 'pressure' || metric === 'airquality') {
                console.log(`📊 ${metric} 차트는 메인 대시보드에서 제거되어 스킵됨`);
            } else {
                console.warn(`⚠️ 차트를 찾을 수 없음: ${chartId}`);
            }
            return;
        }

        // 차트 상태 검증
        if (!chart.data || !chart.data.datasets || !Array.isArray(chart.data.datasets)) {
            console.error(`❌ 차트 데이터 구조가 잘못됨: ${chartId}`);
            return;
        }

        // DOM 요소 존재 확인
        const canvas = document.getElementById(chartId);
        if (!canvas || !canvas.getContext) {
            console.error(`❌ 차트 캔버스 요소를 찾을 수 없음: ${chartId}`);
            return;
        }

        try {
            const data = chart.data;
            
            // 메모리 최적화: 최대 데이터 포인트 제한
            if (data.labels.length >= this.config.maxDataPoints) {
                data.labels.shift();
                data.datasets.forEach(dataset => {
                    if (dataset.data && Array.isArray(dataset.data)) {
                        dataset.data.shift();
                    }
                });
            }
            
            // 시간 라벨 추가
            data.labels.push(timestamp.toLocaleTimeString('ko-KR', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            }));
            
            // 각 센서별 데이터 추가 (인덱스 매핑 사용)
            sensorDataArray.forEach((sensor) => {
                const datasetIndex = sensor.sensorIndex;
                
                if (datasetIndex >= 0 && 
                    datasetIndex < data.datasets.length && 
                    data.datasets[datasetIndex] && 
                    Array.isArray(data.datasets[datasetIndex].data)) {
                    
                    data.datasets[datasetIndex].data.push(sensor.value);
                    console.log(`📈 차트 업데이트: ${metric} 인덱스 ${datasetIndex} = ${sensor.value}`);
                } else {
                    console.warn(`⚠️ 데이터셋 인덱스 ${datasetIndex}가 유효하지 않음 (${metric}, 총 ${data.datasets.length}개 데이터셋)`);
                }
            });
            
            // 빈 데이터셋에 null 추가 (라인 길이 맞춤)
            data.datasets.forEach((dataset, index) => {
                if (dataset.data && Array.isArray(dataset.data) && dataset.data.length < data.labels.length) {
                    dataset.data.push(null);
                }
            });
            
            // 안전한 차트 업데이트
            if (chart && typeof chart.update === 'function') {
                chart.update('none'); // 애니메이션 없이 업데이트
            } else {
                console.error(`❌ 차트 update 함수를 사용할 수 없음: ${chartId}`);
            }
            
        } catch (error) {
            console.error(`❌ 차트 업데이트 중 오류 발생 (${chartId}):`, error);
            
            // 차트가 손상된 경우 재생성 시도
            if (error.message.includes('fullSize') || error.message.includes('configure')) {
                console.log(`🔄 차트 재생성 시도: ${chartId}`);
                this.recreateChartSafely(chartId, metric);
            }
        }
    }

    // 안전한 차트 재생성
    recreateChartSafely(chartId, metric) {
        try {
            console.log(`🔄 차트 안전 재생성 시작: ${chartId}`);
            
            // 기존 차트 정리
            if (this.charts[chartId]) {
                try {
                    this.charts[chartId].destroy();
                } catch (destroyError) {
                    console.warn(`⚠️ 차트 삭제 중 오류 (무시됨): ${destroyError.message}`);
                }
                delete this.charts[chartId];
            }
            
            // 캔버스 요소 확인
            const canvas = document.getElementById(chartId);
            if (!canvas) {
                console.error(`❌ 캔버스 요소 없음: ${chartId}`);
                return false;
            }
            
            // 차트 유형에 따른 라벨 생성
            const sensorLabels = this.generateDefaultSensorLabels(metric);
            
            // 새 차트 생성
            this.createMultiSensorChart(chartId, metric, sensorLabels);
            
            console.log(`✅ 차트 재생성 완료: ${chartId}`);
            return true;
            
        } catch (error) {
            console.error(`❌ 차트 재생성 실패 (${chartId}):`, error);
            return false;
        }
    }

    // 차트 준비 상태 확인
    areChartsReady() {
        const requiredCharts = ['temperature-multi-chart', 'humidity-multi-chart', 'light-multi-chart'];
        
        for (const chartId of requiredCharts) {
            const chart = this.charts[chartId];
            if (!chart) {
                console.log(`📊 차트 준비 안됨: ${chartId}`);
                continue; // 차트가 없는 것은 정상 (동적 로딩)
            }
            
            // 차트 데이터 구조 검증
            if (!chart.data || !chart.data.datasets || !Array.isArray(chart.data.datasets)) {
                console.warn(`⚠️ 차트 데이터 구조 문제: ${chartId}`);
                return false;
            }
            
            // DOM 요소 확인
            const canvas = document.getElementById(chartId);
            if (!canvas || !canvas.getContext) {
                console.warn(`⚠️ 캔버스 요소 문제: ${chartId}`);
                return false;
            }
        }
        
        return true;
    }

    // 기본 센서 라벨 생성 (폴백)
    generateDefaultSensorLabels(metric) {
        // 동적 센서 그룹에서 실제 센서 정보 가져오기
        const group = this.sensorGroups[this.getGroupNameForMetric(metric)];
        
        if (group && group.sensors && group.totalSensors > 0) {
            // 실제 연결된 센서 기반 라벨 생성
            const labels = [];
            Object.values(group.sensors).forEach(sensorList => {
                if (Array.isArray(sensorList)) {
                    sensorList.forEach(sensorId => {
                        const parts = sensorId.split('_');
                        if (parts.length >= 3) {
                            const sensorType = parts[0].toUpperCase();
                            const bus = parseInt(parts[1]);
                            const channel = parseInt(parts[2]);
                            const busLabel = bus === 0 ? 'CH1' : 'CH2';
                            labels.push(`${sensorType} ${busLabel}-Ch${channel}`);
                        } else {
                            labels.push(`${metric} 센서 ${labels.length + 1}`);
                        }
                    });
                }
            });
            
            if (labels.length > 0) {
                console.log(`📊 ${metric} 실제 센서 라벨 생성:`, labels);
                return labels;
            }
        }
        
        // 폴백: 기본 라벨
        switch (metric) {
            case 'temperature':
            case 'humidity':
                return ['BME688 CH2-Ch0', 'BME688 CH2-Ch1', 'BME688 CH2-Ch2', 
                       'BME688 CH2-Ch3', 'BME688 CH2-Ch4', 'BME688 CH2-Ch5', 'SHT40 CH1-Ch0'];
            case 'light':
                // 실제 연결된 센서가 없으면 빈 배열 반환
                console.log(`⚠️ ${metric} 센서가 연결되지 않음, 빈 차트 생성`);
                return [];
            case 'pressure':
                return ['BME688 센서 1', 'BME688 센서 2'];
            default:
                return [`${metric} 센서`];
        }
    }

    // 차트 데이터 업데이트 (그룹별)
    updateChartData(sensorType, value, timestamp) {
        // 해당 센서 타입의 모든 차트 업데이트
        Object.entries(this.charts).forEach(([chartId, chart]) => {
            if (chartId.includes(sensorType)) {
                const data = chart.data;
                
                // 메모리 최적화: 최대 데이터 포인트 제한
                if (data.labels.length >= this.config.maxDataPoints) {
                    data.labels.shift();
                    data.datasets[0].data.shift();
                }

                data.labels.push(timestamp.toLocaleTimeString('ko-KR', { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    second: '2-digit'
                }));
                data.datasets[0].data.push(value);
                
                chart.update('none'); // 애니메이션 없이 업데이트
            }
        });
    }

    // Multi-line 차트 업데이트
    updateMultiSensorChart(groupName, metric, sensorData, timestamp) {
        // SHT40 그룹의 경우 전용 차트 업데이트
        if (groupName === 'sht40') {
            this.updateSHT40GroupChart(metric, sensorData, timestamp);
            return;
        }
        
        const chartId = `${metric}-multi-chart`;
        const chart = this.charts[chartId];
        
        if (!chart) return;
        
        const data = chart.data;
        
        // 메모리 최적화: 최대 데이터 포인트 제한
        if (data.labels.length >= this.config.maxDataPoints) {
            data.labels.shift();
            data.datasets.forEach(dataset => dataset.data.shift());
        }
        
        // 시간 라벨 추가
        data.labels.push(timestamp.toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        }));
        
        // 각 센서별 데이터 추가
        sensorData.forEach((sensor, index) => {
            if (data.datasets[index]) {
                data.datasets[index].data.push(sensor.value);
            }
        });
        
        chart.update('none'); // 애니메이션 없이 업데이트
    }

    // SHT40 그룹 차트 업데이트
    updateSHT40GroupChart(metric, sensorData, timestamp) {
        const chartId = `sht40-${metric}-chart`;
        const chart = this.charts[chartId];
        
        if (!chart) {
            console.warn(`⚠️ SHT40 ${metric} 차트를 찾을 수 없음: ${chartId}`);
            return;
        }
        
        // 각 센서별 데이터 업데이트
        sensorData.forEach((sensor) => {
            this.updateSHT40Chart(chart, {
                sensorId: sensor.sensorId,
                value: sensor.value,
                timestamp: timestamp
            }, metric);
        });
        
        console.log(`📊 SHT40 ${metric} 그룹 차트 업데이트 완료: ${sensorData.length}개 센서`);
    }

    // 요약 위젯 업데이트 (실시간용 - 상태 제외)
    updateSummaryWidgets(groupName, metric, sensorData, skipStatusUpdate = false) {
        if (!sensorData || sensorData.length === 0) {
            console.warn(`⚠️ updateSummaryWidgets: 센서 데이터 없음 (${groupName}, ${metric})`);
            return;
        }
        
        // 안전한 숫자 값 추출 및 유효성 검사
        const values = sensorData.map(s => {
            const value = s.value || s.values || s;
            return typeof value === 'number' && !isNaN(value) ? value : 0;
        }).filter(val => typeof val === 'number' && !isNaN(val));
        
        if (values.length === 0) {
            console.warn(`⚠️ ${metric}: 유효한 숫자 데이터가 없습니다`);
            return;
        }
        
        const average = values.reduce((a, b) => a + b, 0) / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        
        const unit = this.sensorTypes[metric]?.unit || '';
        
        console.log(`📊 요약 위젯 업데이트: ${metric} - 평균: ${average.toFixed(1)}${unit}, 범위: ${min.toFixed(1)}~${max.toFixed(1)}${unit}, 센서수: ${sensorData.length}`);
        
        // pressure와 airquality는 메인 대시보드에서 제거되었으므로 스킵
        if (metric === 'pressure' || metric === 'airquality') {
            console.log(`⚠️ ${metric} 위젯은 메인 대시보드에서 제거되어 스킵합니다`);
            return;
        }
        
        // SHT40 그룹의 경우 전용 위젯 ID 사용
        const prefix = (groupName === 'sht40') ? 'sht40-' : '';
        
        // 평균값 업데이트
        const averageElement = document.getElementById(`${prefix}${metric}-average`);
        if (averageElement) {
            averageElement.textContent = `${average.toFixed(1)}${unit}`;
            console.log(`✅ 평균값 업데이트 성공: ${prefix}${metric}-average = ${average.toFixed(1)}${unit}`);
        } else {
            console.warn(`⚠️ 평균값 엘리먼트를 찾을 수 없음: ${prefix}${metric}-average (정상적으로 제거된 위젯일 수 있습니다)`);
        }
        
        // 범위 업데이트
        const rangeElement = document.getElementById(`${prefix}${metric}-range`);
        if (rangeElement) {
            rangeElement.textContent = `${min.toFixed(1)} ~ ${max.toFixed(1)}${unit}`;
            console.log(`✅ 범위 업데이트 성공: ${prefix}${metric}-range = ${min.toFixed(1)} ~ ${max.toFixed(1)}${unit}`);
        } else {
            console.warn(`⚠️ 범위 엘리먼트를 찾을 수 없음: ${prefix}${metric}-range (정상적으로 제거된 위젯일 수 있습니다)`);
        }
        
        // 상태 업데이트 (실시간에서는 스킵)
        if (!skipStatusUpdate) {
            const statusElement = document.getElementById(`${metric}-status`);
            if (statusElement) {
                const activeCount = sensorData.length;
                const totalCount = this.sensorGroups[groupName]?.totalSensors || activeCount;
                statusElement.textContent = `${activeCount}/${totalCount} 활성`;
            } else if (metric !== 'pressure' && metric !== 'airquality' && metric !== 'temperature' && metric !== 'humidity') {
                // 온습도 센서는 통합 상태만 있고 개별 상태 엘리먼트는 없음
                console.warn(`⚠️ 상태 엘리먼트를 찾을 수 없음: ${metric}-status`);
            }
            
            // 그룹 통합 상태 업데이트 (온습도 센서의 경우)
            if (groupName === 'temp-humidity') {
                const groupStatusElement = document.getElementById('temp-humidity-status');
                if (groupStatusElement && metric === 'temperature') {
                    // BME688 물리적 센서 수에 기반한 계산 (온도 센서 수 = 물리적 센서 수)
                    const physicalSensorCount = sensorData.length; // 온도 센서 7개 = 물리적 BME688 7개
                    const totalPhysicalSensors = this.sensorGroups[groupName]?.totalSensors || physicalSensorCount;
                    
                    groupStatusElement.textContent = `${physicalSensorCount}/${totalPhysicalSensors} 활성`;
                    console.log(`📊 온습도 그룹 상태 업데이트: ${physicalSensorCount}/${totalPhysicalSensors} (물리적 센서 기준)`);
                }
            }
            
            // SHT40 그룹 상태 업데이트
            if (groupName === 'sht40') {
                const groupStatusElement = document.getElementById('sht40-sensor-status');
                if (groupStatusElement && metric === 'temperature') {
                    const activeCount = sensorData.length;
                    const totalCount = this.sensorGroups[groupName]?.totalSensors || activeCount;
                    
                    groupStatusElement.textContent = `${activeCount}/${totalCount} 활성`;
                    
                    const rangeElement = groupStatusElement.nextElementSibling;
                    if (rangeElement) {
                        rangeElement.textContent = activeCount === totalCount ? '모든 센서 정상' : '일부 센서 비활성';
                    }
                    
                    console.log(`📊 SHT40 그룹 상태 업데이트: ${activeCount}/${totalCount}`);
                }
                
                // SHT40 그룹 전체 상태 업데이트
                const sht40GroupStatus = document.getElementById('sht40-group-status');
                const sht40GroupSummary = document.getElementById('sht40-group-summary');
                
                if (sht40GroupStatus && metric === 'temperature') {
                    const activeCount = sensorData.length;
                    sht40GroupStatus.textContent = activeCount > 0 ? `${activeCount}개 연결됨` : '센서 검색 중...';
                    sht40GroupStatus.className = activeCount > 0 ? 'sensor-group-status online' : 'sensor-group-status offline';
                }
                
                if (sht40GroupSummary && metric === 'temperature') {
                    const activeCount = sensorData.length;
                    sht40GroupSummary.textContent = activeCount > 0 ? `SHT40×${activeCount}` : '센서 검색 중';
                }
            }
        }
    }

    // 상태바 업데이트
    updateStatusBar() {
        const now = new Date();
        const timeString = now.toLocaleString('ko-KR', {
            year: 'numeric',
            month: 'numeric', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = `마지막 업데이트: ${timeString}`;
        }
        
        const dbStatusElement = document.getElementById('db-status');
        if (dbStatusElement) {
            dbStatusElement.textContent = `데이터베이스 상태: 연결됨`;
        }
    }

    // 로딩 숨김
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            setTimeout(() => {
                overlay.style.opacity = '0';
                setTimeout(() => overlay.remove(), 300);
            }, 500);
        }
    }
}

// 문서 로드 완료 후 대시보드 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new EGIconDashboard();
});

// 페이지 언로드 시 리소스 정리 (메모리 최적화)
window.addEventListener('beforeunload', () => {
    if (window.dashboard) {
        Object.values(window.dashboard.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        if (window.dashboard.ws) {
            window.dashboard.ws.close();
        }
        if (window.dashboard.mockDataInterval) {
            clearInterval(window.dashboard.mockDataInterval);
        }
    }
});