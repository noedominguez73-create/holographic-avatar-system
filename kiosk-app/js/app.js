/**
 * Holographic Avatar Kiosk - Main Application
 */

class KioskApp {
    constructor() {
        this.currentScreen = 'splash-screen';
        this.currentMode = null;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.settings = this.loadSettings();

        this.init();
    }

    // ==========================================
    // INITIALIZATION
    // ==========================================

    init() {
        // Configurar API
        api.setBaseUrl(this.settings.apiUrl);

        // Event listeners
        this.setupEventListeners();

        // Verificar conexión
        this.checkConnection();

        // Auto-refresh de estado
        setInterval(() => this.checkConnection(), 30000);
    }

    setupEventListeners() {
        // Splash screen
        document.getElementById('splash-screen').addEventListener('click', () => {
            this.showScreen('main-menu');
        });

        // Mode cards
        document.querySelectorAll('.mode-card').forEach(card => {
            card.addEventListener('click', () => {
                const mode = card.dataset.mode;
                this.startMode(mode);
            });
        });

        // Back buttons
        document.querySelectorAll('.back-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = btn.dataset.back;
                this.endCurrentMode();
                this.showScreen(target);
            });
        });

        // Settings
        document.getElementById('settings-fab').addEventListener('click', () => {
            this.showSettings();
        });

        document.getElementById('close-settings').addEventListener('click', () => {
            this.hideSettings();
        });

        document.getElementById('save-settings').addEventListener('click', () => {
            this.saveSettings();
        });

        // Memorial mode
        this.setupMemorialListeners();

        // Receptionist mode
        this.setupReceptionistListeners();

        // Menu mode
        this.setupMenuListeners();

        // Catalog mode
        this.setupCatalogListeners();

        // Videocall mode
        this.setupVideocallListeners();
    }

    // ==========================================
    // SCREEN MANAGEMENT
    // ==========================================

    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });

        const screen = document.getElementById(screenId);
        if (screen) {
            screen.classList.add('active');
            this.currentScreen = screenId;
        }
    }

    async startMode(mode) {
        this.currentMode = mode;
        const screenId = `${mode}-screen`;
        this.showScreen(screenId);

        // Inicializar modo específico
        switch (mode) {
            case 'memorial':
                this.initMemorialMode();
                break;
            case 'receptionist':
                await this.initReceptionistMode();
                break;
            case 'menu':
                await this.initMenuMode();
                break;
            case 'catalog':
                await this.initCatalogMode();
                break;
            case 'videocall':
                this.initVideocallMode();
                break;
        }
    }

    endCurrentMode() {
        switch (this.currentMode) {
            case 'receptionist':
                api.stopReceptionist();
                break;
            case 'videocall':
                // Limpiar completamente la videollamada
                this.stopFrameCapture();
                clearInterval(this.callTimerInterval);
                if (this.localStream) {
                    this.localStream.getTracks().forEach(t => t.stop());
                    this.localStream = null;
                }
                api.endVideocall();
                break;
            case 'memorial':
                // Limpiar cámara de selfie si está activa
                if (this.selfieStream) {
                    this.selfieStream.getTracks().forEach(t => t.stop());
                    this.selfieStream = null;
                }
                break;
        }
        this.currentMode = null;
    }

    // ==========================================
    // CONNECTION STATUS
    // ==========================================

    async checkConnection() {
        const statusEl = document.getElementById('connection-status');
        const deviceEl = document.getElementById('device-status');

        try {
            const healthy = await api.checkHealth();
            if (healthy) {
                statusEl.textContent = '● Conectado';
                statusEl.classList.remove('offline');
                statusEl.classList.add('online');

                // Verificar dispositivo
                const devices = await api.getDevices();
                if (devices.length > 0) {
                    api.deviceId = devices[0].id;
                    deviceEl.textContent = `${devices[0].name} (${devices[0].ip_address})`;
                } else {
                    deviceEl.textContent = 'Sin dispositivo';
                }
            }
        } catch {
            statusEl.textContent = '● Desconectado';
            statusEl.classList.remove('online');
            statusEl.classList.add('offline');
            deviceEl.textContent = 'Sin conexión al servidor';
        }
    }

    // ==========================================
    // MEMORIAL MODE
    // ==========================================

    setupMemorialListeners() {
        const photoInput = document.getElementById('photo-input');
        const uploadArea = document.getElementById('upload-area');
        const generateBtn = document.getElementById('generate-avatar');
        const changePhotoBtn = document.getElementById('change-photo');

        photoInput.addEventListener('change', (e) => {
            this.handlePhotoSelect(e.target.files[0]);
        });

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                this.handlePhotoSelect(e.dataTransfer.files[0]);
            }
        });

        generateBtn.addEventListener('click', () => {
            this.generateMemorialAvatar();
        });

        changePhotoBtn.addEventListener('click', () => {
            this.resetMemorialUpload();
        });

        document.getElementById('take-selfie').addEventListener('click', () => {
            this.takeSelfie();
        });

        document.getElementById('replay-avatar').addEventListener('click', () => {
            this.replayAvatar();
        });

        document.getElementById('capture-photo-btn').addEventListener('click', () => {
            this.capturePhoto();
        });

        document.getElementById('cancel-camera-btn').addEventListener('click', () => {
            this.cancelCamera();
        });

        document.getElementById('save-selfie').addEventListener('click', () => {
            this.saveSelfie();
        });

        document.getElementById('retake-selfie').addEventListener('click', () => {
            this.takeSelfie();
        });
    }

    initMemorialMode() {
        this.resetMemorialUpload();
        this.showMemorialStep(1);
    }

    handlePhotoSelect(file) {
        if (!file || !file.type.startsWith('image/')) return;

        this.selectedPhoto = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('preview-img').src = e.target.result;
            document.getElementById('upload-area').classList.add('hidden');
            document.getElementById('photo-preview').classList.remove('hidden');
            document.getElementById('generate-avatar').disabled = false;
        };
        reader.readAsDataURL(file);
    }

    resetMemorialUpload() {
        this.selectedPhoto = null;
        document.getElementById('photo-input').value = '';
        document.getElementById('upload-area').classList.remove('hidden');
        document.getElementById('photo-preview').classList.add('hidden');
        document.getElementById('generate-avatar').disabled = true;
    }

    showMemorialStep(step) {
        document.querySelectorAll('.memorial-step').forEach(s => {
            s.classList.remove('active');
        });
        document.getElementById(`memorial-step-${step}`).classList.add('active');
    }

    async generateMemorialAvatar() {
        if (!this.selectedPhoto) return;

        this.showMemorialStep(2);

        try {
            // Subir foto
            document.getElementById('processing-status').textContent = 'Subiendo foto...';
            document.getElementById('progress-fill').style.width = '20%';

            const result = await api.uploadMemorialPhoto(this.selectedPhoto);
            const jobId = result.job_id;
            this.currentAvatarId = result.avatar_id;

            // Polling del estado
            await this.pollJobStatus(jobId);

            // Reproducir en ventilador
            document.getElementById('processing-status').textContent = 'Proyectando en holograma...';
            document.getElementById('progress-fill').style.width = '90%';

            const playResult = await api.playMemorialAvatar(this.currentAvatarId);
            this.currentSessionId = playResult.session_id;

            document.getElementById('progress-fill').style.width = '100%';

            // Mostrar éxito
            setTimeout(() => {
                this.showMemorialStep(3);
            }, 500);

        } catch (error) {
            console.error('Error generando avatar:', error);
            alert('Error al generar el avatar. Intenta de nuevo.');
            this.showMemorialStep(1);
        }
    }

    async pollJobStatus(jobId) {
        const maxAttempts = 60;
        let attempts = 0;

        while (attempts < maxAttempts) {
            try {
                const status = await api.getJobStatus(jobId);
                document.getElementById('processing-status').textContent = status.step || 'Procesando...';
                document.getElementById('progress-fill').style.width = `${20 + (status.progress || 0) * 0.7}%`;

                if (status.status === 'completed') {
                    return status;
                }
                if (status.status === 'error') {
                    throw new Error(status.error || 'Error de procesamiento');
                }
            } catch (e) {
                console.error('Error polling:', e);
            }

            await new Promise(r => setTimeout(r, 1000));
            attempts++;
        }

        throw new Error('Timeout esperando procesamiento');
    }

    async takeSelfie() {
        try {
            // Mostrar contenedor de cámara
            document.getElementById('camera-preview-container').classList.remove('hidden');
            document.getElementById('selfie-preview').classList.add('hidden');

            // Solicitar acceso a cámara frontal
            this.selfieStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }
            });

            // Mostrar preview en vivo
            const videoEl = document.getElementById('selfie-video');
            videoEl.srcObject = this.selfieStream;

        } catch (e) {
            console.error('Error accediendo a la cámara:', e);
            alert('No se pudo acceder a la cámara. Verifica los permisos.');
            document.getElementById('camera-preview-container').classList.add('hidden');
        }
    }

    capturePhoto() {
        const videoEl = document.getElementById('selfie-video');
        const canvas = document.getElementById('selfie-canvas');
        const ctx = canvas.getContext('2d');

        // Validar que el video tenga dimensiones
        if (!videoEl.videoWidth || !videoEl.videoHeight) {
            alert('Espera a que la cámara esté lista');
            return;
        }

        // Ajustar canvas al tamaño del video
        canvas.width = videoEl.videoWidth;
        canvas.height = videoEl.videoHeight;

        // Capturar frame actual
        ctx.drawImage(videoEl, 0, 0);

        // Convertir a URL para mostrar
        const imageDataUrl = canvas.toDataURL('image/jpeg', 0.9);

        // Mostrar foto capturada
        document.getElementById('selfie-img').src = imageDataUrl;
        document.getElementById('camera-preview-container').classList.add('hidden');
        document.getElementById('selfie-preview').classList.remove('hidden');

        // Detener stream de cámara
        if (this.selfieStream) {
            this.selfieStream.getTracks().forEach(t => t.stop());
            this.selfieStream = null;
        }

        // Guardar el blob para subir al backend
        canvas.toBlob((blob) => {
            this.capturedSelfieBlob = blob;
        }, 'image/jpeg', 0.9);
    }

    cancelCamera() {
        if (this.selfieStream) {
            this.selfieStream.getTracks().forEach(t => t.stop());
            this.selfieStream = null;
        }
        document.getElementById('camera-preview-container').classList.add('hidden');
    }

    async saveSelfie() {
        if (!this.capturedSelfieBlob || !this.currentSessionId) {
            alert('No hay foto para guardar o sesión no válida');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('photo', this.capturedSelfieBlob, 'selfie.jpg');

            const response = await fetch(
                `${api.baseUrl}/api/v1/memorial/sessions/${this.currentSessionId}/capture-photo`,
                { method: 'POST', body: formData }
            );

            if (response.ok) {
                const result = await response.json();
                console.log('Foto guardada:', result.photo_url);
                alert('Foto guardada exitosamente!');
            } else {
                throw new Error('Error al guardar');
            }
        } catch (e) {
            console.error('Error guardando foto:', e);
            alert('No se pudo guardar la foto.');
        }
    }

    async replayAvatar() {
        if (this.currentAvatarId) {
            await api.playMemorialAvatar(this.currentAvatarId);
        }
    }

    // ==========================================
    // RECEPTIONIST MODE
    // ==========================================

    setupReceptionistListeners() {
        const micBtn = document.getElementById('mic-button');
        const sendBtn = document.getElementById('send-button');
        const textInput = document.getElementById('text-input');

        // Mantener presionado para grabar
        micBtn.addEventListener('mousedown', () => this.startRecording());
        micBtn.addEventListener('mouseup', () => this.stopRecording());
        micBtn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.startRecording();
        });
        micBtn.addEventListener('touchend', () => this.stopRecording());

        // Enviar texto
        sendBtn.addEventListener('click', () => {
            this.sendTextMessage();
        });

        textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendTextMessage();
            }
        });
    }

    async initReceptionistMode() {
        // Obtener avatar de recepcionista
        try {
            const avatars = await api.getAvatars('receptionist');
            if (avatars.length > 0) {
                await api.startReceptionist(avatars[0].id);
            }
        } catch (e) {
            console.error('Error iniciando recepcionista:', e);
        }

        // Limpiar chat
        const messagesEl = document.getElementById('chat-messages');
        messagesEl.innerHTML = `
            <div class="message assistant">
                <p>¡Hola! Soy tu asistente virtual. ¿En qué puedo ayudarte?</p>
            </div>
        `;
    }

    async startRecording() {
        if (this.isRecording) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (e) => {
                this.audioChunks.push(e.data);
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                await this.sendAudioMessage(audioBlob);
                stream.getTracks().forEach(t => t.stop());
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            document.getElementById('mic-button').classList.add('recording');

        } catch (e) {
            console.error('Error accediendo al micrófono:', e);
            alert('No se pudo acceder al micrófono');
        }
    }

    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;

        this.mediaRecorder.stop();
        this.isRecording = false;
        document.getElementById('mic-button').classList.remove('recording');
    }

    async sendTextMessage() {
        const input = document.getElementById('text-input');
        const text = input.value.trim();
        if (!text) return;

        input.value = '';
        this.addMessage(text, 'user');

        try {
            const response = await api.sendMessage(text);
            this.addMessage(response.response_text, 'assistant');
        } catch (e) {
            this.addMessage('Lo siento, ocurrió un error.', 'assistant');
        }
    }

    async sendAudioMessage(audioBlob) {
        this.addMessage('🎤 [Audio]', 'user');

        try {
            const response = await api.sendAudio(audioBlob);
            this.addMessage(response.response_text, 'assistant');
        } catch (e) {
            this.addMessage('Lo siento, no pude procesar el audio.', 'assistant');
        }
    }

    addMessage(text, role) {
        const messagesEl = document.getElementById('chat-messages');
        const msgEl = document.createElement('div');
        msgEl.className = `message ${role}`;
        msgEl.innerHTML = `<p>${text}</p>`;
        messagesEl.appendChild(msgEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    // ==========================================
    // MENU MODE
    // ==========================================

    setupMenuListeners() {
        document.getElementById('close-detail').addEventListener('click', () => {
            document.getElementById('item-detail').classList.add('hidden');
        });

        document.getElementById('show-in-hologram').addEventListener('click', () => {
            this.showItemInHologram();
        });

        document.getElementById('play-video').addEventListener('click', () => {
            this.playItemVideo();
        });
    }

    async initMenuMode() {
        try {
            // Cargar categorías
            const categories = await api.getMenuCategories();
            this.renderMenuCategories(categories);

            // Cargar items destacados
            const items = await api.getMenuItems(null, true);
            this.renderMenuItems(items);
        } catch (e) {
            console.error('Error cargando menú:', e);
        }
    }

    renderMenuCategories(categories) {
        const container = document.getElementById('categories-bar');
        container.innerHTML = `
            <button class="category-chip active" data-category="">Todos</button>
            ${categories.map(cat => `
                <button class="category-chip" data-category="${cat.id}">${cat.name}</button>
            `).join('')}
        `;

        container.querySelectorAll('.category-chip').forEach(chip => {
            chip.addEventListener('click', async () => {
                container.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                const items = await api.getMenuItems(chip.dataset.category || null);
                this.renderMenuItems(items);
            });
        });
    }

    renderMenuItems(items) {
        const container = document.getElementById('menu-items');
        container.innerHTML = items.map(item => `
            <div class="menu-item-card" data-id="${item.id}">
                <img src="${item.image_url || 'assets/placeholder-food.jpg'}" alt="${item.name}">
                <div class="item-info">
                    <h3>${item.name}</h3>
                    <div class="price">$${item.price.toFixed(2)}</div>
                </div>
            </div>
        `).join('');

        container.querySelectorAll('.menu-item-card').forEach(card => {
            card.addEventListener('click', () => {
                this.showItemDetail(card.dataset.id);
            });
        });
    }

    async showItemDetail(itemId) {
        try {
            const item = await api.getMenuItem(itemId);
            this.currentMenuItem = item;

            document.getElementById('detail-image').src = item.image_url || 'assets/placeholder-food.jpg';
            document.getElementById('detail-name').textContent = item.name;
            document.getElementById('detail-description').textContent = item.description || '';
            document.getElementById('detail-price').textContent = `$${item.price.toFixed(2)} ${item.currency}`;

            document.getElementById('play-video').style.display = item.video_url ? 'block' : 'none';
            document.getElementById('item-detail').classList.remove('hidden');
        } catch (e) {
            console.error('Error cargando detalle:', e);
        }
    }

    async showItemInHologram() {
        if (this.currentMenuItem) {
            try {
                await api.showMenuItem(this.currentMenuItem.id, false, true);
            } catch (e) {
                console.error('Error mostrando en holograma:', e);
            }
        }
    }

    async playItemVideo() {
        if (this.currentMenuItem) {
            try {
                await api.showMenuItem(this.currentMenuItem.id, true, false);
            } catch (e) {
                console.error('Error reproduciendo video:', e);
            }
        }
    }

    // ==========================================
    // CATALOG MODE
    // ==========================================

    setupCatalogListeners() {
        const searchInput = document.getElementById('product-search');
        let searchTimeout;

        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.searchProducts(searchInput.value);
            }, 300);
        });

        document.getElementById('close-product-detail').addEventListener('click', () => {
            document.getElementById('product-detail').classList.add('hidden');
        });

        document.getElementById('show-product-hologram').addEventListener('click', () => {
            this.showProductInHologram();
        });
    }

    async initCatalogMode() {
        try {
            // Cargar categorías
            const categories = await api.getCatalogCategories();
            this.renderCatalogFilters(categories);

            // Cargar productos
            const products = await api.searchProducts();
            this.renderProducts(products);
        } catch (e) {
            console.error('Error cargando catálogo:', e);
        }
    }

    renderCatalogFilters(categories) {
        const container = document.getElementById('filter-bar');
        container.innerHTML = `
            <button class="filter-chip active" data-filter="">Todos</button>
            ${categories.map(cat => `
                <button class="filter-chip" data-filter="${cat.id}">${cat.name}</button>
            `).join('')}
        `;

        container.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', async () => {
                container.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                const products = await api.searchProducts('', chip.dataset.filter || null);
                this.renderProducts(products);
            });
        });
    }

    renderProducts(products) {
        const container = document.getElementById('products-grid');
        container.innerHTML = products.map(product => `
            <div class="product-card" data-id="${product.id}">
                <img src="${(product.images && product.images[0]) || 'assets/placeholder-product.jpg'}" alt="${product.name}">
                <div class="product-info">
                    <h3>${product.name}</h3>
                    <div class="price">$${product.price.toFixed(2)}</div>
                </div>
            </div>
        `).join('');

        container.querySelectorAll('.product-card').forEach(card => {
            card.addEventListener('click', () => {
                this.showProductDetail(card.dataset.id);
            });
        });
    }

    async searchProducts(query) {
        try {
            const products = await api.searchProducts(query);
            this.renderProducts(products);
        } catch (e) {
            console.error('Error buscando productos:', e);
        }
    }

    async showProductDetail(productId) {
        try {
            const product = await api.getProduct(productId);
            this.currentProduct = product;

            // Renderizar imágenes
            const imagesContainer = document.getElementById('product-images');
            imagesContainer.innerHTML = product.images?.map(img => `
                <img src="${img}" alt="${product.name}">
            `).join('') || '<img src="assets/placeholder-product.jpg">';

            document.getElementById('product-name').textContent = product.name;
            document.getElementById('product-description').textContent = product.description || '';
            document.getElementById('product-price').textContent = `$${product.price.toFixed(2)} ${product.currency}`;

            // Tallas
            const sizesContainer = document.getElementById('size-buttons');
            sizesContainer.innerHTML = product.sizes?.map(size => `
                <button class="size-btn" data-size="${size}">${size}</button>
            `).join('') || '<span>Talla única</span>';

            sizesContainer.querySelectorAll('.size-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    sizesContainer.querySelectorAll('.size-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.selectedSize = btn.dataset.size;
                    this.updateStockStatus();
                });
            });

            // Colores
            const colorsContainer = document.getElementById('color-buttons');
            colorsContainer.innerHTML = product.colors?.map(color => `
                <button class="color-btn" data-color="${color}">${color}</button>
            `).join('') || '';

            colorsContainer.querySelectorAll('.color-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    colorsContainer.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.selectedColor = btn.dataset.color;
                    this.updateStockStatus();
                });
            });

            document.getElementById('product-detail').classList.remove('hidden');
        } catch (e) {
            console.error('Error cargando producto:', e);
        }
    }

    async updateStockStatus() {
        if (!this.currentProduct) return;

        const statusEl = document.getElementById('stock-status');
        try {
            // TODO: Obtener location_id real
            const locationId = '00000000-0000-0000-0000-000000000001';
            const availability = await api.checkProductAvailability(
                this.currentProduct.id,
                locationId,
                this.selectedSize,
                this.selectedColor
            );

            if (availability.quantity > 5) {
                statusEl.className = 'stock-status in-stock';
                statusEl.textContent = `✓ Disponible (${availability.quantity} unidades)`;
            } else if (availability.quantity > 0) {
                statusEl.className = 'stock-status low-stock';
                statusEl.textContent = `⚠ Últimas ${availability.quantity} unidades`;
            } else {
                statusEl.className = 'stock-status out-of-stock';
                statusEl.textContent = '✗ Agotado';
            }
        } catch (e) {
            statusEl.className = 'stock-status';
            statusEl.textContent = 'Verificando disponibilidad...';
        }
    }

    async showProductInHologram() {
        if (this.currentProduct) {
            try {
                await api.showProduct(this.currentProduct.id, 0, true);
            } catch (e) {
                console.error('Error mostrando en holograma:', e);
            }
        }
    }

    // ==========================================
    // VIDEOCALL MODE
    // ==========================================

    setupVideocallListeners() {
        document.getElementById('start-call').addEventListener('click', () => {
            this.startVideocall();
        });

        document.getElementById('end-call').addEventListener('click', () => {
            this.endVideocall();
        });

        document.getElementById('toggle-mic').addEventListener('click', (e) => {
            e.target.classList.toggle('muted');
        });

        document.getElementById('toggle-camera').addEventListener('click', (e) => {
            e.target.classList.toggle('camera-off');
        });
    }

    initVideocallMode() {
        this.showVideocallState('idle');
        document.getElementById('caller-id').value = '';
    }

    showVideocallState(state) {
        document.querySelectorAll('.videocall-state').forEach(s => s.classList.remove('active'));
        document.getElementById(`videocall-${state}`).classList.add('active');
    }

    async startVideocall() {
        const callerId = document.getElementById('caller-id').value.trim() || 'Usuario';

        this.showVideocallState('connecting');

        try {
            // Obtener video local
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            document.getElementById('local-video').srcObject = stream;
            this.localStream = stream;

            // Iniciar llamada (esto abre el WebSocket)
            await api.startVideocall(callerId);

            this.showVideocallState('active');
            this.startCallTimer();

            // Iniciar captura y envío de frames
            this.startFrameCapture();

        } catch (e) {
            console.error('Error iniciando videollamada:', e);
            alert('No se pudo iniciar la videollamada');
            this.showVideocallState('idle');
        }
    }

    startFrameCapture() {
        // Crear canvas para capturar frames
        this.frameCanvas = document.createElement('canvas');
        this.frameCanvas.width = 256;
        this.frameCanvas.height = 256;
        this.frameCtx = this.frameCanvas.getContext('2d');

        const videoEl = document.getElementById('local-video');

        // Capturar y enviar frames cada 100ms (10 FPS)
        this.frameInterval = setInterval(() => {
            if (api.streamSocket && api.streamSocket.readyState === WebSocket.OPEN && videoEl.readyState >= 2) {
                // Dibujar frame del video al canvas (redimensionado a 256x256)
                this.frameCtx.drawImage(videoEl, 0, 0, 256, 256);

                // Convertir a JPEG blob y enviar
                this.frameCanvas.toBlob((blob) => {
                    if (blob) {
                        api.sendFrame(blob);
                    }
                }, 'image/jpeg', 0.7);
            }
        }, 100);
    }

    stopFrameCapture() {
        if (this.frameInterval) {
            clearInterval(this.frameInterval);
            this.frameInterval = null;
        }
        this.frameCanvas = null;
        this.frameCtx = null;
    }

    startCallTimer() {
        this.callStartTime = Date.now();
        this.callTimerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.callStartTime) / 1000);
            const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
            const secs = (elapsed % 60).toString().padStart(2, '0');
            document.getElementById('call-duration').textContent = `${mins}:${secs}`;
        }, 1000);
    }

    async endVideocall() {
        // Detener captura de frames
        this.stopFrameCapture();

        clearInterval(this.callTimerInterval);

        if (this.localStream) {
            this.localStream.getTracks().forEach(t => t.stop());
            this.localStream = null;
        }

        await api.endVideocall();
        this.showVideocallState('idle');
    }

    // ==========================================
    // SETTINGS
    // ==========================================

    loadSettings() {
        const saved = localStorage.getItem('holographic-settings');
        return saved ? JSON.parse(saved) : {
            apiUrl: 'http://localhost:8000',
            deviceIp: '192.168.4.1',
            language: 'es'
        };
    }

    showSettings() {
        document.getElementById('api-url').value = this.settings.apiUrl;
        document.getElementById('device-ip').value = this.settings.deviceIp;
        document.getElementById('language').value = this.settings.language;
        document.getElementById('settings-modal').classList.remove('hidden');
    }

    hideSettings() {
        document.getElementById('settings-modal').classList.add('hidden');
    }

    saveSettings() {
        this.settings.apiUrl = document.getElementById('api-url').value;
        this.settings.deviceIp = document.getElementById('device-ip').value;
        this.settings.language = document.getElementById('language').value;

        localStorage.setItem('holographic-settings', JSON.stringify(this.settings));
        api.setBaseUrl(this.settings.apiUrl);

        this.hideSettings();
        this.checkConnection();
    }
}

// Inicializar app cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    window.app = new KioskApp();
});
