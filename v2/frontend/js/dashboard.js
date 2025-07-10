// Modern Factory Dashboard JavaScript
class FactoryDashboard {
    constructor() {
        this.ws = null;
        this.processes = [
            { id: "deposition", name: "실장공정", status: "normal", sensors: 10, alerts: 0, icon: "🏭" },
            { id: "photo", name: "라미공정", status: "warning", sensors: 40, alerts: 1, icon: "📸" },
            { id: "etch", name: "조립공정", status: "danger", sensors: 80, alerts: 3, icon: "⚗️" },
            { id: "encapsulation", name: "검사공정", status: "normal", sensors: 30, alerts: 0, icon: "📦" },
        ];
        
        this.kpiData = {
            production_efficiency: { value: 94.2, trend: "up", change: 2.1 },
            equipment_utilization: { value: 87.8, trend: "up", change: 1.5 },
            quality_index: { value: 98.7, trend: "stable", change: 0.2 },
            energy_consumption: { value: 2847, trend: "down", change: -3.2 },
            ai_prediction_accuracy: { value: 91.4, trend: "up", change: 4.1 },
        };
        
        this.init();
    }

    init() {
        this.updateTime();
        this.renderProcesses();
        this.updateAlertSummary();
        this.connectWebSocket();
        
        // Update time every second
        setInterval(() => this.updateTime(), 1000);
        
        // Simulate real-time data updates
        setInterval(() => this.simulateDataUpdate(), 2000);
    }

    updateTime() {
        const now = new Date();
        const dateStr = now.toLocaleDateString('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        const timeStr = now.toLocaleTimeString('ko-KR');
        
        document.getElementById('current-date').textContent = dateStr;
        document.getElementById('current-time').textContent = timeStr;
    }

    renderProcesses() {
        const processList = document.getElementById('process-list');
        processList.innerHTML = '';
        
        this.processes.forEach(process => {
            const processItem = document.createElement('div');
            processItem.className = 'process-item';
            processItem.onclick = () => this.goToProcess(process.id);
            processItem.style.cursor = 'pointer';
            
            processItem.innerHTML = `
                <div class="process-left">
                    <div class="process-icon">${process.icon}</div>
                    <div>
                        <div class="process-name">${process.name}</div>
                        <div class="process-sensors">센서 ${process.sensors}개</div>
                    </div>
                </div>
                <div class="process-right">
                    ${process.alerts > 0 ? `<span class="badge badge-destructive">${process.alerts}건</span>` : ''}
                    <span class="badge badge-${process.status}">
                        ${this.getStatusIcon(process.status)}
                        <span>${this.getStatusText(process.status)}</span>
                    </span>
                </div>
            `;
            
            processList.appendChild(processItem);
        });
    }

    getStatusIcon(status) {
        switch (status) {
            case "normal":
                return `<svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                </svg>`;
            case "warning":
                return `<svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                </svg>`;
            case "danger":
                return `<svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>`;
            default:
                return `<svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>`;
        }
    }

    getStatusText(status) {
        switch (status) {
            case "normal": return "정상";
            case "warning": return "주의";
            case "danger": return "위험";
            default: return "알 수 없음";
        }
    }

    updateAlertSummary() {
        const totalAlerts = this.processes.reduce((sum, process) => sum + process.alerts, 0);
        const criticalProcesses = this.processes.filter(p => p.status === "danger").length;
        const warningProcesses = this.processes.filter(p => p.status === "warning").length;
        
        // Update alert count in header
        document.getElementById('alert-count').textContent = totalAlerts;
        
        // Show/hide alert summary
        const alertSummary = document.getElementById('alert-summary');
        const emergencyLight = document.getElementById('emergency-light');
        
        if (totalAlerts > 0) {
            alertSummary.classList.remove('hidden');
            document.getElementById('critical-count').textContent = criticalProcesses;
            document.getElementById('warning-count').textContent = warningProcesses;
            document.getElementById('total-alerts').textContent = totalAlerts;
            
            // Show emergency light if there are critical processes
            if (criticalProcesses > 0) {
                emergencyLight.classList.remove('hidden');
            } else {
                emergencyLight.classList.add('hidden');
            }
        } else {
            alertSummary.classList.add('hidden');
            emergencyLight.classList.add('hidden');
        }
    }

    updateKPI(data = null) {
        const kpi = data || this.kpiData;
        
        // Production Efficiency
        this.updateKPICard('production-efficiency', 'production-progress', 'production-trend', 
            kpi.production_efficiency.value, kpi.production_efficiency.trend, kpi.production_efficiency.change, '%');
        
        // Equipment Utilization
        this.updateKPICard('equipment-utilization', 'equipment-progress', 'equipment-trend',
            kpi.equipment_utilization.value, kpi.equipment_utilization.trend, kpi.equipment_utilization.change, '%');
        
        // Quality Index
        this.updateKPICard('quality-index', 'quality-progress', 'quality-trend',
            kpi.quality_index.value, kpi.quality_index.trend, kpi.quality_index.change, '%');
        
        // Energy Consumption
        document.getElementById('energy-consumption').textContent = `${kpi.energy_consumption.value.toLocaleString()}kW`;
        this.updateTrend('energy-trend', kpi.energy_consumption.trend, kpi.energy_consumption.change);
        
        // AI Prediction
        this.updateKPICard('ai-prediction', 'ai-progress', 'ai-trend',
            kpi.ai_prediction_accuracy.value, kpi.ai_prediction_accuracy.trend, kpi.ai_prediction_accuracy.change, '%');
    }

    updateKPICard(valueId, progressId, trendId, value, trend, change, unit) {
        document.getElementById(valueId).textContent = `${value.toFixed(1)}${unit}`;
        document.getElementById(progressId).style.width = `${value}%`;
        this.updateTrend(trendId, trend, Math.abs(change));
    }

    updateTrend(trendId, trend, change) {
        const trendElement = document.getElementById(trendId);
        if (!trendElement) return;
        
        trendElement.className = `kpi-trend trend-${trend}`;
        
        let icon;
        switch (trend) {
            case 'up':
                icon = `<svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                </svg>`;
                break;
            case 'down':
                icon = `<svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 13l-5 5-5-5m5 5V6"/>
                </svg>`;
                break;
            default:
                icon = `<svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/>
                </svg>`;
        }
        
        trendElement.innerHTML = `${icon}<span>${change}%</span>`;
    }

    simulateDataUpdate() {
        // Simulate small fluctuations in KPI data
        this.kpiData.production_efficiency.value = Math.max(85, Math.min(98, 
            this.kpiData.production_efficiency.value + (Math.random() - 0.5) * 0.5));
        
        this.kpiData.equipment_utilization.value = Math.max(80, Math.min(95, 
            this.kpiData.equipment_utilization.value + (Math.random() - 0.5) * 0.3));
        
        this.kpiData.quality_index.value = Math.max(95, Math.min(99.5, 
            this.kpiData.quality_index.value + (Math.random() - 0.5) * 0.2));
        
        this.kpiData.energy_consumption.value = Math.max(2500, Math.min(3200, 
            this.kpiData.energy_consumption.value + (Math.random() - 0.5) * 20));
        
        this.kpiData.ai_prediction_accuracy.value = Math.max(85, Math.min(95, 
            this.kpiData.ai_prediction_accuracy.value + (Math.random() - 0.5) * 0.3));
        
        // Add visual feedback for updates
        this.addUpdateAnimation();
        
        // Update the UI
        this.updateKPI();
    }

    addUpdateAnimation() {
        const kpiCards = document.querySelectorAll('.kpi-card');
        kpiCards.forEach(card => {
            card.classList.add('updating');
            setTimeout(() => card.classList.remove('updating'), 500);
        });
    }

    connectWebSocket() {
        try {
            // Use current host for WebSocket connection
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsHost = window.location.hostname;
            const wsPort = window.location.port || '8002';
            this.ws = new WebSocket(`${wsProtocol}//${wsHost}:${wsPort}/ws/realtime`);
            
            this.ws.onopen = () => {
                console.log('🔌 WebSocket 연결됨');
                
                // Send periodic ping
                setInterval(() => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 30000);
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'realtime_update') {
                    // API 응답 형식에 맞게 처리
                    if (data.data && data.data.factory_kpi) {
                        this.updateKPI(data.data.factory_kpi);
                    } else if (data.factory_kpi) {
                        this.updateKPI(data.factory_kpi);
                    }
                    
                    if (data.data && data.data.factory_layout) {
                        this.updateFactoryLayout(data.data.factory_layout);
                    }
                } else if (data.type === 'alert') {
                    this.showAlert(data);
                }
            };
            
            this.ws.onclose = () => {
                console.log('🔌 WebSocket 연결 끊김 - 재연결 시도 중...');
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket 오류:', error);
            };
            
        } catch (error) {
            console.error('WebSocket 연결 실패:', error);
            setTimeout(() => this.connectWebSocket(), 3000);
        }
    }

    updateFactoryLayout(layoutData) {
        console.log('공장 평면도 업데이트:', layoutData);
        // Implement factory layout updates if needed
    }

    showAlert(alertData) {
        console.log('알림:', alertData);
        // Implement alert display logic
        
        // Simple toast notification
        this.showToast(`🚨 ${alertData.message}`, 'error');
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? 'var(--color-red-600)' : 'var(--color-blue-600)'};
            color: white;
            padding: 1rem;
            border-radius: var(--rounded-lg);
            box-shadow: var(--shadow-md);
            z-index: 1000;
            max-width: 300px;
            font-size: 0.875rem;
            animation: slideInRight 0.3s ease-out;
        `;
        toast.textContent = message;
        
        // Add animation keyframes if not exists
        if (!document.querySelector('#toast-animations')) {
            const style = document.createElement('style');
            style.id = 'toast-animations';
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        // Remove toast after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 5000);
    }

    goToProcess(processId) {
        window.location.href = `/process/${processId}`;
    }

    // API methods
    async loadInitialData() {
        try {
            const response = await fetch('/api/factory/kpi');
            if (response.ok) {
                const data = await response.json();
                // API 데이터가 factory_kpi 래퍼를 가지고 있는 경우
                if (data.factory_kpi) {
                    this.updateKPI(data.factory_kpi);
                } else {
                    this.updateKPI(data);
                }
            } else {
                console.warn('API 응답 실패 - Mock 데이터 사용');
            }
        } catch (error) {
            console.error('초기 데이터 로드 실패:', error);
            console.log('Mock 데이터로 계속 진행');
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new FactoryDashboard();
    dashboard.loadInitialData();
    
    // Make dashboard globally accessible for debugging
    window.dashboard = dashboard;
});