"""Seed the Al Qasr database with sample attar and perfume products.

Usage:
    uv run python scripts/seed.py
    uv run python scripts/seed.py --limit 15 --dry-run
    uv run python scripts/seed.py --images-dir ./seed_images

If ``--images-dir`` contains ``aatr/`` and/or ``perfume/`` sub-folders, the
image files inside them are uploaded. Otherwise distinct placeholder PNGs are
generated so the script works without any bundled assets.
"""

import argparse
import asyncio
import colorsys
import struct
import sys
import zlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import UploadFile  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.db.models.product import Category, ProductType, SizeUnit  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.repo.image import delete_image_repo  # noqa: E402
from app.repo.product import get_product_by_title_repo  # noqa: E402
from app.schemas.category import CreateCategoryRequest  # noqa: E402
from app.schemas.product import (  # noqa: E402
    CreateProductRequest,
    CreateProductVariantRequest,
    ProductImageInput,
)
from app.services.category import create_category_service  # noqa: E402
from app.services.image import delete_imagekit_files, upload_images_service  # noqa: E402
from app.services.product import create_product_service  # noqa: E402

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_IMAGES_DIR = PROJECT_ROOT / "seed_images"


@dataclass(frozen=True)
class SeedProduct:
    title: str
    ingredients: str
    product_type: ProductType

    @property
    def category(self) -> str:
        return "Attars" if self.product_type is ProductType.AATR else "Perfumes"

    @property
    def details(self) -> str:
        return (
            f"{self.title} is a long-lasting {self.product_type.value} "
            f"blended with {self.ingredients.lower()}."
        )


SEED_PRODUCTS: tuple[SeedProduct, ...] = (
    SeedProduct("Royal Oud Attar", "Oud, Amber, Musk", ProductType.AATR),
    SeedProduct("Taifi Rose Attar", "Rose, Sandalwood, Musk", ProductType.AATR),
    SeedProduct("White Musk Attar", "White Musk, Vanilla, Amber", ProductType.AATR),
    SeedProduct(
        "Mysore Sandalwood Attar", "Sandalwood, Cedar, Amber", ProductType.AATR
    ),
    SeedProduct("Jasmine Sambac Attar", "Jasmine, Neroli, Musk", ProductType.AATR),
    SeedProduct("Saffron Oud Attar", "Saffron, Oud, Rose", ProductType.AATR),
    SeedProduct("Amber Musk Attar", "Amber, Musk, Vanilla", ProductType.AATR),
    SeedProduct("Bakhoor Rose Attar", "Bakhoor, Rose, Oud", ProductType.AATR),
    SeedProduct(
        "Kashmiri Musk Attar", "Musk, Saffron, Sandalwood", ProductType.AATR
    ),
    SeedProduct("Oud Al Layl Attar", "Oud, Rose, Amber", ProductType.AATR),
    SeedProduct("Midnight Oud Perfume", "Oud, Patchouli, Vanilla", ProductType.PERFUME),
    SeedProduct(
        "Golden Amber Perfume", "Amber, Tonka Bean, Bergamot", ProductType.PERFUME
    ),
    SeedProduct("Aqua Fresh Perfume", "Sea Notes, Citrus, Musk", ProductType.PERFUME),
    SeedProduct("Velvet Rose Perfume", "Rose, Peony, Musk", ProductType.PERFUME),
    SeedProduct(
        "Spiced Cedar Perfume", "Cedar, Cinnamon, Vetiver", ProductType.PERFUME
    ),
    SeedProduct("Citrus Bloom Perfume", "Lemon, Neroli, Jasmine", ProductType.PERFUME),
    SeedProduct("Noir Musk Perfume", "Musk, Leather, Amber", ProductType.PERFUME),
    SeedProduct(
        "Desert Bloom Perfume",
        "Orange Blossom, Amber, Sandalwood",
        ProductType.PERFUME,
    ),
    SeedProduct(
        "Ocean Mist Perfume", "Marine Notes, Bergamot, White Musk", ProductType.PERFUME
    ),
    SeedProduct(
        "Amber Nuit Perfume", "Amber, Vanilla, Sandalwood", ProductType.PERFUME
    ),
)

AATR_VARIANTS = (
    (3.0, 400.0, 500.0),
    (6.0, 750.0, 900.0),
    (12.0, 1400.0, 1700.0),
)
PERFUME_VARIANTS = (
    (50.0, 1600.0, 2000.0),
    (100.0, 2800.0, 3400.0),
)


def _build_variants(
    seed_product: SeedProduct, index: int
) -> list[CreateProductVariantRequest]:
    base = AATR_VARIANTS if seed_product.product_type is ProductType.AATR else PERFUME_VARIANTS
    multiplier = 1 + (index % 6) * 0.06
    variants: list[CreateProductVariantRequest] = []

    for offset, (size, price, compare_price) in enumerate(base):
        stock = 8 + (index * 7 + offset * 11) % 50
        variants.append(
            CreateProductVariantRequest(
                size=size,
                unit=SizeUnit.CM,
                price=round(price * multiplier, 2),
                compare_price=round(compare_price * multiplier, 2),
                stock=stock,
                product_type=seed_product.product_type,
            )
        )

    return variants


def _png_gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> bytes:
    width = height = 320
    raw = bytearray()

    for y in range(height):
        ratio = y / (height - 1)
        color = tuple(
            int(top[channel] + (bottom[channel] - top[channel]) * ratio)
            for channel in range(3)
        )
        raw.append(0)
        raw.extend(bytes(color) * width)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def _placeholder_image(index: int, image_index: int) -> bytes:
    hue = (index * 0.11 + image_index * 0.05) % 1.0
    top = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.45, 0.95))
    bottom = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.85, 0.45))
    return _png_gradient(top, bottom)  # type: ignore[arg-type]


def _image_pool(images_dir: Path | None, product_type: ProductType) -> list[Path]:
    if images_dir is None or not images_dir.is_dir():
        return []

    typed_dir = images_dir / product_type.value
    folder = typed_dir if typed_dir.is_dir() else images_dir
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def _build_upload_files(
    seed_product: SeedProduct,
    index: int,
    pool: list[Path],
    count: int,
) -> list[UploadFile]:
    files: list[UploadFile] = []

    for image_index in range(count):
        unique = uuid4().hex[:10]
        if pool:
            source = pool[(index + image_index) % len(pool)]
            content = source.read_bytes()
            filename = f"seed-{unique}-{source.name}"
        else:
            content = _placeholder_image(index, image_index)
            filename = f"seed-{index}-{image_index}-{unique}.png"

        files.append(UploadFile(file=BytesIO(content), filename=filename))

    return files


async def _get_or_create_category(session, name: str) -> Category:
    stmt = select(Category).where(func.lower(Category.name) == name.lower())
    category = await session.scalar(stmt)
    if category is not None:
        return category

    return await create_category_service(session, CreateCategoryRequest(name=name))


async def _cleanup_images(session, images) -> None:
    if not images:
        return
    await delete_imagekit_files([image.file_id for image in images])
    try:
        for image in images:
            await delete_image_repo(session, image)
        await session.commit()
    except Exception:
        await session.rollback()


async def seed(limit: int, images_dir: Path | None, dry_run: bool) -> int:
    products = SEED_PRODUCTS[:limit]

    if dry_run:
        for index, seed_product in enumerate(products):
            variants = _build_variants(seed_product, index)
            print(
                f"[dry-run] {seed_product.title} ({seed_product.category}) "
                f"- {len(variants)} variants, "
                f"{2 + index % 2} images"
            )
        return 0

    created = skipped = failed = 0

    async with SessionLocal() as session:
        for index, seed_product in enumerate(products):
            existing = await get_product_by_title_repo(session, seed_product.title)
            if existing is not None:
                skipped += 1
                print(f"[skip] {seed_product.title} already exists")
                continue

            images = []
            try:
                category = await _get_or_create_category(
                    session, seed_product.category
                )
                image_count = 2 + index % 2
                pool = _image_pool(images_dir, seed_product.product_type)
                upload_files = _build_upload_files(
                    seed_product, index, pool, image_count
                )
                images = await upload_images_service(session, upload_files)

                payload = CreateProductRequest(
                    title=seed_product.title,
                    ingredients=seed_product.ingredients,
                    details=seed_product.details,
                    is_active=True,
                    category_id=category.id,
                    variants=_build_variants(seed_product, index),
                    images=[
                        ProductImageInput(image_id=image.id, is_primary=position == 0)
                        for position, image in enumerate(images)
                    ],
                )
                product = await create_product_service(session, payload)
            except Exception as exc:
                await session.rollback()
                await _cleanup_images(session, images)
                failed += 1
                print(f"[fail] {seed_product.title}: {exc}")
                continue

            created += 1
            print(
                f"[ok] {seed_product.title} (id={product.id}, "
                f"variants={len(payload.variants)}, images={len(images)})"
            )

    print(
        f"\nDone. created={created} skipped={skipped} failed={failed} "
        f"total={len(products)}"
    )
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed sample Al Qasr products.")
    parser.add_argument(
        "--limit",
        type=int,
        default=len(SEED_PRODUCTS),
        help=f"Number of products to seed (max {len(SEED_PRODUCTS)}).",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=DEFAULT_IMAGES_DIR,
        help=(
            "Directory with real images (optional sub-folders: aatr/, perfume/). "
            "Placeholder images are generated when absent."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be seeded without touching the database.",
    )
    args = parser.parse_args()

    if not 1 <= args.limit <= len(SEED_PRODUCTS):
        parser.error(f"--limit must be between 1 and {len(SEED_PRODUCTS)}")

    if args.images_dir is not None and not args.images_dir.is_dir():
        args.images_dir = None

    return args


def main() -> None:
    args = parse_args()
    raise SystemExit(asyncio.run(seed(args.limit, args.images_dir, args.dry_run)))


if __name__ == "__main__":
    main()
