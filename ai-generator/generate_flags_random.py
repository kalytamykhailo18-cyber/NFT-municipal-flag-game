"""
AI Flag Image Generator for Municipal Flag NFT Game.

This script generates flag images using Stable Diffusion.
Supports both local generation and cloud APIs (Replicate, Stability AI).
"""
import os
import json
import time
from pathlib import Path
from typing import Optional
from tqdm import tqdm

from config import (
    Config, MUNICIPALITIES_DATA, LOCATION_TYPES, CATEGORY_ASSIGNMENT
)

# Ensure output directories exist
Config.ensure_directories()


def get_prompt_for_flag(municipality: str, region: str, country: str, location_type: str) -> str:
    """Generate a prompt for Stable Diffusion."""
    base_prompt = f"""A beautiful heraldic municipal flag design for {municipality}, {region}, {country}.
The flag features a {location_type.lower()} as the central element.
Traditional European heraldic style with vibrant colors.
Symmetrical coat of arms design with ornate borders.
High quality, detailed, professional flag design.
Clean background, centered composition."""

    return base_prompt


def get_negative_prompt() -> str:
    """Get negative prompt to avoid unwanted elements."""
    return """blurry, low quality, distorted, deformed, ugly, bad anatomy,
watermark, text, signature, logo, modern, photorealistic, photograph,
person, human, face, hands, anime, cartoon"""


class LocalGenerator:
    """Generate images using local Stable Diffusion."""

    def __init__(self):
        self.pipe = None

    def load_model(self):
        """Load the Stable Diffusion model."""
        print("Loading Stable Diffusion model locally...")
        try:
            from diffusers import StableDiffusionPipeline
            import torch

            self.pipe = StableDiffusionPipeline.from_pretrained(
                Config.SD_MODEL_PATH,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )

            if torch.cuda.is_available():
                self.pipe = self.pipe.to("cuda")
                print("Using CUDA GPU")
            else:
                print("Using CPU (this will be slow)")

        except ImportError:
            raise ImportError("Please install diffusers and torch: pip install diffusers torch")

    def generate(self, prompt: str, negative_prompt: str, output_path: Path) -> bool:
        """Generate an image."""
        if self.pipe is None:
            self.load_model()

        try:
            image = self.pipe(
                prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=Config.NUM_INFERENCE_STEPS,
                guidance_scale=Config.GUIDANCE_SCALE,
                height=Config.IMAGE_HEIGHT,
                width=Config.IMAGE_WIDTH
            ).images[0]

            image.save(output_path)
            return True

        except Exception as e:
            print(f"Error generating image: {e}")
            return False


class ReplicateGenerator:
    """Generate images using Replicate API."""

    def __init__(self):
        self.client = None

    def initialize(self):
        """Initialize Replicate client."""
        if not Config.REPLICATE_API_TOKEN:
            raise ValueError("REPLICATE_API_TOKEN not set in .env file")

        try:
            import replicate
            os.environ["REPLICATE_API_TOKEN"] = Config.REPLICATE_API_TOKEN
            self.client = replicate
            print("Replicate API initialized")
        except ImportError:
            raise ImportError("Please install replicate: pip install replicate")

    def generate(self, prompt: str, negative_prompt: str, output_path: Path) -> bool:
        """Generate an image using Replicate."""
        if self.client is None:
            self.initialize()

        try:
            output = self.client.run(
                "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf",
                input={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": Config.IMAGE_WIDTH,
                    "height": Config.IMAGE_HEIGHT,
                    "num_inference_steps": Config.NUM_INFERENCE_STEPS,
                    "guidance_scale": Config.GUIDANCE_SCALE
                }
            )

            # Download the image
            import requests
            if output and len(output) > 0:
                image_url = output[0]
                response = requests.get(image_url)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True

        except Exception as e:
            print(f"Error generating image: {e}")

        return False


class StabilityGenerator:
    """Generate images using Stability AI API."""

    def __init__(self):
        self.api_key = Config.STABILITY_API_KEY

    def generate(self, prompt: str, negative_prompt: str, output_path: Path) -> bool:
        """Generate an image using Stability AI."""
        if not self.api_key:
            raise ValueError("STABILITY_API_KEY not set in .env file")

        try:
            import requests

            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "text_prompts": [
                        {"text": prompt, "weight": 1},
                        {"text": negative_prompt, "weight": -1}
                    ],
                    "cfg_scale": Config.GUIDANCE_SCALE,
                    "height": Config.IMAGE_HEIGHT,
                    "width": Config.IMAGE_WIDTH,
                    "steps": Config.NUM_INFERENCE_STEPS,
                    "samples": 1
                }
            )

            if response.status_code == 200:
                data = response.json()
                import base64
                image_data = base64.b64decode(data["artifacts"][0]["base64"])
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                return True
            else:
                print(f"API Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Error generating image: {e}")

        return False


class PlaceholderGenerator:
    """Generate placeholder images when no AI API is available."""

    def generate(self, prompt: str, negative_prompt: str, output_path: Path) -> bool:
        """Generate a placeholder image with text."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Create a colored image
            colors = [
                (70, 130, 180),   # Steel Blue
                (178, 34, 34),    # Firebrick
                (34, 139, 34),    # Forest Green
                (255, 140, 0),    # Dark Orange
                (128, 0, 128),    # Purple
                (0, 128, 128),    # Teal
                (139, 69, 19),    # Saddle Brown
                (47, 79, 79),     # Dark Slate Gray
            ]

            # Use hash of prompt to get consistent color
            color_index = hash(prompt) % len(colors)
            bg_color = colors[color_index]

            img = Image.new('RGB', (Config.IMAGE_WIDTH, Config.IMAGE_HEIGHT), bg_color)
            draw = ImageDraw.Draw(img)

            # Add some heraldic-style decorations
            # Border
            border_color = tuple(max(0, c - 50) for c in bg_color)
            draw.rectangle([10, 10, Config.IMAGE_WIDTH - 10, Config.IMAGE_HEIGHT - 10],
                           outline=border_color, width=5)

            # Center cross pattern
            center_x = Config.IMAGE_WIDTH // 2
            center_y = Config.IMAGE_HEIGHT // 2
            cross_color = tuple(min(255, c + 80) for c in bg_color)

            # Vertical line
            draw.rectangle([center_x - 20, 50, center_x + 20, Config.IMAGE_HEIGHT - 50],
                           fill=cross_color)
            # Horizontal line
            draw.rectangle([50, center_y - 20, Config.IMAGE_WIDTH - 50, center_y + 20],
                           fill=cross_color)

            # Add text (location type)
            # Extract location type from prompt
            for location in LOCATION_TYPES:
                if location.lower() in prompt.lower():
                    try:
                        font = ImageFont.truetype("arial.ttf", 24)
                    except:
                        font = ImageFont.load_default()

                    text = location.upper()
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_x = (Config.IMAGE_WIDTH - text_width) // 2
                    draw.text((text_x, Config.IMAGE_HEIGHT - 60), text,
                              fill=(255, 255, 255), font=font)
                    break

            img.save(output_path)
            return True

        except Exception as e:
            print(f"Error creating placeholder: {e}")
            return False


def get_generator():
    """Get the appropriate generator based on configuration."""
    if Config.SD_LOCAL_ENABLED:
        print("Using local Stable Diffusion")
        return LocalGenerator()
    elif Config.SD_USE_CLOUD_API:
        # Prefer Stability AI over Replicate (Replicate requires payment)
        if Config.STABILITY_API_KEY:
            print("Using Stability AI API")
            return StabilityGenerator()
        elif Config.REPLICATE_API_TOKEN:
            print("Using Replicate API")
            return ReplicateGenerator()

    print("No AI API configured, using placeholder generator")
    return PlaceholderGenerator()


def generate_all_flags():
    """Generate all flag images for the demo."""
    print("=" * 60)
    print("Municipal Flag NFT - Image Generator")
    print("=" * 60)

    generator = get_generator()
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

            for i, location_type in enumerate(LOCATION_TYPES):
                flag_id += 1

                # Generate filename
                filename = f"{country['code']}_{municipality['name'].lower()}_{flag_id:03d}.png"
                output_path = Config.OUTPUT_DIR / filename

                # Skip if already exists
                if output_path.exists():
                    skipped += 1
                    tqdm.write(f"  [{flag_id}/{total_flags}] {location_type}: Skipped (exists)")
                    continue

                # Generate prompt
                prompt = get_prompt_for_flag(
                    municipality["name"],
                    region["name"],
                    country["name"],
                    location_type
                )

                # Generate image
                tqdm.write(f"  [{flag_id}/{total_flags}] {location_type}: Generating...")

                success = generator.generate(prompt, negative_prompt, output_path)

                if success:
                    generated += 1
                    tqdm.write(f"  [{flag_id}/{total_flags}] {location_type}: Done!")
                else:
                    failed += 1
                    tqdm.write(f"  [{flag_id}/{total_flags}] {location_type}: FAILED")

                # Rate limiting for API calls
                if Config.SD_USE_CLOUD_API:
                    time.sleep(1)

    # Summary
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"  Generated: {generated}")
    print(f"  Skipped:   {skipped}")
    print(f"  Failed:    {failed}")
    print(f"  Total:     {flag_id}")
    print(f"\nImages saved to: {Config.OUTPUT_DIR}")


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


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--metadata-only":
        generate_metadata()
    else:
        generate_all_flags()
        generate_metadata()
