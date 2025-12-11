"""
AI Flag Image Generator for Municipal Flag NFT Game.

This script generates flag images using AI APIs:
- Primary: Replicate API (Stable Diffusion XL) - requires paid account
- Fallback: Stability AI API - has free tier
- Last resort: Placeholder generator

It can optionally fetch real Street View images and transform them.
"""
import os
import sys
import json
import time
import base64
import requests
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / ".env")

from config import (
    Config, MUNICIPALITIES_DATA, LOCATION_TYPES, CATEGORY_ASSIGNMENT
)

# Ensure output directories exist
Config.ensure_directories()

# API Configuration
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Replicate SDXL model for high quality image generation
SDXL_MODEL = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"

# Rate limiting settings
RATE_LIMIT_DELAY = 10  # seconds between API calls


def get_street_view_image(latitude: float, longitude: float, heading: int = 0) -> Optional[bytes]:
    """
    Fetch Street View image from Google Maps API.

    Args:
        latitude: Location latitude
        longitude: Location longitude
        heading: Camera direction (0-360)

    Returns:
        Image bytes or None if not available
    """
    if not GOOGLE_MAPS_API_KEY:
        print("  WARNING: GOOGLE_MAPS_API_KEY not set, skipping Street View")
        return None

    # Check if Street View is available
    metadata_url = "https://maps.googleapis.com/maps/api/streetview/metadata"
    params = {
        "location": f"{latitude},{longitude}",
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        response = requests.get(metadata_url, params=params, timeout=10)
        metadata = response.json()

        if metadata.get("status") != "OK":
            print(f"  No Street View at ({latitude}, {longitude})")
            return None

        # Fetch the actual image
        image_url = "https://maps.googleapis.com/maps/api/streetview"
        image_params = {
            "size": "640x640",
            "location": f"{latitude},{longitude}",
            "heading": heading,
            "pitch": 0,
            "fov": 90,
            "key": GOOGLE_MAPS_API_KEY
        }

        image_response = requests.get(image_url, params=image_params, timeout=30)

        if "image" in image_response.headers.get("content-type", ""):
            return image_response.content

        return None

    except Exception as e:
        print(f"  Error fetching Street View: {e}")
        return None


def generate_with_replicate(
    prompt: str,
    negative_prompt: str,
    width: int = 1024,
    height: int = 1024
) -> Optional[bytes]:
    """
    Generate image using Replicate API with SDXL.
    Requires paid Replicate account with credits.
    """
    if not REPLICATE_API_TOKEN:
        return None

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    model_input = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "num_inference_steps": 30,
        "guidance_scale": 7.5,
        "scheduler": "K_EULER",
        "num_outputs": 1
    }

    model_version = SDXL_MODEL.split(":")[-1]
    payload = {"version": model_version, "input": model_input}

    try:
        response = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 402:
            print("\n  [Replicate] Insufficient credits - need payment")
            return None
        elif response.status_code == 429:
            print("\n  [Replicate] Rate limited - waiting...")
            time.sleep(15)
            return None
        elif response.status_code != 201:
            return None

        prediction = response.json()
        prediction_id = prediction.get("id")
        if not prediction_id:
            return None

        # Poll for completion
        poll_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        max_wait = 120
        start_time = time.time()

        while time.time() - start_time < max_wait:
            poll_response = requests.get(poll_url, headers=headers, timeout=10)
            result = poll_response.json()
            status = result.get("status")

            if status == "succeeded":
                output = result.get("output")
                if isinstance(output, list) and len(output) > 0:
                    image_url = output[0]
                elif isinstance(output, str):
                    image_url = output
                else:
                    return None
                image_response = requests.get(image_url, timeout=30)
                return image_response.content

            elif status in ("failed", "canceled"):
                return None

            time.sleep(2)

        return None

    except Exception:
        return None


def generate_with_stability(
    prompt: str,
    negative_prompt: str,
    width: int = 1024,
    height: int = 1024
) -> Optional[bytes]:
    """
    Generate image using Stability AI API.
    Has free tier with 25 credits.
    Get API key at: https://platform.stability.ai/
    """
    if not STABILITY_API_KEY:
        return None

    try:
        response = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {STABILITY_API_KEY}"
            },
            json={
                "text_prompts": [
                    {"text": prompt, "weight": 1},
                    {"text": negative_prompt, "weight": -1}
                ],
                "cfg_scale": 7,
                "height": height,
                "width": width,
                "steps": 30,
                "samples": 1
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            image_data = base64.b64decode(data["artifacts"][0]["base64"])
            return image_data
        elif response.status_code == 402:
            print("\n  [Stability] Insufficient credits")
            return None
        elif response.status_code == 429:
            print("\n  [Stability] Rate limited")
            return None
        else:
            return None

    except Exception:
        return None


def generate_placeholder(
    municipality: str,
    location_type: str,
    category: int,
    width: int = 1024,
    height: int = 1024
) -> Optional[bytes]:
    """
    Generate a placeholder image when no AI API is available.
    Creates a simple heraldic-style flag design.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("\n  [Placeholder] PIL not installed. Run: pip install Pillow")
        return None

    # Category colors
    category_colors = {
        0: [(70, 130, 180), (135, 206, 235)],    # Standard - Steel Blue
        1: [(218, 165, 32), (255, 215, 0)],      # Plus - Gold
        2: [(128, 0, 128), (186, 85, 211)],      # Premium - Purple
    }

    colors = category_colors.get(category, category_colors[0])
    bg_color = colors[0]
    accent_color = colors[1]

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Border
    border_width = 20
    draw.rectangle(
        [border_width, border_width, width - border_width, height - border_width],
        outline=accent_color,
        width=10
    )

    # Center shield shape
    cx, cy = width // 2, height // 2
    shield_points = [
        (cx - 150, cy - 180),
        (cx + 150, cy - 180),
        (cx + 150, cy + 50),
        (cx, cy + 180),
        (cx - 150, cy + 50),
    ]
    draw.polygon(shield_points, fill=accent_color, outline=(255, 255, 255), width=5)

    # Location type icon (simple shapes)
    icon_color = bg_color
    if location_type == "Town Hall":
        # Building shape
        draw.rectangle([cx-80, cy-80, cx+80, cy+60], fill=icon_color)
        draw.polygon([(cx-100, cy-80), (cx, cy-150), (cx+100, cy-80)], fill=icon_color)
    elif location_type == "Church":
        # Cross
        draw.rectangle([cx-15, cy-100, cx+15, cy+80], fill=icon_color)
        draw.rectangle([cx-60, cy-50, cx+60, cy-20], fill=icon_color)
    elif location_type == "Fire Station":
        # Flame shape
        draw.ellipse([cx-50, cy-80, cx+50, cy+60], fill=(255, 100, 50))
    elif location_type == "Bridge":
        # Arch
        draw.arc([cx-100, cy-50, cx+100, cy+100], 0, 180, fill=icon_color, width=20)
    elif location_type == "Fountain":
        # Water drops
        draw.ellipse([cx-60, cy-40, cx+60, cy+60], fill=(100, 149, 237))
    elif location_type == "Park":
        # Tree
        draw.ellipse([cx-50, cy-100, cx+50, cy], fill=(34, 139, 34))
        draw.rectangle([cx-15, cy, cx+15, cy+80], fill=(139, 69, 19))
    elif location_type == "Market Square":
        # Grid pattern
        for i in range(-2, 3):
            for j in range(-2, 3):
                if (i + j) % 2 == 0:
                    draw.rectangle([cx+i*30-10, cy+j*30-10, cx+i*30+10, cy+j*30+10], fill=icon_color)
    else:  # Bakery or other
        # Simple circle
        draw.ellipse([cx-50, cy-50, cx+50, cy+50], fill=icon_color)

    # Add text
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = font_large

    # Municipality name at top
    text = municipality.upper()
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, 50), text, fill=(255, 255, 255), font=font_large)

    # Location type at bottom
    text2 = location_type.upper()
    bbox2 = draw.textbbox((0, 0), text2, font=font_small)
    text2_width = bbox2[2] - bbox2[0]
    draw.text(((width - text2_width) // 2, height - 80), text2, fill=(255, 255, 255), font=font_small)

    # Category badge
    category_names = ["STANDARD", "PLUS", "PREMIUM"]
    cat_text = category_names[category]
    draw.rectangle([width - 150, 30, width - 30, 70], fill=accent_color)
    draw.text((width - 140, 38), cat_text, fill=(0, 0, 0), font=font_small)

    # Save to bytes
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def get_flag_prompt(municipality: str, region: str, country: str, location_type: str) -> str:
    """Generate an optimized prompt for flag image generation."""
    return f"""A beautiful artistic municipal flag design representing {location_type} in {municipality}, {region}, {country}.
Style: heraldic emblem, coat of arms, official flag design, bold colors, clean lines, symmetrical composition.
The design features iconic elements of a {location_type.lower()} in European style.
High quality, professional municipal flag, vector art style, centered emblem on solid background."""


def get_negative_prompt() -> str:
    """Negative prompt to avoid unwanted elements."""
    return """photorealistic, photograph, blurry, low quality, distorted, deformed,
watermark, text, signature, logo, person, human, face, hands, anime, cartoon,
noisy, grainy, oversaturated, dark, ugly, amateur"""


def generate_image(
    prompt: str,
    negative_prompt: str,
    municipality: str,
    location_type: str,
    category: int,
    use_placeholder: bool = False
) -> Optional[bytes]:
    """
    Generate image using available APIs with fallback chain:
    1. Replicate API (if configured and has credits)
    2. Stability AI API (if configured)
    3. Placeholder generator (always available)
    """
    # If placeholder mode is forced
    if use_placeholder:
        return generate_placeholder(municipality, location_type, category)

    # Try Replicate first
    if REPLICATE_API_TOKEN:
        print("[Replicate]", end=" ", flush=True)
        result = generate_with_replicate(prompt, negative_prompt)
        if result:
            return result

    # Try Stability AI
    if STABILITY_API_KEY:
        print("[Stability]", end=" ", flush=True)
        result = generate_with_stability(prompt, negative_prompt)
        if result:
            return result

    # Fallback to placeholder
    print("[Placeholder]", end=" ", flush=True)
    return generate_placeholder(municipality, location_type, category)


def generate_all_flags(use_placeholder: bool = False):
    """Generate all flag images for the demo municipalities."""
    print("=" * 60)
    print("Municipal Flag NFT - AI Image Generator")
    print("=" * 60)

    # Check API configuration
    print("\nAPI Configuration:")
    print(f"  Replicate API:    {'Configured' if REPLICATE_API_TOKEN else 'Not configured'}")
    print(f"  Stability AI API: {'Configured' if STABILITY_API_KEY else 'Not configured'}")
    print(f"  Google Maps API:  {'Configured' if GOOGLE_MAPS_API_KEY else 'Not configured'}")

    if use_placeholder:
        print("\n  Mode: PLACEHOLDER (no AI)")
    elif not REPLICATE_API_TOKEN and not STABILITY_API_KEY:
        print("\n  WARNING: No AI API configured!")
        print("  Will generate placeholder images.")
        print("\n  To use AI generation, add to .env:")
        print("    REPLICATE_API_TOKEN=r8_xxx  (https://replicate.com/account)")
        print("    STABILITY_API_KEY=sk-xxx    (https://platform.stability.ai/)")
        use_placeholder = True

    negative_prompt = get_negative_prompt()

    flag_id = 0
    generated = 0
    skipped = 0
    failed = 0

    # Calculate total
    total_flags = sum(
        len(country_data["municipalities"]) * len(LOCATION_TYPES)
        for country_data in MUNICIPALITIES_DATA
    )

    print(f"\nGenerating {total_flags} flag images...")
    print(f"Output directory: {Config.OUTPUT_DIR}\n")

    for country_data in MUNICIPALITIES_DATA:
        country = country_data["country"]
        region = country_data["region"]

        for municipality in country_data["municipalities"]:
            print(f"\n{country['name']} > {region['name']} > {municipality['name']}")

            for location_type in LOCATION_TYPES:
                flag_id += 1

                # Generate filename
                filename = f"{country['code']}_{municipality['name'].lower()}_{flag_id:03d}.png"
                output_path = Config.OUTPUT_DIR / filename

                # Skip if already exists
                if output_path.exists():
                    skipped += 1
                    print(f"  [{flag_id}/{total_flags}] {location_type}: Skipped (exists)")
                    continue

                print(f"  [{flag_id}/{total_flags}] {location_type}: ", end="", flush=True)

                # Get category for this location type
                category = CATEGORY_ASSIGNMENT.get(location_type, 0)

                # Generate prompt
                prompt = get_flag_prompt(
                    municipality["name"],
                    region["name"],
                    country["name"],
                    location_type
                )

                # Generate image
                image_data = generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    municipality=municipality["name"],
                    location_type=location_type,
                    category=category,
                    use_placeholder=use_placeholder
                )

                if image_data:
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                    generated += 1
                    print("Done!")
                else:
                    failed += 1
                    print("FAILED")

                # Rate limiting for API calls
                if not use_placeholder:
                    time.sleep(RATE_LIMIT_DELAY)

    # Summary
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"  Generated: {generated}")
    print(f"  Skipped:   {skipped}")
    print(f"  Failed:    {failed}")
    print(f"  Total:     {flag_id}")
    print(f"\nImages saved to: {Config.OUTPUT_DIR}")


def generate_single_flag(
    municipality: str,
    region: str,
    country: str,
    location_type: str,
    latitude: float,
    longitude: float,
    output_name: str
) -> bool:
    """
    Generate a single flag image.

    Args:
        municipality: Municipality name
        region: Region name
        country: Country name
        location_type: Type of location (Town Hall, Church, etc.)
        latitude: Location latitude
        longitude: Location longitude
        output_name: Output filename

    Returns:
        True if successful
    """
    if not REPLICATE_API_TOKEN:
        print("ERROR: REPLICATE_API_TOKEN not set")
        return False

    output_path = Config.OUTPUT_DIR / output_name

    print(f"Generating flag for {location_type} in {municipality}...")

    # Try Street View
    street_view_image = None
    if GOOGLE_MAPS_API_KEY:
        street_view_image = get_street_view_image(latitude, longitude)
        if street_view_image:
            print("  Using Street View image as base")

    prompt = get_flag_prompt(municipality, region, country, location_type)
    negative_prompt = get_negative_prompt()

    image_data = generate_with_replicate(
        prompt=prompt,
        negative_prompt=negative_prompt,
        input_image=street_view_image,
        width=1024,
        height=1024
    )

    if image_data:
        with open(output_path, 'wb') as f:
            f.write(image_data)
        print(f"  Saved to: {output_path}")
        return True

    return False


def generate_metadata():
    """Generate metadata JSON files for all flags."""
    print("\n" + "=" * 60)
    print("Generating Metadata Files")
    print("=" * 60)

    flag_id = 0
    metadata_list = []

    for country_data in MUNICIPALITIES_DATA:
        country = country_data["country"]
        region = country_data["region"]

        for municipality in country_data["municipalities"]:
            for i, location_type in enumerate(LOCATION_TYPES):
                flag_id += 1

                # Calculate coordinates with offset
                lat_offset = (i % 4) * 0.001
                lon_offset = (i // 4) * 0.001
                latitude = municipality["latitude"] + lat_offset
                longitude = municipality["longitude"] + lon_offset

                # Get category
                category = CATEGORY_ASSIGNMENT.get(location_type, 0)
                category_name = ["Standard", "Plus", "Premium"][category]

                # Create metadata
                metadata = {
                    "name": f"Flag at {latitude:.6f}, {longitude:.6f}",
                    "description": f"{location_type} flag of {municipality['name']}, {region['name']}, {country['name']}. Part of the Municipal Flag NFT collection.",
                    "image": "",  # Will be set after IPFS upload
                    "external_url": f"https://municipalflagnft.demo/{flag_id}",
                    "attributes": [
                        {"trait_type": "Country", "value": country["name"]},
                        {"trait_type": "Country Code", "value": country["code"]},
                        {"trait_type": "Region", "value": region["name"]},
                        {"trait_type": "Municipality", "value": municipality["name"]},
                        {"trait_type": "Location Type", "value": location_type},
                        {"trait_type": "Category", "value": category_name},
                        {"trait_type": "Latitude", "value": latitude},
                        {"trait_type": "Longitude", "value": longitude},
                        {"display_type": "number", "trait_type": "Flag ID", "value": flag_id}
                    ]
                }

                # Save individual metadata file
                metadata_path = Config.METADATA_DIR / f"{flag_id}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                metadata_list.append({
                    "flag_id": flag_id,
                    "image_filename": f"{country['code']}_{municipality['name'].lower()}_{flag_id:03d}.png",
                    "metadata_filename": f"{flag_id}.json",
                    "metadata": metadata
                })

    # Save combined metadata file
    combined_path = Config.METADATA_DIR / "all_metadata.json"
    with open(combined_path, 'w') as f:
        json.dump(metadata_list, f, indent=2)

    print(f"Generated {flag_id} metadata files")
    print(f"Metadata saved to: {Config.METADATA_DIR}")
    print(f"Combined file: {combined_path}")


def test_api():
    """Test the Replicate API connection."""
    print("Testing Replicate API connection...")

    if not REPLICATE_API_TOKEN:
        print("ERROR: REPLICATE_API_TOKEN not set in .env")
        return False

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        # Just check if we can access the API
        response = requests.get(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            print("SUCCESS: Replicate API is accessible")
            return True
        else:
            print(f"ERROR: API returned status {response.status_code}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--metadata-only":
            generate_metadata()
        elif command == "--test":
            test_api()
        elif command == "--placeholder":
            # Generate placeholder images without AI (free, fast)
            generate_all_flags(use_placeholder=True)
            generate_metadata()
        elif command == "--single" and len(sys.argv) >= 8:
            # Usage: --single "Barcelona" "Catalonia" "Spain" "Town Hall" 41.3851 2.1734 "test_flag.png"
            generate_single_flag(
                municipality=sys.argv[2],
                region=sys.argv[3],
                country=sys.argv[4],
                location_type=sys.argv[5],
                latitude=float(sys.argv[6]),
                longitude=float(sys.argv[7]),
                output_name=sys.argv[8] if len(sys.argv) > 8 else "test_flag.png"
            )
        elif command == "--help" or command == "-h":
            print("Municipal Flag NFT - AI Image Generator")
            print("=" * 50)
            print("\nUsage:")
            print("  python generate_flags.py                 # Generate with AI (needs API keys)")
            print("  python generate_flags.py --placeholder   # Generate placeholder images (FREE)")
            print("  python generate_flags.py --test          # Test API connection")
            print("  python generate_flags.py --metadata-only # Generate metadata JSON only")
            print("\nAPI Keys (add to root .env file):")
            print("  REPLICATE_API_TOKEN=r8_xxx    # https://replicate.com/account")
            print("  STABILITY_API_KEY=sk-xxx      # https://platform.stability.ai/")
            print("\nNote: Without API keys, placeholder images are generated automatically.")
        else:
            print(f"Unknown command: {command}")
            print("Use --help for usage information")
    else:
        generate_all_flags()
        generate_metadata()
