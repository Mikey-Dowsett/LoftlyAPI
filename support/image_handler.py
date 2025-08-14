import io

from PIL import Image


def compress_image(content: str, mime_type: str, target_size_kb: int = 976) -> bytes:
    max_bytes = target_size_kb * 1024
    image = Image.open(content)

    # Convert to RGB (needed for JPEG)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Set initial quality/resizing parameters
    quality = 85
    width, height = image.size
    scale_factor = 0.9  # Shrink by 10% each iteration
    min_quality = 20

    output = io.BytesIO()

    while True:
        temp_io = io.BytesIO()

        # Resize if necessary
        image_resized = image.resize((int(width), int(height)), Image.LANCZOS)

        if mime_type == "image/png":
            image_resized.save(temp_io, format="PNG", optimize=True)
        elif mime_type in ["image/jpeg", "image/jpg"]:
            image_resized.save(temp_io, format="JPEG", optimize=True, quality=quality)
        else:
            raise ValueError("Unsupported image type")

        size = temp_io.tell()

        # Check if image meets size requirement
        if size <= max_bytes or (quality <= min_quality and (width < 200 or height < 200)):
            output = temp_io
            break

        # Otherwise shrink more
        width *= scale_factor
        height *= scale_factor
        quality = max(min_quality, quality - 5)

    return output.getvalue()
