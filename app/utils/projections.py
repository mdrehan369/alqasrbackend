from app.db.models.product import Product

ALLOWED_PRODUCT_FIELDS = {
    "id": Product.id,
    "title": Product.title,
    "ingredients": Product.ingredients,
    "details": Product.details,
    "is_active": Product.is_active,
    "created_at": Product.created_at,
    "product": Product,
}

DEFAULT_PRODUCT_FIELDS = [Product.id, Product.title]
