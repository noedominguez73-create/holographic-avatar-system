-- =====================================================
-- HOLOGRAPHIC AVATAR SYSTEM - DATABASE SCHEMA
-- =====================================================

-- Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Para búsqueda fuzzy

-- =====================================================
-- ESQUEMA: core
-- =====================================================
CREATE SCHEMA IF NOT EXISTS core;

-- Ubicaciones (restaurantes, tiendas, etc.)
CREATE TABLE core.locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'America/Mexico_City',
    is_active BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Dispositivos (ventiladores holográficos)
CREATE TABLE core.devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_id UUID REFERENCES core.locations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(50) DEFAULT 'led_fan_224',
    ip_address INET NOT NULL,
    tcp_port INTEGER DEFAULT 5499,
    http_port INTEGER DEFAULT 80,
    protocol_type VARCHAR(20) DEFAULT 'tcp',
    resolution_diameter INTEGER DEFAULT 224,
    status VARCHAR(20) DEFAULT 'offline',
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    config JSONB DEFAULT '{"fps": 10, "rays": 2700}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Usuarios administradores
CREATE TABLE core.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'operator',
    location_id UUID REFERENCES core.locations(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ESQUEMA: content
-- =====================================================
CREATE SCHEMA IF NOT EXISTS content;

-- Avatares (imágenes base para animación)
CREATE TABLE content.avatars (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_url VARCHAR(512) NOT NULL,
    thumbnail_url VARCHAR(512),
    avatar_type VARCHAR(50) DEFAULT 'custom',
    voice_profile_id UUID,
    animation_preset VARCHAR(50) DEFAULT 'natural',
    background_color VARCHAR(7) DEFAULT '#000000',
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES core.users(id)
);

-- Videos pre-generados
CREATE TABLE content.animated_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    avatar_id UUID REFERENCES content.avatars(id) ON DELETE CASCADE,
    video_url VARCHAR(512) NOT NULL,
    bin_file_url VARCHAR(512),
    duration_seconds DECIMAL(5,2),
    frame_count INTEGER,
    animation_type VARCHAR(50),
    driving_source VARCHAR(50),
    status VARCHAR(20) DEFAULT 'processing',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sesiones memorial
CREATE TABLE content.memorial_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_id UUID REFERENCES core.locations(id),
    device_id UUID REFERENCES core.devices(id),
    avatar_id UUID REFERENCES content.avatars(id),
    user_email VARCHAR(255),
    user_phone VARCHAR(20),
    photo_taken_url VARCHAR(512),
    session_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- =====================================================
-- ESQUEMA: menu
-- =====================================================
CREATE SCHEMA IF NOT EXISTS menu;

-- Categorías de menú
CREATE TABLE menu.categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_id UUID REFERENCES core.locations(id),
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    description TEXT,
    image_url VARCHAR(512),
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

-- Items del menú
CREATE TABLE menu.items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID REFERENCES menu.categories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    description TEXT,
    description_en TEXT,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'MXN',
    image_url VARCHAR(512),
    video_url VARCHAR(512),
    ingredients TEXT[],
    allergens TEXT[],
    nutritional_info JSONB,
    preparation_time_minutes INTEGER,
    is_available BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Respuestas del avatar para menú
CREATE TABLE menu.avatar_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_id UUID REFERENCES core.locations(id),
    trigger_type VARCHAR(50),
    trigger_value VARCHAR(255),
    response_text TEXT NOT NULL,
    response_text_en TEXT,
    audio_url VARCHAR(512),
    animation_preset VARCHAR(50)
);

-- =====================================================
-- ESQUEMA: catalog
-- =====================================================
CREATE SCHEMA IF NOT EXISTS catalog;

-- Categorías de productos
CREATE TABLE catalog.categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_id UUID REFERENCES core.locations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_url VARCHAR(512),
    parent_id UUID REFERENCES catalog.categories(id),
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);

-- Productos
CREATE TABLE catalog.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID REFERENCES catalog.categories(id) ON DELETE CASCADE,
    sku VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'MXN',
    images TEXT[],
    sizes TEXT[],
    colors TEXT[],
    brand VARCHAR(100),
    is_available BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Inventario por ubicación
CREATE TABLE catalog.inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES catalog.products(id) ON DELETE CASCADE,
    location_id UUID REFERENCES core.locations(id),
    size VARCHAR(50),
    color VARCHAR(50),
    quantity INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, location_id, size, color)
);

-- =====================================================
-- ESQUEMA: conversations
-- =====================================================
CREATE SCHEMA IF NOT EXISTS conversations;

-- Sesiones de conversación
CREATE TABLE conversations.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_id UUID REFERENCES core.locations(id),
    device_id UUID REFERENCES core.devices(id),
    mode VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- Mensajes
CREATE TABLE conversations.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES conversations.sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    audio_url VARCHAR(512),
    intent_detected VARCHAR(100),
    entities JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ÍNDICES
-- =====================================================
CREATE INDEX idx_devices_location ON core.devices(location_id);
CREATE INDEX idx_devices_status ON core.devices(status);
CREATE INDEX idx_avatars_type ON content.avatars(avatar_type);
CREATE INDEX idx_menu_items_category ON menu.items(category_id);
CREATE INDEX idx_menu_items_name_trgm ON menu.items USING gin(name gin_trgm_ops);
CREATE INDEX idx_products_category ON catalog.products(category_id);
CREATE INDEX idx_products_name_trgm ON catalog.products USING gin(name gin_trgm_ops);
CREATE INDEX idx_inventory_product ON catalog.inventory(product_id);
CREATE INDEX idx_inventory_location ON catalog.inventory(location_id);
CREATE INDEX idx_sessions_location ON conversations.sessions(location_id);
CREATE INDEX idx_sessions_mode ON conversations.sessions(mode);
CREATE INDEX idx_messages_session ON conversations.messages(session_id);

-- =====================================================
-- TRIGGER para updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_locations_updated_at
    BEFORE UPDATE ON core.locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_devices_updated_at
    BEFORE UPDATE ON core.devices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_updated_at
    BEFORE UPDATE ON catalog.inventory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- DATOS INICIALES
-- =====================================================
INSERT INTO core.locations (name, address, city) VALUES
('Demo Location', 'Av. Principal 123', 'Ciudad de México');

INSERT INTO content.avatars (name, avatar_type, image_url, description) VALUES
('Asistente Virtual', 'receptionist', '/defaults/assistant.png', 'Avatar de recepcionista predeterminado'),
('Mesero Virtual', 'menu', '/defaults/waiter.png', 'Avatar para menú interactivo'),
('Vendedor Virtual', 'catalog', '/defaults/sales.png', 'Avatar para catálogo de tienda');
