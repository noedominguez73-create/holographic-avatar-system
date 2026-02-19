/**
 * Admin Dashboard - Holographic Avatar System
 */

class AdminDashboard {
    constructor() {
        this.isAuthenticated = false;
        this.pin = '';
        this.attempts = 0;
        this.maxAttempts = 3;
        this.sessionTimeout = null;
        this.healthInterval = null;
        this.config = this.loadConfig();

        this.init();
    }

    // ==========================================
    // INITIALIZATION
    // ==========================================

    init() {
        // Setup PIN keypad
        this.setupPinKeypad();

        // Setup navigation
        this.setupNavigation();

        // Setup event listeners
        this.setupEventListeners();

        // Check if already authenticated (session)
        if (this.checkSession()) {
            this.showDashboard();
        }
    }

    loadConfig() {
        const saved = localStorage.getItem('admin-config');
        return saved ? JSON.parse(saved) : {
            pin: '1234',
            apiUrl: 'http://localhost:8000',
            fanIp: '192.168.4.1',
            sessionTimeout: 30,
            autoRefresh: true
        };
    }

    saveConfig() {
        localStorage.setItem('admin-config', JSON.stringify(this.config));
    }

    // ==========================================
    // PIN AUTHENTICATION
    // ==========================================

    setupPinKeypad() {
        document.querySelectorAll('.pin-key').forEach(key => {
            key.addEventListener('click', () => {
                const value = key.dataset.key;
                this.handlePinKey(value);
            });
        });
    }

    handlePinKey(key) {
        const dots = document.querySelectorAll('.pin-dot');
        const errorEl = document.getElementById('pin-error');

        if (key === 'clear') {
            this.pin = '';
            dots.forEach(dot => dot.classList.remove('filled'));
            errorEl.classList.add('hidden');
        } else if (key === 'back') {
            if (this.pin.length > 0) {
                this.pin = this.pin.slice(0, -1);
                dots[this.pin.length].classList.remove('filled');
            }
        } else {
            if (this.pin.length < 4) {
                this.pin += key;
                dots[this.pin.length - 1].classList.add('filled');

                if (this.pin.length === 4) {
                    setTimeout(() => this.validatePin(), 200);
                }
            }
        }
    }

    validatePin() {
        if (this.pin === this.config.pin) {
            this.isAuthenticated = true;
            this.attempts = 0;
            this.setSession();
            this.showDashboard();
        } else {
            this.attempts++;
            this.pin = '';
            document.querySelectorAll('.pin-dot').forEach(dot => dot.classList.remove('filled'));

            const errorEl = document.getElementById('pin-error');
            if (this.attempts >= this.maxAttempts) {
                errorEl.textContent = 'Demasiados intentos. Espera 30 segundos.';
                errorEl.classList.remove('hidden');
                document.querySelectorAll('.pin-key').forEach(k => k.disabled = true);
                setTimeout(() => {
                    this.attempts = 0;
                    document.querySelectorAll('.pin-key').forEach(k => k.disabled = false);
                    errorEl.classList.add('hidden');
                }, 30000);
            } else {
                errorEl.textContent = `PIN incorrecto. Intentos restantes: ${this.maxAttempts - this.attempts}`;
                errorEl.classList.remove('hidden');
            }
        }
    }

    setSession() {
        const expiry = Date.now() + (this.config.sessionTimeout * 60 * 1000);
        localStorage.setItem('admin-session', expiry.toString());
    }

    checkSession() {
        const expiry = localStorage.getItem('admin-session');
        if (expiry && Date.now() < parseInt(expiry)) {
            return true;
        }
        localStorage.removeItem('admin-session');
        return false;
    }

    logout() {
        localStorage.removeItem('admin-session');
        this.isAuthenticated = false;
        clearInterval(this.healthInterval);
        document.getElementById('dashboard').classList.add('hidden');
        document.getElementById('pin-modal').classList.add('active');
        this.pin = '';
        document.querySelectorAll('.pin-dot').forEach(dot => dot.classList.remove('filled'));
    }

    showDashboard() {
        document.getElementById('pin-modal').classList.remove('active');
        document.getElementById('dashboard').classList.remove('hidden');

        // Load initial data
        this.loadSystemHealth();
        this.loadDevices();
        this.loadSessions();
        this.loadAvatars();
        this.loadConfigUI();

        // Start auto-refresh if enabled
        if (this.config.autoRefresh) {
            this.startAutoRefresh();
        }

        // Reset session timeout on activity
        document.addEventListener('click', () => this.setSession());
    }

    // ==========================================
    // NAVIGATION
    // ==========================================

    setupNavigation() {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabId = tab.dataset.tab;
                this.switchTab(tabId);
            });
        });
    }

    switchTab(tabId) {
        // Update tabs
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelector(`.nav-tab[data-tab="${tabId}"]`).classList.add('active');

        // Update panels
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        document.getElementById(`tab-${tabId}`).classList.add('active');
    }

    // ==========================================
    // EVENT LISTENERS
    // ==========================================

    setupEventListeners() {
        // Logout
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());

        // Refresh health
        document.getElementById('refresh-health').addEventListener('click', () => this.loadSystemHealth());

        // Refresh sessions
        document.getElementById('refresh-sessions').addEventListener('click', () => this.loadSessions());

        // Add device
        document.getElementById('add-device-btn').addEventListener('click', () => this.showDeviceModal());

        // Device form
        document.getElementById('device-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveDevice();
        });

        // Upload avatar
        document.getElementById('upload-avatar-btn').addEventListener('click', () => this.showAvatarModal());

        // Avatar form
        document.getElementById('avatar-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadAvatar();
        });

        // Avatar file preview
        document.getElementById('avatar-file').addEventListener('change', (e) => {
            this.previewAvatarFile(e.target.files[0]);
        });

        // Avatar filter
        document.getElementById('avatar-filter').addEventListener('change', (e) => {
            this.loadAvatars(e.target.value);
        });

        // Modal close buttons
        document.querySelectorAll('[data-close]').forEach(btn => {
            btn.addEventListener('click', () => {
                const modalId = btn.dataset.close;
                const modal = document.getElementById(modalId);
                modal.classList.add('hidden');
                modal.classList.remove('active');
            });
        });

        // Accordion
        document.querySelectorAll('.accordion-header').forEach(header => {
            header.addEventListener('click', () => {
                header.parentElement.classList.toggle('open');
            });
        });

        // Range sliders
        this.setupRangeSliders();

        // Save buttons
        document.getElementById('save-modes-btn').addEventListener('click', () => this.saveModes());
        document.getElementById('save-ai-btn').addEventListener('click', () => this.saveAI());
        document.getElementById('save-processing-btn').addEventListener('click', () => this.saveProcessing());
        document.getElementById('change-pin-btn').addEventListener('click', () => this.changePin());
        document.getElementById('save-connection-btn').addEventListener('click', () => this.saveConnection());
    }

    setupRangeSliders() {
        const sliders = [
            { id: 'memorial-duration', suffix: 's' },
            { id: 'receptionist-timeout', suffix: 's' },
            { id: 'videocall-fps', suffix: ' FPS' },
            { id: 'tts-rate', suffix: '%', prefix: true },
            { id: 'tts-volume', suffix: '%' },
            { id: 'llm-temperature', transform: v => (v / 100).toFixed(1) },
            { id: 'llm-max-tokens', suffix: '' },
            { id: 'avatar-fps', suffix: '' },
            { id: 'fp-resolution', suffix: 'px' },
            { id: 'fp-brightness', transform: v => (v / 100).toFixed(1) },
            { id: 'fp-contrast', transform: v => (v / 100).toFixed(1) }
        ];

        sliders.forEach(slider => {
            const el = document.getElementById(slider.id);
            if (!el) return;

            const valueEl = el.parentElement.querySelector('.range-value') ||
                           document.getElementById(`${slider.id}-value`);

            if (valueEl) {
                const updateValue = () => {
                    let value = el.value;
                    if (slider.transform) {
                        value = slider.transform(parseInt(value));
                    } else if (slider.prefix && parseInt(value) > 0) {
                        value = '+' + value;
                    }
                    valueEl.textContent = value + (slider.suffix || '');
                };

                el.addEventListener('input', updateValue);
                updateValue();
            }
        });
    }

    // ==========================================
    // SYSTEM HEALTH
    // ==========================================

    async loadSystemHealth() {
        const services = [
            { id: 'orchestrator', url: `${this.config.apiUrl}/health`, port: 8000 },
            { id: 'frame-processor', url: `${this.config.apiUrl.replace(':8000', ':8010')}/health`, port: 8010 },
            { id: 'polar-encoder', url: `${this.config.apiUrl.replace(':8000', ':8011')}/health`, port: 8011 },
            { id: 'fan-driver', url: `${this.config.apiUrl.replace(':8000', ':8012')}/health`, port: 8012 },
            { id: 'linly-tts', url: `${this.config.apiUrl.replace(':8000', ':8001')}/health`, port: 8001 },
            { id: 'linly-llm', url: `${this.config.apiUrl.replace(':8000', ':8002')}/health`, port: 8002 },
            { id: 'linly-asr', url: `${this.config.apiUrl.replace(':8000', ':8004')}/health`, port: 8004 },
            { id: 'faster-liveportrait', url: `${this.config.apiUrl.replace(':8000', ':9871')}/`, port: 9871 }
        ];

        let onlineCount = 0;

        for (const service of services) {
            const card = document.querySelector(`.service-card[data-service="${service.id}"]`);
            if (!card) continue;

            const statusEl = card.querySelector('.service-status');
            if (!statusEl) continue;

            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 3000);

                const response = await fetch(service.url, { signal: controller.signal });
                clearTimeout(timeoutId);

                if (response.ok) {
                    statusEl.classList.remove('offline');
                    statusEl.classList.add('online');
                    onlineCount++;
                } else {
                    statusEl.classList.remove('online');
                    statusEl.classList.add('offline');
                }
            } catch {
                statusEl.classList.remove('online');
                statusEl.classList.add('offline');
            }
        }

        document.getElementById('online-count').textContent = onlineCount;
        document.getElementById('last-update').textContent = `Última actualización: ${new Date().toLocaleTimeString()}`;
    }

    startAutoRefresh() {
        this.healthInterval = setInterval(() => {
            this.loadSystemHealth();
        }, 10000);
    }

    // ==========================================
    // DEVICES
    // ==========================================

    async loadDevices() {
        try {
            const response = await fetch(`${this.config.apiUrl}/api/v1/devices`);
            const devices = await response.json();

            const tbody = document.getElementById('devices-table-body');

            if (!Array.isArray(devices) || devices.length === 0) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No hay dispositivos registrados</td></tr>';
            } else {
                tbody.innerHTML = devices.map(device => `
                    <tr data-id="${device.id}">
                        <td>${device.name}</td>
                        <td>${device.ip_address}</td>
                        <td><span class="status-badge ${device.status}">${device.status}</span></td>
                        <td>${device.protocol_type.toUpperCase()}</td>
                        <td>${device.last_heartbeat ? new Date(device.last_heartbeat).toLocaleString() : 'Nunca'}</td>
                        <td class="action-buttons">
                            <button class="btn-secondary btn-small" onclick="admin.pingDevice('${device.id}')">Ping</button>
                            <button class="btn-secondary btn-small" onclick="admin.editDevice('${device.id}')">Editar</button>
                            <button class="btn-danger btn-small" onclick="admin.deleteDevice('${device.id}')">Eliminar</button>
                        </td>
                    </tr>
                `).join('');
            }

            document.getElementById('devices-count').textContent = devices.length;
        } catch (e) {
            console.error('Error loading devices:', e);
            this.showToast('Error al cargar dispositivos', 'error');
        }
    }

    showDeviceModal(device = null) {
        document.getElementById('device-modal-title').textContent = device ? 'Editar Dispositivo' : 'Agregar Dispositivo';
        document.getElementById('device-id').value = device?.id || '';
        document.getElementById('device-name').value = device?.name || '';
        document.getElementById('device-ip').value = device?.ip_address || '';
        document.getElementById('device-protocol').value = device?.protocol_type || 'tcp';
        document.getElementById('device-tcp-port').value = device?.tcp_port || 5499;
        document.getElementById('device-modal').classList.remove('hidden');
        document.getElementById('device-modal').classList.add('active');
    }

    async saveDevice() {
        const id = document.getElementById('device-id').value;
        const data = {
            name: document.getElementById('device-name').value,
            ip_address: document.getElementById('device-ip').value,
            protocol_type: document.getElementById('device-protocol').value,
            tcp_port: parseInt(document.getElementById('device-tcp-port').value),
            location_id: '00000000-0000-0000-0000-000000000001'
        };

        try {
            const url = id ? `${this.config.apiUrl}/api/v1/devices/${id}` : `${this.config.apiUrl}/api/v1/devices`;
            const method = id ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                document.getElementById('device-modal').classList.add('hidden');
                document.getElementById('device-modal').classList.remove('active');
                this.loadDevices();
                this.showToast('Dispositivo guardado correctamente', 'success');
            } else {
                throw new Error('Error al guardar');
            }
        } catch (e) {
            console.error('Error saving device:', e);
            this.showToast('Error al guardar dispositivo', 'error');
        }
    }

    async editDevice(id) {
        try {
            const response = await fetch(`${this.config.apiUrl}/api/v1/devices/${id}`);
            const device = await response.json();
            this.showDeviceModal(device);
        } catch (e) {
            this.showToast('Error al cargar dispositivo', 'error');
        }
    }

    async deleteDevice(id) {
        if (!confirm('¿Estás seguro de eliminar este dispositivo?')) return;

        try {
            const response = await fetch(`${this.config.apiUrl}/api/v1/devices/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadDevices();
                this.showToast('Dispositivo eliminado', 'success');
            }
        } catch (e) {
            this.showToast('Error al eliminar dispositivo', 'error');
        }
    }

    async pingDevice(id) {
        try {
            const response = await fetch(`${this.config.apiUrl}/api/v1/devices/${id}/ping`, {
                method: 'POST'
            });

            if (response.ok) {
                const result = await response.json();
                const latency = result.latency_ms ? `${result.latency_ms}ms` : 'OK';
                this.showToast(`Ping exitoso: ${latency}`, 'success');
                this.loadDevices();
            } else {
                this.showToast('Dispositivo no responde', 'warning');
            }
        } catch (e) {
            this.showToast('Error al hacer ping', 'error');
        }
    }

    // ==========================================
    // SESSIONS
    // ==========================================

    async loadSessions() {
        try {
            const response = await fetch(`${this.config.apiUrl}/api/v1/sessions`);
            const sessions = await response.json();

            const tbody = document.getElementById('sessions-table-body');

            if (!Array.isArray(sessions) || sessions.length === 0) {
                tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No hay sesiones activas</td></tr>';
            } else {
                tbody.innerHTML = sessions.map(session => {
                    const duration = this.formatDuration(new Date() - new Date(session.started_at));
                    return `
                        <tr data-id="${session.id}">
                            <td>${session.device_name || session.device_id}</td>
                            <td>${session.mode}</td>
                            <td>${new Date(session.started_at).toLocaleString()}</td>
                            <td>${duration}</td>
                            <td class="action-buttons">
                                <button class="btn-danger btn-small" onclick="admin.endSession('${session.id}')">Terminar</button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            document.getElementById('sessions-count').textContent = sessions.length;
        } catch (e) {
            console.error('Error loading sessions:', e);
        }
    }

    formatDuration(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        }
        return `${seconds}s`;
    }

    async endSession(id) {
        if (!confirm('¿Terminar esta sesión?')) return;

        try {
            await fetch(`${this.config.apiUrl}/api/v1/sessions/${id}`, {
                method: 'DELETE'
            });
            this.loadSessions();
            this.showToast('Sesión terminada', 'success');
        } catch (e) {
            this.showToast('Error al terminar sesión', 'error');
        }
    }

    // ==========================================
    // AVATARS
    // ==========================================

    async loadAvatars(filter = '') {
        try {
            let url = `${this.config.apiUrl}/api/v1/content/avatars`;
            if (filter) {
                url += `?avatar_type=${filter}`;
            }

            const response = await fetch(url);
            const avatars = await response.json();

            const grid = document.getElementById('avatars-grid');

            if (!Array.isArray(avatars) || avatars.length === 0) {
                grid.innerHTML = '<div class="avatar-card placeholder"><div class="avatar-placeholder">No hay avatares</div></div>';
            } else {
                grid.innerHTML = avatars.map(avatar => `
                    <div class="avatar-card" data-id="${avatar.id}">
                        <img src="${avatar.image_url || 'assets/placeholder-avatar.jpg'}" alt="${avatar.name}">
                        <div class="avatar-card-info">
                            <h4>${avatar.name}</h4>
                            <span class="avatar-type">${avatar.avatar_type}</span>
                        </div>
                        <div class="avatar-card-actions">
                            <button class="btn-secondary btn-small" onclick="admin.generateAnimation('${avatar.id}')">Animar</button>
                            <button class="btn-danger btn-small" onclick="admin.deleteAvatar('${avatar.id}')">Eliminar</button>
                        </div>
                    </div>
                `).join('');
            }
        } catch (e) {
            console.error('Error loading avatars:', e);
        }
    }

    showAvatarModal() {
        document.getElementById('avatar-form').reset();
        document.getElementById('avatar-preview').innerHTML = '';
        document.getElementById('avatar-modal').classList.remove('hidden');
        document.getElementById('avatar-modal').classList.add('active');
    }

    previewAvatarFile(file) {
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('avatar-preview').innerHTML = `<img src="${e.target.result}" alt="Preview">`;
        };
        reader.readAsDataURL(file);
    }

    async uploadAvatar() {
        const file = document.getElementById('avatar-file').files[0];
        const name = document.getElementById('avatar-name').value;
        const type = document.getElementById('avatar-type').value;

        if (!file) {
            this.showToast('Selecciona una imagen', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('image', file);
        formData.append('name', name);
        formData.append('avatar_type', type);

        try {
            const response = await fetch(`${this.config.apiUrl}/api/v1/content/avatars`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                document.getElementById('avatar-modal').classList.add('hidden');
                document.getElementById('avatar-modal').classList.remove('active');
                this.loadAvatars();
                this.showToast('Avatar subido correctamente', 'success');
            } else {
                throw new Error('Error al subir');
            }
        } catch (e) {
            console.error('Error uploading avatar:', e);
            this.showToast('Error al subir avatar', 'error');
        }
    }

    async generateAnimation(id) {
        this.showToast('Generando animación...', 'warning');

        try {
            const response = await fetch(`${this.config.apiUrl}/api/v1/content/avatars/${id}/generate-animation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    driving_source: 'natural',
                    duration_seconds: 5
                })
            });

            if (response.ok) {
                this.showToast('Animación generada', 'success');
            } else {
                throw new Error('Error');
            }
        } catch (e) {
            this.showToast('Error al generar animación', 'error');
        }
    }

    async deleteAvatar(id) {
        if (!confirm('¿Eliminar este avatar?')) return;

        try {
            await fetch(`${this.config.apiUrl}/api/v1/content/avatars/${id}`, {
                method: 'DELETE'
            });
            this.loadAvatars();
            this.showToast('Avatar eliminado', 'success');
        } catch (e) {
            this.showToast('Error al eliminar avatar', 'error');
        }
    }

    // ==========================================
    // CONFIGURATION
    // ==========================================

    loadConfigUI() {
        // Load saved settings into UI
        document.getElementById('settings-api-url').value = this.config.apiUrl;
        document.getElementById('settings-fan-ip').value = this.config.fanIp;
        document.getElementById('session-timeout').value = this.config.sessionTimeout;
        document.getElementById('auto-refresh').checked = this.config.autoRefresh;
    }

    saveModes() {
        const modesConfig = {
            memorial: {
                duration: document.getElementById('memorial-duration').value,
                loops: document.getElementById('memorial-loops').value,
                preset: document.getElementById('memorial-preset').value,
                savePhotos: document.getElementById('memorial-save-photos').checked
            },
            receptionist: {
                greeting: document.getElementById('receptionist-greeting').value,
                farewell: document.getElementById('receptionist-farewell').value,
                timeout: document.getElementById('receptionist-timeout').value,
                idle: document.getElementById('receptionist-idle').value
            },
            menu: {
                showPrices: document.getElementById('menu-show-prices').checked,
                showVideos: document.getElementById('menu-show-videos').checked,
                recommendations: document.getElementById('menu-recommendations').checked,
                narration: document.getElementById('menu-narration').checked
            },
            catalog: {
                showStock: document.getElementById('catalog-show-stock').checked,
                showSizes: document.getElementById('catalog-show-sizes').checked,
                showColors: document.getElementById('catalog-show-colors').checked,
                rotation3d: document.getElementById('catalog-3d-rotation').checked
            },
            videocall: {
                fps: document.getElementById('videocall-fps').value,
                quality: document.getElementById('videocall-quality').value,
                audio: document.getElementById('videocall-audio').checked,
                stun: document.getElementById('videocall-stun').value
            }
        };

        localStorage.setItem('modes-config', JSON.stringify(modesConfig));
        this.showToast('Configuración de modos guardada', 'success');
    }

    saveAI() {
        const aiConfig = {
            tts: {
                engine: document.getElementById('tts-engine').value,
                voice: document.getElementById('tts-voice').value,
                rate: document.getElementById('tts-rate').value,
                volume: document.getElementById('tts-volume').value
            },
            llm: {
                model: document.getElementById('llm-model').value,
                temperature: document.getElementById('llm-temperature').value / 100,
                maxTokens: document.getElementById('llm-max-tokens').value
            },
            asr: {
                model: document.getElementById('asr-model').value,
                language: document.getElementById('asr-language').value
            },
            avatar: {
                engine: document.getElementById('avatar-engine').value,
                preprocess: document.getElementById('avatar-preprocess').value,
                fps: document.getElementById('avatar-fps').value
            }
        };

        localStorage.setItem('ai-config', JSON.stringify(aiConfig));
        this.showToast('Configuración AI guardada', 'success');
    }

    saveProcessing() {
        const processingConfig = {
            frameProcessor: {
                resolution: document.getElementById('fp-resolution').value,
                brightness: document.getElementById('fp-brightness').value / 100,
                contrast: document.getElementById('fp-contrast').value / 100,
                circular: document.getElementById('fp-circular').checked,
                removeBg: document.getElementById('fp-remove-bg').checked
            },
            polarEncoder: {
                dithering: document.getElementById('pe-dithering').value
            }
        };

        localStorage.setItem('processing-config', JSON.stringify(processingConfig));
        this.showToast('Configuración de procesamiento guardada', 'success');
    }

    changePin() {
        const newPin = document.getElementById('new-pin').value;
        const confirmPin = document.getElementById('confirm-pin').value;

        if (newPin.length < 4 || newPin.length > 6) {
            this.showToast('El PIN debe tener 4-6 dígitos', 'warning');
            return;
        }

        if (newPin !== confirmPin) {
            this.showToast('Los PINs no coinciden', 'error');
            return;
        }

        this.config.pin = newPin;
        this.saveConfig();
        document.getElementById('new-pin').value = '';
        document.getElementById('confirm-pin').value = '';
        this.showToast('PIN actualizado correctamente', 'success');
    }

    saveConnection() {
        this.config.apiUrl = document.getElementById('settings-api-url').value;
        this.config.fanIp = document.getElementById('settings-fan-ip').value;
        this.config.sessionTimeout = parseInt(document.getElementById('session-timeout').value);
        this.config.autoRefresh = document.getElementById('auto-refresh').checked;

        this.saveConfig();

        // Update API client
        if (typeof api !== 'undefined') {
            api.setBaseUrl(this.config.apiUrl);
        }

        this.showToast('Configuración de conexión guardada', 'success');
    }

    // ==========================================
    // TOAST NOTIFICATIONS
    // ==========================================

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 4000);
    }
}

// Initialize dashboard
const admin = new AdminDashboard();
