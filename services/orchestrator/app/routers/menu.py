"""
Router para Modo 3: Menú Interactivo
Presenta el menú del restaurante de forma interactiva
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from uuid import UUID
from typing import List, Optional
import logging

from ..db.database import get_db
from ..models import (
    MenuCategory, MenuItem, MenuRecommendRequest, ShowItemRequest,
    ConversationInput, ConversationResponse
)
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/categories", response_model=List[MenuCategory])
async def list_categories(
    location_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Listar categorías del menú"""
    query = """
        SELECT c.*, COUNT(i.id) as items_count
        FROM menu.categories c
        LEFT JOIN menu.items i ON c.id = i.category_id AND i.is_available = true
        WHERE c.is_active = true
    """
    params = {}

    if location_id:
        query += " AND c.location_id = :location_id"
        params["location_id"] = str(location_id)

    query += " GROUP BY c.id ORDER BY c.display_order"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        MenuCategory(
            id=row.id,
            name=row.name,
            description=row.description,
            image_url=row.image_url,
            items_count=row.items_count or 0
        )
        for row in rows
    ]


@router.get("/items", response_model=List[MenuItem])
async def list_items(
    category_id: Optional[UUID] = None,
    featured_only: bool = False,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Listar items del menú"""
    query = "SELECT * FROM menu.items WHERE is_available = true"
    params = {}

    if category_id:
        query += " AND category_id = :category_id"
        params["category_id"] = str(category_id)

    if featured_only:
        query += " AND is_featured = true"

    if search:
        query += " AND (name ILIKE :search OR description ILIKE :search)"
        params["search"] = f"%{search}%"

    query += " ORDER BY display_order"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return [
        MenuItem(
            id=row.id,
            category_id=row.category_id,
            name=row.name,
            description=row.description,
            price=float(row.price),
            currency=row.currency,
            image_url=row.image_url,
            video_url=row.video_url,
            ingredients=row.ingredients,
            is_available=row.is_available,
            is_featured=row.is_featured
        )
        for row in rows
    ]


@router.get("/items/{item_id}", response_model=MenuItem)
async def get_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Obtener detalle de un item"""
    result = await db.execute(
        text("SELECT * FROM menu.items WHERE id = :item_id"),
        {"item_id": str(item_id)}
    )
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    return MenuItem(
        id=row.id,
        category_id=row.category_id,
        name=row.name,
        description=row.description,
        price=float(row.price),
        currency=row.currency,
        image_url=row.image_url,
        video_url=row.video_url,
        ingredients=row.ingredients,
        is_available=row.is_available,
        is_featured=row.is_featured
    )


@router.post("/recommend")
async def get_recommendations(
    request: MenuRecommendRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtener recomendaciones basadas en preferencias.

    Usa el LLM para sugerir platillos basados en:
    - Preferencias del usuario
    - Restricciones alimenticias
    - Presupuesto máximo
    """
    # Obtener todos los items disponibles
    query = "SELECT * FROM menu.items WHERE is_available = true"
    params = {}

    if request.budget_max:
        query += " AND price <= :budget_max"
        params["budget_max"] = request.budget_max

    result = await db.execute(text(query), params)
    items = result.fetchall()

    # Filtrar por restricciones
    filtered_items = []
    for item in items:
        allergens = item.allergens or []
        has_restriction = any(
            restriction.lower() in [a.lower() for a in allergens]
            for restriction in request.dietary_restrictions
        )
        if not has_restriction:
            filtered_items.append(item)

    # TODO: Usar LLM para ranking más inteligente

    # Por ahora, retornar items destacados o primeros 5
    recommended = [
        item for item in filtered_items if item.is_featured
    ][:5]

    if len(recommended) < 3:
        recommended = filtered_items[:5]

    return {
        "recommendations": [
            {
                "id": str(item.id),
                "name": item.name,
                "description": item.description,
                "price": float(item.price),
                "image_url": item.image_url,
                "reason": "Platillo destacado" if item.is_featured else "Recomendado para ti"
            }
            for item in recommended
        ],
        "total_options": len(filtered_items)
    }


@router.post("/show-item/{item_id}")
async def show_item_on_hologram(
    item_id: UUID,
    request: ShowItemRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mostrar item en el holograma.

    Puede mostrar:
    - Imagen del platillo
    - Video de preparación
    - Narración del avatar describiendo el platillo
    """
    # Obtener item
    result = await db.execute(
        text("SELECT * FROM menu.items WHERE id = :item_id"),
        {"item_id": str(item_id)}
    )
    item = result.fetchone()

    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")

    # Verificar dispositivo
    result = await db.execute(
        text("SELECT * FROM core.devices WHERE id = :device_id"),
        {"device_id": str(request.device_id)}
    )
    device = result.fetchone()

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Preparar contenido a mostrar
    content_to_show = {
        "type": "menu_item",
        "item_id": str(item_id),
        "name": item.name,
        "price": f"${item.price:.2f} {item.currency}"
    }

    if request.show_video and item.video_url:
        content_to_show["video_url"] = item.video_url
        content_to_show["display_type"] = "video"
    else:
        content_to_show["image_url"] = item.image_url
        content_to_show["display_type"] = "image"

    if request.narrate:
        # Preparar texto para narración
        narration_text = f"Te presento {item.name}. {item.description}"
        if item.price:
            narration_text += f" Su precio es {item.price:.0f} pesos."
        content_to_show["narration_text"] = narration_text

    # TODO: Enviar al Frame Processor y Fan Driver

    return {
        "status": "displaying",
        "device_id": str(request.device_id),
        "content": content_to_show
    }


@router.post("/conversation")
async def menu_conversation(
    input_data: ConversationInput,
    db: AsyncSession = Depends(get_db)
):
    """
    Conversación contextual sobre el menú.

    El avatar puede:
    - Describir categorías
    - Recomendar platillos
    - Responder sobre ingredientes
    - Explicar precios
    """
    # TODO: Implementar conversación con contexto de menú

    return ConversationResponse(
        response_text="¿Te gustaría ver nuestras opciones de entradas o platos fuertes?",
        audio_url=None,
        video_url=None,
        intent="menu_navigation",
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
    db: AsyncSession = Depends(get_db)
):
    """Crear nueva categoría (admin)"""
    result = await db.execute(
        text("""
            INSERT INTO menu.categories (location_id, name, description, image_url)
            VALUES (:location_id, :name, :description, :image_url)
            RETURNING *
        """),
        {
            "location_id": str(location_id),
            "name": name,
            "description": description,
            "image_url": image_url
        }
    )
    await db.commit()
    row = result.fetchone()

    return MenuCategory(
        id=row.id,
        name=row.name,
        description=row.description,
        image_url=row.image_url,
        items_count=0
    )


@router.post("/items")
async def create_item(
    category_id: UUID,
    name: str,
    price: float,
    description: Optional[str] = None,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    ingredients: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db)
):
    """Crear nuevo item de menú (admin)"""
    result = await db.execute(
        text("""
            INSERT INTO menu.items (
                category_id, name, description, price,
                image_url, video_url, ingredients
            )
            VALUES (
                :category_id, :name, :description, :price,
                :image_url, :video_url, :ingredients
            )
            RETURNING *
        """),
        {
            "category_id": str(category_id),
            "name": name,
            "description": description,
            "price": price,
            "image_url": image_url,
            "video_url": video_url,
            "ingredients": ingredients
        }
    )
    await db.commit()
    row = result.fetchone()

    return MenuItem(
        id=row.id,
        category_id=row.category_id,
        name=row.name,
        description=row.description,
        price=float(row.price),
        currency=row.currency,
        image_url=row.image_url,
        video_url=row.video_url,
        ingredients=row.ingredients,
        is_available=row.is_available,
        is_featured=row.is_featured
    )
