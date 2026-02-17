"""
Router para Modo 4: Catálogo de Tienda
Asistente virtual para tiendas de ropa y productos
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import List, Optional
import logging

from ..db.database import get_db
from ..models import (
    CatalogCategory, Product, ProductAvailability, ShowProductRequest,
    ConversationInput, ConversationResponse
)
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/categories", response_model=List[CatalogCategory])
async def list_categories(
    location_id: Optional[UUID] = None,
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Listar categorías de productos"""
    query = "SELECT * FROM catalog.categories WHERE is_active = true"
    params = {}

    if location_id:
        query += " AND location_id = :location_id"
        params["location_id"] = str(location_id)

    if parent_id:
        query += " AND parent_id = :parent_id"
        params["parent_id"] = str(parent_id)
    else:
        query += " AND parent_id IS NULL"

    query += " ORDER BY display_order"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        CatalogCategory(
            id=row.id,
            name=row.name,
            description=row.description,
            image_url=row.image_url,
            parent_id=row.parent_id
        )
        for row in rows
    ]


@router.get("/products", response_model=List[Product])
async def search_products(
    query: Optional[str] = None,
    category_id: Optional[UUID] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    size: Optional[str] = None,
    color: Optional[str] = None,
    in_stock: bool = True,
    location_id: Optional[UUID] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Buscar productos con filtros"""
    sql = "SELECT DISTINCT p.* FROM catalog.products p"
    params = {}

    # Join con inventario si se filtra por stock o ubicación
    if in_stock or location_id:
        sql += " LEFT JOIN catalog.inventory i ON p.id = i.product_id"

    sql += " WHERE p.is_available = true"

    if query:
        sql += " AND (p.name ILIKE :query OR p.description ILIKE :query OR p.sku ILIKE :query)"
        params["query"] = f"%{query}%"

    if category_id:
        sql += " AND p.category_id = :category_id"
        params["category_id"] = str(category_id)

    if min_price:
        sql += " AND p.price >= :min_price"
        params["min_price"] = min_price

    if max_price:
        sql += " AND p.price <= :max_price"
        params["max_price"] = max_price

    if size:
        sql += " AND :size = ANY(p.sizes)"
        params["size"] = size

    if color:
        sql += " AND :color = ANY(p.colors)"
        params["color"] = color

    if in_stock and location_id:
        sql += " AND i.location_id = :location_id AND i.quantity > 0"
        params["location_id"] = str(location_id)
    elif in_stock:
        sql += " AND EXISTS (SELECT 1 FROM catalog.inventory WHERE product_id = p.id AND quantity > 0)"

    sql += f" ORDER BY p.name LIMIT {limit} OFFSET {offset}"

    result = await db.execute(text(sql), params)
    rows = result.fetchall()

    return [
        Product(
            id=row.id,
            category_id=row.category_id,
            sku=row.sku,
            name=row.name,
            description=row.description,
            price=float(row.price),
            currency=row.currency,
            images=row.images or [],
            sizes=row.sizes or [],
            colors=row.colors or [],
            is_available=row.is_available
        )
        for row in rows
    ]


@router.get("/products/{product_id}", response_model=Product)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Obtener detalle de producto"""
    result = await db.execute(
        text("SELECT * FROM catalog.products WHERE id = :product_id"),
        {"product_id": str(product_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    return Product(
        id=row.id,
        category_id=row.category_id,
        sku=row.sku,
        name=row.name,
        description=row.description,
        price=float(row.price),
        currency=row.currency,
        images=row.images or [],
        sizes=row.sizes or [],
        colors=row.colors or [],
        is_available=row.is_available
    )


@router.get("/products/{product_id}/availability", response_model=ProductAvailability)
async def check_availability(
    product_id: UUID,
    location_id: UUID,
    size: Optional[str] = None,
    color: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Verificar disponibilidad de producto"""
    query = """
        SELECT COALESCE(SUM(quantity), 0) as total_quantity
        FROM catalog.inventory
        WHERE product_id = :product_id AND location_id = :location_id
    """
    params = {
        "product_id": str(product_id),
        "location_id": str(location_id)
    }

    if size:
        query = query.replace("WHERE", "WHERE size = :size AND")
        params["size"] = size

    if color:
        query = query.replace("WHERE", "WHERE color = :color AND")
        params["color"] = color

    result = await db.execute(text(query), params)
    row = result.fetchone()

    quantity = int(row.total_quantity) if row else 0

    return ProductAvailability(
        product_id=product_id,
        location_id=location_id,
        size=size,
        color=color,
        quantity=quantity,
        is_available=quantity > 0
    )


@router.post("/show-product/{product_id}")
async def show_product_on_hologram(
    product_id: UUID,
    request: ShowProductRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mostrar producto en el holograma.

    Puede mostrar:
    - Imagen del producto (con rotación)
    - Múltiples ángulos
    - Narración del avatar describiendo el producto
    """
    # Obtener producto
    result = await db.execute(
        text("SELECT * FROM catalog.products WHERE id = :product_id"),
        {"product_id": str(product_id)}
    )
    product = result.fetchone()

    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Verificar dispositivo
    result = await db.execute(
        text("SELECT * FROM core.devices WHERE id = :device_id"),
        {"device_id": str(request.device_id)}
    )
    device = result.fetchone()

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Seleccionar imagen
    images = product.images or []
    image_url = images[request.image_index] if request.image_index < len(images) else (images[0] if images else None)

    content_to_show = {
        "type": "product",
        "product_id": str(product_id),
        "name": product.name,
        "price": f"${product.price:.2f} {product.currency}",
        "image_url": image_url,
        "rotate": request.rotate,
        "display_type": "image_rotation" if request.rotate else "image"
    }

    # Preparar narración
    narration_text = f"Te presento {product.name}."
    if product.description:
        narration_text += f" {product.description}"
    narration_text += f" Precio: {product.price:.0f} pesos."

    if product.sizes:
        narration_text += f" Disponible en tallas: {', '.join(product.sizes)}."
    if product.colors:
        narration_text += f" Colores disponibles: {', '.join(product.colors)}."

    content_to_show["narration_text"] = narration_text

    # TODO: Enviar al Frame Processor y Fan Driver

    return {
        "status": "displaying",
        "device_id": str(request.device_id),
        "content": content_to_show
    }


@router.post("/conversation")
async def catalog_conversation(
    input_data: ConversationInput,
    db: AsyncSession = Depends(get_db)
):
    """
    Conversación contextual sobre productos.

    El avatar puede:
    - Buscar productos por nombre o característica
    - Recomendar productos similares
    - Informar sobre tallas y colores
    - Verificar disponibilidad
    """
    # TODO: Implementar conversación con contexto de catálogo

    return ConversationResponse(
        response_text="¿Buscas algo en particular? Puedo ayudarte a encontrar ropa por estilo, color o talla.",
        audio_url=None,
        video_url=None,
        intent="product_search",
        entities={}
    )


# ============================================
# CRUD para admin
# ============================================

@router.post("/categories")
async def create_category(
    name: str,
    location_id: UUID,
    description: Optional[str] = None,
    image_url: Optional[str] = None,
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Crear categoría (admin)"""
    result = await db.execute(
        text("""
            INSERT INTO catalog.categories (location_id, name, description, image_url, parent_id)
            VALUES (:location_id, :name, :description, :image_url, :parent_id)
            RETURNING *
        """),
        {
            "location_id": str(location_id),
            "name": name,
            "description": description,
            "image_url": image_url,
            "parent_id": str(parent_id) if parent_id else None
        }
    )
    await db.commit()
    row = result.fetchone()

    return CatalogCategory(
        id=row.id,
        name=row.name,
        description=row.description,
        image_url=row.image_url,
        parent_id=row.parent_id
    )


@router.post("/products")
async def create_product(
    category_id: UUID,
    name: str,
    price: float,
    sku: Optional[str] = None,
    description: Optional[str] = None,
    images: Optional[List[str]] = None,
    sizes: Optional[List[str]] = None,
    colors: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db)
):
    """Crear producto (admin)"""
    result = await db.execute(
        text("""
            INSERT INTO catalog.products (
                category_id, sku, name, description, price, images, sizes, colors
            )
            VALUES (
                :category_id, :sku, :name, :description, :price, :images, :sizes, :colors
            )
            RETURNING *
        """),
        {
            "category_id": str(category_id),
            "sku": sku,
            "name": name,
            "description": description,
            "price": price,
            "images": images,
            "sizes": sizes,
            "colors": colors
        }
    )
    await db.commit()
    row = result.fetchone()

    return Product(
        id=row.id,
        category_id=row.category_id,
        sku=row.sku,
        name=row.name,
        description=row.description,
        price=float(row.price),
        currency=row.currency,
        images=row.images or [],
        sizes=row.sizes or [],
        colors=row.colors or [],
        is_available=row.is_available
    )


@router.put("/inventory")
async def update_inventory(
    product_id: UUID,
    location_id: UUID,
    quantity: int,
    size: Optional[str] = None,
    color: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Actualizar inventario (admin)"""
    result = await db.execute(
        text("""
            INSERT INTO catalog.inventory (product_id, location_id, size, color, quantity)
            VALUES (:product_id, :location_id, :size, :color, :quantity)
            ON CONFLICT (product_id, location_id, size, color)
            DO UPDATE SET quantity = :quantity, updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """),
        {
            "product_id": str(product_id),
            "location_id": str(location_id),
            "size": size,
            "color": color,
            "quantity": quantity
        }
    )
    await db.commit()
    row = result.fetchone()

    return {
        "product_id": str(product_id),
        "location_id": str(location_id),
        "size": size,
        "color": color,
        "quantity": quantity,
        "updated_at": str(row.updated_at)
    }
