/**
 * EG-ICON Dashboard - 차트 매니저
 * ===============================
 * 차트 생성, 업데이트, 관리 전담 모듈
 */

import { getSensorColor, parseSensorId } from '../utils/helpers.js';

export class ChartManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.charts = {};
        this.colorPalette = [
            '#ff6384', '#36a2eb', '#4bc0c0', '#ff9f40', 
            '#9966ff', '#ffcd56', '#c9cbcf', '#ff6384'
        ];
    }

    /**
     * 차트 초기화
     */
    initializeCharts() {
        // SHT40 전용 차트 생성
        this.createSHT40Charts();
        
        // SDP810 전용 차트 생성
        this.createSDP810Charts();
        
        // 센서 그룹 기반 차트 생성
        this.createChartsFromSensorGroups();
        
        console.log('📊 모든 차트 초기화 완료');
    }

    /**
     * 센서 그룹 기반 차트 생성
     */
    createChartsFromSensorGroups() {
        Object.entries(this.dashboard.sensorGroups).forEach(([groupName, group]) => {
            // 비활성화된 그룹은 건너뛰기
            if (group.disabled) {
                console.log(`📊 그룹 ${groupName}은 비활성화되어 차트 생성 스킵`);
                return;
            }
            
            if (group.totalSensors > 0) {
                // 각 메트릭별로 차트 생성
                group.metrics.forEach(metric => {
                    const normalizedMetric = metric.replace(/_/g, '-');
                    const chartId = `${normalizedMetric}-multi-chart`;
                    const sensorLabels = this.generateSensorLabels(group, metric);
                    
                    // BH1750 light 차트는 전용 핸들러에서 처리
                    if (chartId === 'light-multi-chart' || metric === 'light') {
                        console.log(`🚫 BH1750 light 차트는 BH1750ChartHandler에서 처리, dashboard.js에서 건너뜀`);
                        return;
                    }
                    
                    if (sensorLabels.length > 1) {
                        this.createMultiSensorChart(chartId, metric, sensorLabels);
                    } else {
                        this.createMultiSensorChart(chartId, metric, sensorLabels);
                    }
                });
            }
        });
    }

    /**
     * 센서 라벨 생성
     */
    generateSensorLabels(group, metric) {
        const labels = [];
        
        if (Array.isArray(group.sensors)) {
            group.sensors.forEach((sensorId, index) => {
                const parts = sensorId.split('_');
                if (parts.length >= 3) {
                    const sensorType = parts[0].toUpperCase();
                    const { bus, channel } = parseSensorId(sensorId);
                    const busLabel = bus === 0 ? 'CH1' : 'CH2';
                    labels.push(`${sensorType} ${busLabel}-Ch${channel}`);
                } else {
                    labels.push(`${group.title} ${index + 1}`);
                }
            });
        } else {
            Object.entries(group.sensors).forEach(([sensorType, sensorList]) => {
                if (Array.isArray(sensorList)) {
                    sensorList.forEach((sensorId) => {
                        const parts = sensorId.split('_');
                        if (parts.length >= 3) {
                            const type = parts[0].toUpperCase();
                            const { bus, channel } = parseSensorId(sensorId);
                            const busLabel = bus === 0 ? 'CH1' : 'CH2';
                            labels.push(`${type} ${busLabel}-Ch${channel}`);
                        } else {
                            labels.push(`${sensorType.toUpperCase()} 센서`);
                        }
                    });
                }
            });
        }
        
        return labels;
    }

    /**
     * 다중 센서 차트 생성
     */
    createMultiSensorChart(canvasId, sensorType, sensorLabels) {
        console.log(`📊 다중 센서 차트 생성 시작: ${canvasId}, 타입: ${sensorType}, 라벨: ${sensorLabels.length}개`);
        
        // BME688 차트 중복 생성 방지
        if ((canvasId === 'pressure-multi-chart' || canvasId === 'gas-resistance-multi-chart') && 
            this.charts[canvasId] && 
            this.charts[canvasId].data.datasets.length === 5) {
            console.log(`⚠️ BME688 차트 ${canvasId} 이미 5개 데이터셋으로 생성됨, 중복 생성 방지`);
            return;
        }
        
        // BH1750 차트는 전용 핸들러에서만 처리
        if (canvasId === 'light-multi-chart') {
            console.log(`⚠️ BH1750 차트 ${canvasId}는 BH1750ChartHandler에서 처리됨, dashboard.js에서 중복 생성 방지`);
            return;
        }
        
        // DOM 로드 확인
        if (document.readyState !== 'complete') {
            console.log(`⏳ DOM 로드 대기 중... readyState: ${document.readyState}`);
            setTimeout(() => {
                this.createMultiSensorChart(canvasId, sensorType, sensorLabels);
            }, 100);
            return;
        }
        
        const ctx = document.getElementById(canvasId);
        if (!ctx) {
            console.error(`❌ 차트 캔버스를 찾을 수 없음: ${canvasId}`);
            return;
        }

        // 기존 차트 제거
        this.destroyChart(canvasId);
        
        const sensorConfig = this.dashboard.sensorTypes[sensorType];
        if (!sensorConfig) {
            console.error(`❌ 센서 타입 설정을 찾을 수 없음: ${sensorType}`);
            return;
        }
        
        // 각 센서별 데이터셋 생성
        const datasets = sensorLabels.map((label, index) => {
            const color = this.colorPalette[index % this.colorPalette.length];
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
                            boxWidth: 12,
                            padding: 10,
                            font: {
                                size: 11
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        titleColor: '#333',
                        bodyColor: '#666',
                        borderColor: '#ddd',
                        borderWidth: 1,
                        cornerRadius: 6,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}${sensorConfig.unit || ''}`;
                            }
                        }
                    }
                },
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
                        min: sensorConfig.min,
                        max: sensorConfig.max,
                        title: {
                            display: true,
                            text: `${sensorConfig.label} (${sensorConfig.unit})`
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
        
        console.log(`✅ 다중 센서 차트 생성 완료: ${canvasId}`);
    }

    /**
     * SHT40 차트들 생성
     */
    createSHT40Charts() {
        this.createSHT40Chart('sht40-temperature-chart', 'temperature', 'SHT40 온도', '°C', '#ff6384', -10, 50);
        this.createSHT40Chart('sht40-humidity-chart', 'humidity', 'SHT40 습도', '%', '#36a2eb', 0, 100);
        console.log('📊 SHT40 전용 차트 생성 완료');
    }

    /**
     * SHT40 개별 차트 생성
     */
    createSHT40Chart(canvasId, metric, title, unit, color, min, max) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`⚠️ SHT40 차트 캔버스 찾을 수 없음: ${canvasId}`);
            return;
        }

        const ctx = canvas.getContext('2d');
        
        // 기존 차트 제거
        this.destroyChart(canvasId);

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

    /**
     * SDP810 차트들 생성
     */
    createSDP810Charts() {
        this.createSDP810Chart('sdp810-pressure-chart', 'pressure', 'SDP810 차압', 'Pa', '#4bc0c0', -500, 500);
        console.log('📊 SDP810 전용 차트 생성 완료');
    }

    /**
     * SDP810 개별 차트 생성
     */
    createSDP810Chart(canvasId, metric, title, unit, color, min, max) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.warn(`⚠️ SDP810 차트 캔버스 찾을 수 없음: ${canvasId}`);
            return;
        }

        const ctx = canvas.getContext('2d');
        
        // 기존 차트 제거
        this.destroyChart(canvasId);

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
        
        console.log(`📊 SDP810 ${metric} 차트 생성 완료: ${canvasId}`);
    }

    /**
     * 차트 라벨 업데이트
     */
    updateChartLabels(chartId, newLabels) {
        if (!this.charts[chartId]) {
            console.warn(`⚠️ 차트를 찾을 수 없음: ${chartId}`);
            return;
        }

        const chart = this.charts[chartId];
        const currentLabels = chart.data.datasets.map(ds => ds.label);
        
        if (JSON.stringify(currentLabels) !== JSON.stringify(newLabels)) {
            console.log(`🔄 차트 라벨 변경 감지: ${chartId}`);
            this.recreateChart(chartId, newLabels);
        }
    }

    /**
     * 차트 재생성
     */
    recreateChart(chartId, sensorLabels) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        
        // 기존 차트 삭제
        this.destroyChart(chartId);
        
        // 센서 타입 추출
        const sensorType = chartId.replace('-multi-chart', '');
        
        // 새 차트 생성
        this.createMultiSensorChart(chartId, sensorType, sensorLabels);
    }

    /**
     * 차트 파괴
     */
    destroyChart(canvasId) {
        const existingChart = Chart.getChart(canvasId);
        if (existingChart) {
            console.log(`🗑️ 기존 차트 파괴: ${canvasId}`);
            existingChart.destroy();
        }
        
        if (this.charts[canvasId]) {
            delete this.charts[canvasId];
        }
    }

    /**
     * 모든 차트 파괴
     */
    destroyAllCharts() {
        Object.keys(this.charts).forEach(chartId => {
            this.destroyChart(chartId);
        });
        console.log('🗑️ 모든 차트 파괴 완료');
    }

    /**
     * 차트 가져오기
     */
    getChart(canvasId) {
        return this.charts[canvasId];
    }

    /**
     * 모든 차트 가져오기
     */
    getAllCharts() {
        return this.charts;
    }
}