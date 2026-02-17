/**
 * API Client para comunicación con el backend
 */

class HolographicAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.deviceId = null;
        this.sessionId = null;
    }

    setBaseUrl(url) {
        this.baseUrl = url;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API Error: ${endpoint}`, error);
            throw error;
        }
    }

    // ==========================================
    // HEALTH & STATUS
    // ==========================================

    async checkHealth() {
        try {
            const result = await this.request('/health');
            return result.status === 'healthy';
        } catch {
            return false;
        }
    }

    async getModes() {
        return this.request('/api/v1/modes');
    }

    // ==========================================
    // DEVICES
    // ==========================================

    async getDevices() {
        return this.request('/api/v1/devices');
    }

    async registerDevice(ip, name = 'Kiosk Fan') {
        const result = await this.request('/api/v1/devices', {
            method: 'POST',
            body: JSON.stringify({
                location_id: '00000000-0000-0000-0000-000000000001', // Default
                name: name,
                ip_address: ip,
                protocol_type: 'tcp'
            })
        });
        this.deviceId = result.id;
        return result;
    }

    async pingDevice(ip) {
        return this.request(`/api/v1/devices/${ip}/ping`, { method: 'POST' });
    }

    // ==========================================
    // SESSIONS
    // ==========================================

    async createSession(mode, avatarId = null) {
        if (!this.deviceId) {
            throw new Error('No device registered');
        }

        const result = await this.request('/api/v1/sessions', {
            method: 'POST',
            body: JSON.stringify({
                device_id: this.deviceId,
                mode: mode,
                avatar_id: avatarId
            })
        });
        this.sessionId = result.id;
        return result;
    }

    async endSession() {
        if (!this.sessionId) return;

        await this.request(`/api/v1/sessions/${this.sessionId}`, {
            method: 'DELETE'
        });
        this.sessionId = null;
    }

    // ==========================================
    // MEMORIAL MODE
    // ==========================================

    async uploadMemorialPhoto(photoFile, email = '', phone = '') {
        const formData = new FormData();
        formData.append('photo', photoFile);
        formData.append('user_email', email);
        formData.append('user_phone', phone);

        const response = await fetch(`${this.baseUrl}/api/v1/memorial/upload-photo`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status}`);
        }

        return response.json();
    }

    async getJobStatus(jobId) {
        return this.request(`/api/v1/memorial/jobs/${jobId}`);
    }

    async playMemorialAvatar(avatarId, loop = true, duration = 5) {
        return this.request(`/api/v1/memorial/play/${avatarId}`, {
            method: 'POST',
            body: JSON.stringify({
                device_id: this.deviceId,
                loop: loop,
                duration_seconds: duration
            })
        });
    }

    // ==========================================
    // RECEPTIONIST MODE
    // ==========================================

    async startReceptionist(avatarId, greeting = '¡Hola! ¿En qué puedo ayudarte?') {
        return this.request('/api/v1/receptionist/start', {
            method: 'POST',
            body: JSON.stringify({
                device_id: this.deviceId,
                avatar_id: avatarId,
                greeting_message: greeting
            })
        });
    }

    async sendMessage(text) {
        return this.request('/api/v1/receptionist/conversation', {
            method: 'POST',
            body: JSON.stringify({
                session_id: this.sessionId,
                text: text
            })
        });
    }

    async sendAudio(audioBlob) {
        const reader = new FileReader();
        return new Promise((resolve, reject) => {
            reader.onload = async () => {
                const base64 = reader.result.split(',')[1];
                try {
                    const result = await this.request('/api/v1/receptionist/conversation', {
                        method: 'POST',
                        body: JSON.stringify({
                            session_id: this.sessionId,
                            audio_base64: base64
                        })
                    });
                    resolve(result);
                } catch (e) {
                    reject(e);
                }
            };
            reader.onerror = reject;
            reader.readAsDataURL(audioBlob);
        });
    }

    async stopReceptionist() {
        if (this.sessionId) {
            return this.request(`/api/v1/receptionist/stop/${this.sessionId}`, {
                method: 'POST'
            });
        }
    }

    // ==========================================
    // MENU MODE
    // ==========================================

    async getMenuCategories(locationId = null) {
        let endpoint = '/api/v1/menu/categories';
        if (locationId) {
            endpoint += `?location_id=${locationId}`;
        }
        return this.request(endpoint);
    }

    async getMenuItems(categoryId = null, featured = false) {
        let endpoint = '/api/v1/menu/items?';
        if (categoryId) endpoint += `category_id=${categoryId}&`;
        if (featured) endpoint += 'featured_only=true&';
        return this.request(endpoint);
    }

    async getMenuItem(itemId) {
        return this.request(`/api/v1/menu/items/${itemId}`);
    }

    async showMenuItem(itemId, showVideo = false, narrate = true) {
        return this.request(`/api/v1/menu/show-item/${itemId}`, {
            method: 'POST',
            body: JSON.stringify({
                device_id: this.deviceId,
                show_video: showVideo,
                narrate: narrate
            })
        });
    }

    async getMenuRecommendations(preferences = [], restrictions = []) {
        return this.request('/api/v1/menu/recommend', {
            method: 'POST',
            body: JSON.stringify({
                session_id: this.sessionId,
                preferences: preferences,
                dietary_restrictions: restrictions
            })
        });
    }

    // ==========================================
    // CATALOG MODE
    // ==========================================

    async getCatalogCategories(locationId = null) {
        let endpoint = '/api/v1/catalog/categories';
        if (locationId) {
            endpoint += `?location_id=${locationId}`;
        }
        return this.request(endpoint);
    }

    async searchProducts(query = '', categoryId = null, filters = {}) {
        let endpoint = '/api/v1/catalog/products?';
        if (query) endpoint += `query=${encodeURIComponent(query)}&`;
        if (categoryId) endpoint += `category_id=${categoryId}&`;
        if (filters.minPrice) endpoint += `min_price=${filters.minPrice}&`;
        if (filters.maxPrice) endpoint += `max_price=${filters.maxPrice}&`;
        if (filters.size) endpoint += `size=${filters.size}&`;
        if (filters.color) endpoint += `color=${filters.color}&`;
        return this.request(endpoint);
    }

    async getProduct(productId) {
        return this.request(`/api/v1/catalog/products/${productId}`);
    }

    async checkProductAvailability(productId, locationId, size = null, color = null) {
        let endpoint = `/api/v1/catalog/products/${productId}/availability?location_id=${locationId}`;
        if (size) endpoint += `&size=${size}`;
        if (color) endpoint += `&color=${color}`;
        return this.request(endpoint);
    }

    async showProduct(productId, imageIndex = 0, rotate = false) {
        return this.request(`/api/v1/catalog/show-product/${productId}`, {
            method: 'POST',
            body: JSON.stringify({
                device_id: this.deviceId,
                image_index: imageIndex,
                rotate: rotate
            })
        });
    }

    // ==========================================
    // VIDEOCALL MODE
    // ==========================================

    async startVideocall(callerId) {
        // Crear oferta SDP (simplificada)
        const offer = await this.createWebRTCOffer();

        return this.request('/api/v1/videocall/start', {
            method: 'POST',
            body: JSON.stringify({
                device_id: this.deviceId,
                caller_id: callerId,
                webrtc_offer: offer
            })
        });
    }

    async addIceCandidate(candidate) {
        return this.request(`/api/v1/videocall/${this.sessionId}/ice`, {
            method: 'POST',
            body: JSON.stringify(candidate)
        });
    }

    async endVideocall() {
        if (this.sessionId) {
            return this.request(`/api/v1/videocall/${this.sessionId}/end`, {
                method: 'POST'
            });
        }
    }

    async createWebRTCOffer() {
        // Placeholder - en producción usar WebRTC real
        return 'v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=holographic\r\n';
    }

    // ==========================================
    // AVATARS
    // ==========================================

    async getAvatars(type = null) {
        let endpoint = '/api/v1/content/avatars';
        if (type) {
            endpoint += `?avatar_type=${type}`;
        }
        return this.request(endpoint);
    }

    // ==========================================
    // LOCATIONS
    // ==========================================

    async getLocations() {
        return this.request('/api/v1/locations');
    }
}

// Instancia global
const api = new HolographicAPI();
