"""
Municipal Flag NFT - ALL-IN-ONE Script

ONE COMMAND does everything:
1. Generate flag images (placeholder mode - FREE)
2. Upload images to Pinata IPFS
3. Update metadata JSON files with IPFS hashes
4. Seed backend database with all flag data

Usage:
    pip install -r requirements.txt
    python run_all.py

That's it!
"""
import os
import sys
import json
import requests
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv

# ============================================================
# SETUP
# ============================================================

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = SCRIPT_DIR / "output"
METADATA_DIR = SCRIPT_DIR / "metadata"

# Load environment from both root .env and backend/.env
load_dotenv(ROOT_DIR / ".env")  # Root config (Pinata, etc)
load_dotenv(ROOT_DIR / "backend" / ".env")  # Backend config (admin key, database)

# Pinata credentials (from root .env)
PINATA_JWT = os.getenv("PINATA_JWT", "")
PINATA_API_KEY = os.getenv("PINATA_API_KEY", "")
PINATA_API_SECRET = os.getenv("PINATA_API_SECRET", "")

# Backend URL and Admin Key (from backend/.env)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key-change-in-production")

# Create directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# MUNICIPALITY DATA (same as config.py)
# ============================================================

MUNICIPALITIES_DATA = [
    {
        "country": {"name": "Spain", "code": "ESP"},
        "region": {"name": "Catalonia"},
        "municipalities": [
            {"name": "Barcelona", "latitude": 41.3851, "longitude": 2.1734},
            {"name": "Girona", "latitude": 41.9794, "longitude": 2.8214},
        ]
    },
    {
        "country": {"name": "France", "code": "FRA"},
        "region": {"name": "Provence"},
        "municipalities": [
            {"name": "Marseille", "latitude": 43.2965, "longitude": 5.3698},
            {"name": "Nice", "latitude": 43.7102, "longitude": 7.2620},
        ]
    },
    {
        "country": {"name": "Germany", "code": "DEU"},
        "region": {"name": "Bavaria"},
        "municipalities": [
            {"name": "Munich", "latitude": 48.1351, "longitude": 11.5820},
            {"name": "Nuremberg", "latitude": 49.4521, "longitude": 11.0767},
        ]
    },
    {
        "country": {"name": "Italy", "code": "ITA"},
        "region": {"name": "Tuscany"},
        "municipalities": [
            {"name": "Florence", "latitude": 43.7696, "longitude": 11.2558},
            {"name": "Siena", "latitude": 43.3188, "longitude": 11.3308},
        ]
    }
]

LOCATION_TYPES = [
    "Town Hall", "Fire Station", "Bakery", "Church",
    "Market Square", "Fountain", "Bridge", "Park"
]

CATEGORY_ASSIGNMENT = {
    "Town Hall": 2,      # Premium
    "Fire Station": 1,   # Plus
    "Bakery": 0,         # Standard
    "Church": 1,         # Plus
    "Market Square": 0,  # Standard
    "Fountain": 0,       # Standard
    "Bridge": 1,         # Plus
    "Park": 0            # Standard
}

CATEGORY_NAMES = ["standard", "plus", "premium"]


# ============================================================
# STEP 1: GENERATE PLACEHOLDER IMAGES
# ============================================================

def generate_placeholder(municipality, location_type, category, width=1024, height=1024):
    """Generate a placeholder flag image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install Pillow")
        sys.exit(1)

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
    draw.rectangle([20, 20, width - 20, height - 20], outline=accent_color, width=10)

    # Center shield
    cx, cy = width // 2, height // 2
    shield_points = [
        (cx - 150, cy - 180), (cx + 150, cy - 180),
        (cx + 150, cy + 50), (cx, cy + 180), (cx - 150, cy + 50),
    ]
    draw.polygon(shield_points, fill=accent_color, outline=(255, 255, 255), width=5)

    # Location icon
    icon_color = bg_color
    if location_type == "Town Hall":
        draw.rectangle([cx-80, cy-80, cx+80, cy+60], fill=icon_color)
        draw.polygon([(cx-100, cy-80), (cx, cy-150), (cx+100, cy-80)], fill=icon_color)
    elif location_type == "Church":
        draw.rectangle([cx-15, cy-100, cx+15, cy+80], fill=icon_color)
        draw.rectangle([cx-60, cy-50, cx+60, cy-20], fill=icon_color)
    elif location_type == "Fire Station":
        draw.ellipse([cx-50, cy-80, cx+50, cy+60], fill=(255, 100, 50))
    elif location_type == "Bridge":
        draw.arc([cx-100, cy-50, cx+100, cy+100], 0, 180, fill=icon_color, width=20)
    elif location_type == "Fountain":
        draw.ellipse([cx-60, cy-40, cx+60, cy+60], fill=(100, 149, 237))
    elif location_type == "Park":
        draw.ellipse([cx-50, cy-100, cx+50, cy], fill=(34, 139, 34))
        draw.rectangle([cx-15, cy, cx+15, cy+80], fill=(139, 69, 19))
    elif location_type == "Market Square":
        for i in range(-2, 3):
            for j in range(-2, 3):
                if (i + j) % 2 == 0:
                    draw.rectangle([cx+i*30-10, cy+j*30-10, cx+i*30+10, cy+j*30+10], fill=icon_color)
    else:
        draw.ellipse([cx-50, cy-50, cx+50, cy+50], fill=icon_color)

    # Text
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except:
        font_large = ImageFont.load_default()
        font_small = font_large

    # Municipality name
    text = municipality.upper()
    bbox = draw.textbbox((0, 0), text, font=font_large)
    draw.text(((width - (bbox[2] - bbox[0])) // 2, 50), text, fill=(255, 255, 255), font=font_large)

    # Location type
    text2 = location_type.upper()
    bbox2 = draw.textbbox((0, 0), text2, font=font_small)
    draw.text(((width - (bbox2[2] - bbox2[0])) // 2, height - 80), text2, fill=(255, 255, 255), font=font_small)

    # Category badge
    cat_text = ["STANDARD", "PLUS", "PREMIUM"][category]
    draw.rectangle([width - 150, 30, width - 30, 70], fill=accent_color)
    draw.text((width - 140, 38), cat_text, fill=(0, 0, 0), font=font_small)

    # Return bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def generate_all_images():
    """Generate all flag images."""
    print("\n" + "=" * 60)
    print("STEP 1: Generating Flag Images")
    print("=" * 60)

    flag_id = 0
    generated = 0
    skipped = 0
    all_flags = []

    for country_data in MUNICIPALITIES_DATA:
        country = country_data["country"]
        region = country_data["region"]

        for municipality in country_data["municipalities"]:
            base_lat = municipality["latitude"]
            base_lon = municipality["longitude"]

            for i, location_type in enumerate(LOCATION_TYPES):
                flag_id += 1
                category = CATEGORY_ASSIGNMENT.get(location_type, 0)

                # Offset coordinates slightly for each location
                lat = round(base_lat + (i * 0.003), 6)
                lon = round(base_lon + (i * 0.003), 6)

                filename = f"{country['code']}_{municipality['name'].lower()}_{flag_id:03d}.png"
                output_path = OUTPUT_DIR / filename

                flag_info = {
                    "id": flag_id,
                    "filename": filename,
                    "country": country["name"],
                    "country_code": country["code"],
                    "region": region["name"],
                    "municipality": municipality["name"],
                    "location_type": location_type,
                    "category": CATEGORY_NAMES[category],
                    "latitude": lat,
                    "longitude": lon,
                    "image_ipfs_hash": None,
                    "metadata_ipfs_hash": None
                }

                if output_path.exists():
                    skipped += 1
                    print(f"  [{flag_id}] {municipality['name']} - {location_type}: Skipped (exists)")
                else:
                    image_data = generate_placeholder(municipality["name"], location_type, category)
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                    generated += 1
                    print(f"  [{flag_id}] {municipality['name']} - {location_type}: Generated")

                all_flags.append(flag_info)

    print(f"\n  Generated: {generated}, Skipped: {skipped}, Total: {len(all_flags)}")
    return all_flags


# ============================================================
# STEP 2: UPLOAD TO PINATA IPFS
# ============================================================

class PinataUploader:
    def __init__(self):
        self.base_url = "https://api.pinata.cloud"

        if not PINATA_JWT and not (PINATA_API_KEY and PINATA_API_SECRET):
            raise ValueError("Missing Pinata credentials in .env")

    def _headers(self, for_upload=False):
        if PINATA_JWT:
            headers = {"Authorization": f"Bearer {PINATA_JWT}"}
        else:
            headers = {
                "pinata_api_key": PINATA_API_KEY,
                "pinata_secret_api_key": PINATA_API_SECRET
            }
        if not for_upload:
            headers["Content-Type"] = "application/json"
        return headers

    def test_auth(self):
        try:
            r = requests.get(f"{self.base_url}/data/testAuthentication", headers=self._headers())
            return r.status_code == 200
        except:
            return False

    def upload_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                r = requests.post(
                    f"{self.base_url}/pinning/pinFileToIPFS",
                    files={'file': (file_path.name, f)},
                    headers=self._headers(for_upload=True)
                )
                if r.status_code == 200:
                    return r.json()["IpfsHash"]
        except:
            pass
        return None

    def upload_json(self, data, name):
        try:
            r = requests.post(
                f"{self.base_url}/pinning/pinJSONToIPFS",
                json={"pinataContent": data, "pinataMetadata": {"name": name}},
                headers=self._headers()
            )
            if r.status_code == 200:
                return r.json()["IpfsHash"]
        except:
            pass
        return None


def upload_to_ipfs(all_flags):
    """Upload all images and metadata to IPFS."""
    print("\n" + "=" * 60)
    print("STEP 2: Uploading to Pinata IPFS")
    print("=" * 60)

    # Check credentials
    if not PINATA_JWT and not PINATA_API_KEY:
        print("  WARNING: No Pinata credentials found in .env")
        print("  Skipping IPFS upload. Add PINATA_JWT or PINATA_API_KEY to .env")
        return all_flags

    try:
        uploader = PinataUploader()
        if not uploader.test_auth():
            print("  ERROR: Pinata authentication failed!")
            return all_flags
        print("  Pinata authenticated successfully\n")
    except Exception as e:
        print(f"  ERROR: {e}")
        return all_flags

    uploaded = 0
    for flag in all_flags:
        image_path = OUTPUT_DIR / flag["filename"]

        if not image_path.exists():
            print(f"  [{flag['id']}] Missing image: {flag['filename']}")
            continue

        # Upload image
        print(f"  [{flag['id']}] Uploading {flag['filename']}...", end=" ", flush=True)
        image_hash = uploader.upload_file(image_path)

        if not image_hash:
            print("FAILED")
            continue

        flag["image_ipfs_hash"] = image_hash

        # Create and upload metadata
        metadata = {
            "name": f"Flag of {flag['municipality']} - {flag['location_type']}",
            "description": f"{flag['location_type']} flag of {flag['municipality']}, {flag['region']}, {flag['country']}. Part of the Municipal Flag NFT collection.",
            "image": f"ipfs://{image_hash}",
            "external_url": f"https://municipalflagnft.demo/{flag['id']}",
            "attributes": [
                {"trait_type": "Country", "value": flag["country"]},
                {"trait_type": "Country Code", "value": flag["country_code"]},
                {"trait_type": "Region", "value": flag["region"]},
                {"trait_type": "Municipality", "value": flag["municipality"]},
                {"trait_type": "Location Type", "value": flag["location_type"]},
                {"trait_type": "Category", "value": flag["category"].title()},
                {"trait_type": "Latitude", "value": flag["latitude"]},
                {"trait_type": "Longitude", "value": flag["longitude"]},
                {"display_type": "number", "trait_type": "Flag ID", "value": flag["id"]}
            ]
        }

        metadata_hash = uploader.upload_json(metadata, f"flag_{flag['id']}_metadata.json")
        if metadata_hash:
            flag["metadata_ipfs_hash"] = metadata_hash
            uploaded += 1
            print(f"OK -> {image_hash[:12]}...")
        else:
            print("Metadata failed")

    print(f"\n  Uploaded: {uploaded}/{len(all_flags)}")
    return all_flags


# ============================================================
# STEP 3: UPDATE METADATA JSON FILES
# ============================================================

def update_metadata_files(all_flags):
    """Update metadata JSON files with IPFS hashes."""
    print("\n" + "=" * 60)
    print("STEP 3: Updating Metadata JSON Files")
    print("=" * 60)

    for flag in all_flags:
        metadata_path = METADATA_DIR / f"{flag['id']}.json"

        metadata = {
            "name": f"Flag of {flag['municipality']} - {flag['location_type']}",
            "description": f"{flag['location_type']} flag of {flag['municipality']}, {flag['region']}, {flag['country']}. Part of the Municipal Flag NFT collection.",
            "image": f"ipfs://{flag['image_ipfs_hash']}" if flag['image_ipfs_hash'] else "",
            "external_url": f"https://municipalflagnft.demo/{flag['id']}",
            "attributes": [
                {"trait_type": "Country", "value": flag["country"]},
                {"trait_type": "Country Code", "value": flag["country_code"]},
                {"trait_type": "Region", "value": flag["region"]},
                {"trait_type": "Municipality", "value": flag["municipality"]},
                {"trait_type": "Location Type", "value": flag["location_type"]},
                {"trait_type": "Category", "value": flag["category"].title()},
                {"trait_type": "Latitude", "value": flag["latitude"]},
                {"trait_type": "Longitude", "value": flag["longitude"]},
                {"display_type": "number", "trait_type": "Flag ID", "value": flag["id"]}
            ]
        }

        # Add IPFS hashes if available
        if flag["image_ipfs_hash"]:
            metadata["image_ipfs_hash"] = flag["image_ipfs_hash"]
        if flag["metadata_ipfs_hash"]:
            metadata["metadata_ipfs_hash"] = flag["metadata_ipfs_hash"]

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    print(f"  Updated {len(all_flags)} metadata files in {METADATA_DIR}")


# ============================================================
# STEP 4: SEED BACKEND DATABASE
# ============================================================

def seed_backend_database(all_flags):
    """Seed the backend database via API."""
    print("\n" + "=" * 60)
    print("STEP 4: Seeding Backend Database")
    print("=" * 60)

    # First, try the admin seed endpoint
    print(f"  Calling {BACKEND_URL}/api/admin/seed ...")

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/admin/seed",
            headers={"X-Admin-Key": ADMIN_KEY},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            print(f"  Database seeded successfully!")
            print(f"    Countries: {data.get('countries_created', 'N/A')}")
            print(f"    Regions: {data.get('regions_created', 'N/A')}")
            print(f"    Municipalities: {data.get('municipalities_created', 'N/A')}")
            print(f"    Flags: {data.get('flags_created', 'N/A')}")
        else:
            print(f"  Seed endpoint returned: {response.status_code}")
            print(f"  Response: {response.text[:200]}")

    except requests.exceptions.ConnectionError:
        print(f"  ERROR: Cannot connect to backend at {BACKEND_URL}")
        print(f"  Make sure backend is running: cd ../backend && python main.py")
        return
    except Exception as e:
        print(f"  ERROR: {e}")
        return

    # Now update flags with IPFS hashes
    flags_with_ipfs = [f for f in all_flags if f.get("image_ipfs_hash")]

    if not flags_with_ipfs:
        print("\n  No IPFS hashes to update (Pinata not configured)")
        return

    print(f"\n  Updating {len(flags_with_ipfs)} flags with IPFS hashes...")

    updated = 0
    for flag in flags_with_ipfs:
        try:
            # Update flag via API - parameters are query params, not JSON body
            response = requests.patch(
                f"{BACKEND_URL}/api/admin/flags/{flag['id']}/ipfs",
                params={
                    "image_ipfs_hash": flag["image_ipfs_hash"],
                    "metadata_ipfs_hash": flag["metadata_ipfs_hash"]
                },
                headers={"X-Admin-Key": ADMIN_KEY},
                timeout=10
            )

            if response.status_code == 200:
                updated += 1
            else:
                print(f"    Flag {flag['id']}: {response.status_code} - {response.text[:100]}")

        except Exception as e:
            print(f"    Flag {flag['id']}: Error - {e}")

    print(f"  Updated {updated}/{len(flags_with_ipfs)} flags with IPFS hashes")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  Municipal Flag NFT - ALL-IN-ONE Setup")
    print("=" * 60)
    print("\nThis script will:")
    print("  1. Generate 64 flag placeholder images")
    print("  2. Upload images to Pinata IPFS (if configured)")
    print("  3. Update metadata JSON files")
    print("  4. Seed backend database")
    print()

    # Step 1: Generate images
    all_flags = generate_all_images()

    # Step 2: Upload to IPFS
    all_flags = upload_to_ipfs(all_flags)

    # Step 3: Update metadata files
    update_metadata_files(all_flags)

    # Step 4: Seed database
    seed_backend_database(all_flags)

    # Done
    print("\n" + "=" * 60)
    print("  ALL DONE!")
    print("=" * 60)
    print(f"\n  Images:   {OUTPUT_DIR}")
    print(f"  Metadata: {METADATA_DIR}")
    print(f"  Backend:  {BACKEND_URL}")
    print()


if __name__ == "__main__":
    main()
