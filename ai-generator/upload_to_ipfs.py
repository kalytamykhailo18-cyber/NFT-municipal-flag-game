"""
IPFS Upload Script for Municipal Flag NFT Game.

Simple, clean script that:
1. Uploads images from output/ folder to IPFS via Pinata
2. Updates database with IPFS hashes

No complicated imports or path juggling.
"""
import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, Optional, List
from tqdm import tqdm
from dotenv import load_dotenv

# ============================================================
# CONFIGURATION
# ============================================================

# Setup paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = SCRIPT_DIR / "output"
METADATA_DIR = SCRIPT_DIR / "metadata"

# Load environment
load_dotenv(ROOT_DIR / ".env")

# Pinata credentials
PINATA_JWT = os.getenv("PINATA_JWT", "")
PINATA_API_KEY = os.getenv("PINATA_API_KEY", "")
PINATA_API_SECRET = os.getenv("PINATA_API_SECRET", "")


# ============================================================
# PINATA UPLOADER
# ============================================================

class PinataUploader:
    """Simple IPFS uploader using Pinata."""

    def __init__(self):
        self.base_url = "https://api.pinata.cloud"

        if not PINATA_JWT and not (PINATA_API_KEY and PINATA_API_SECRET):
            raise ValueError(
                "Missing Pinata credentials. Set PINATA_JWT or "
                "(PINATA_API_KEY + PINATA_API_SECRET) in .env"
            )

    def _headers(self, for_upload: bool = False) -> Dict[str, str]:
        """Get request headers."""
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

    def test_auth(self) -> bool:
        """Test if credentials are valid."""
        try:
            response = requests.get(
                f"{self.base_url}/data/testAuthentication",
                headers=self._headers()
            )
            return response.status_code == 200
        except:
            return False

    def upload_file(self, file_path: Path) -> Optional[str]:
        """Upload a file to IPFS. Returns IPFS hash or None."""
        if not file_path.exists():
            return None

        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f)}

                response = requests.post(
                    f"{self.base_url}/pinning/pinFileToIPFS",
                    files=files,
                    headers=self._headers(for_upload=True)
                )

                if response.status_code == 200:
                    return response.json()["IpfsHash"]
                else:
                    return None
        except:
            return None

    def upload_json(self, data: Dict, name: str) -> Optional[str]:
        """Upload JSON to IPFS. Returns IPFS hash or None."""
        try:
            payload = {
                "pinataContent": data,
                "pinataMetadata": {"name": name}
            }

            response = requests.post(
                f"{self.base_url}/pinning/pinJSONToIPFS",
                json=payload,
                headers=self._headers()
            )

            if response.status_code == 200:
                return response.json()["IpfsHash"]
            else:
                return None
        except:
            return None


# ============================================================
# DATABASE ACCESS (ISOLATED)
# ============================================================

def get_database_connection():
    """Get database connection. Import here to avoid conflicts."""
    # Add backend to path
    backend_path = str(ROOT_DIR / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    # Change to backend directory so database is created there
    import os
    original_dir = os.getcwd()
    os.chdir(ROOT_DIR / "backend")

    try:
        # Import database modules
        from database import SessionLocal, init_db
        from models import Flag, Municipality, Region, Country

        # Initialize and return
        init_db()
        return SessionLocal(), Flag, Municipality, Region, Country
    finally:
        # Change back to original directory
        os.chdir(original_dir)


def get_flags_from_db() -> List[Dict]:
    """Get all flags from database."""
    db, Flag, Municipality, Region, Country = get_database_connection()

    try:
        flags = db.query(Flag).join(
            Municipality
        ).join(
            Region
        ).join(
            Country
        ).all()

        result = []
        for flag in flags:
            muni = flag.municipality
            region = muni.region
            country = region.country

            # Image filename pattern: CODE_municipality_ID.png
            filename = f"{country.code}_{muni.name.lower()}_{flag.id:03d}.png"

            result.append({
                "flag_id": flag.id,
                "flag": flag,
                "filename": filename,
                "country": country.name,
                "region": region.name,
                "municipality": muni.name,
                "location": flag.location_type
            })

        return result
    finally:
        db.close()


def update_flag_hashes(flag_id: int, image_hash: str, metadata_hash: str) -> bool:
    """Update a flag's IPFS hashes in database."""
    db, Flag, _, _, _ = get_database_connection()

    try:
        flag = db.query(Flag).filter(Flag.id == flag_id).first()
        if flag:
            flag.image_ipfs_hash = image_hash
            flag.metadata_ipfs_hash = metadata_hash
            db.commit()
            return True
        return False
    finally:
        db.close()


# ============================================================
# MAIN UPLOAD LOGIC
# ============================================================

def upload_all(force: bool = False):
    """
    Upload all images to IPFS and update database.

    Args:
        force: If True, re-upload even if IPFS hashes exist
    """
    print("=" * 60)
    print("Municipal Flag NFT - IPFS Upload")
    print("=" * 60)

    if force:
        print("FORCE MODE: Re-uploading all images\n")

    # Test Pinata
    print("Testing Pinata credentials...")
    uploader = PinataUploader()
    if not uploader.test_auth():
        print("ERROR: Pinata authentication failed!")
        return
    print("✓ Pinata authenticated\n")

    # Get flags from database
    print("Loading flags from database...")
    flags = get_flags_from_db()

    if not flags:
        print("ERROR: No flags in database!")
        print("Run: curl -X POST http://localhost:8000/api/admin/seed -H 'X-Admin-Key: YOUR_KEY'")
        return

    print(f"✓ Found {len(flags)} flags\n")

    # Upload
    print("Uploading to IPFS...")
    print("-" * 60)

    uploaded = 0
    skipped = 0
    failed = 0

    for item in tqdm(flags, desc="Processing"):
        flag = item["flag"]

        # Skip if already uploaded (unless force mode)
        if not force and flag.image_ipfs_hash and flag.metadata_ipfs_hash:
            skipped += 1
            continue

        # Check if image file exists
        image_path = OUTPUT_DIR / item["filename"]
        if not image_path.exists():
            tqdm.write(f"  ✗ Missing: {item['filename']}")
            failed += 1
            continue

        # Upload image
        image_hash = uploader.upload_file(image_path)
        if not image_hash:
            tqdm.write(f"  ✗ Upload failed: {item['filename']}")
            failed += 1
            continue

        # Create metadata
        metadata = {
            "name": f"Flag at {flag.name}",
            "description": f"{flag.location_type} flag of {item['municipality']}, {item['region']}, {item['country']}",
            "image": f"ipfs://{image_hash}",
            "attributes": [
                {"trait_type": "Country", "value": item['country']},
                {"trait_type": "Region", "value": item['region']},
                {"trait_type": "Municipality", "value": item['municipality']},
                {"trait_type": "Location", "value": item['location']},
                {"trait_type": "Category", "value": flag.category.value.title()},
                {"trait_type": "Flag ID", "value": flag.id}
            ]
        }

        # Upload metadata
        metadata_hash = uploader.upload_json(metadata, f"flag_{flag.id}_metadata.json")
        if not metadata_hash:
            tqdm.write(f"  ✗ Metadata upload failed: {item['filename']}")
            failed += 1
            continue

        # Update database
        if update_flag_hashes(flag.id, image_hash, metadata_hash):
            uploaded += 1
            tqdm.write(f"  ✓ {item['filename']} -> {image_hash[:12]}...")
        else:
            tqdm.write(f"  ✗ DB update failed: {item['filename']}")
            failed += 1

    # Summary
    print("-" * 60)
    print("\n" + "=" * 60)
    print("UPLOAD COMPLETE")
    print("=" * 60)
    print(f"  Uploaded: {uploaded}")
    print(f"  Skipped:  {skipped}")
    print(f"  Failed:   {failed}")
    print(f"  Total:    {len(flags)}")
    print()


def show_status():
    """Show current upload status."""
    print("=" * 60)
    print("IPFS Upload Status")
    print("=" * 60)

    flags = get_flags_from_db()

    with_hashes = sum(1 for f in flags if f["flag"].image_ipfs_hash)
    without = len(flags) - with_hashes

    print(f"\nTotal flags:      {len(flags)}")
    print(f"Uploaded:         {with_hashes}")
    print(f"Pending upload:   {without}")
    print()


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "--force":
            upload_all(force=True)
        elif cmd == "--status":
            show_status()
        elif cmd == "--help":
            print("Usage: python upload_to_ipfs.py [OPTIONS]")
            print()
            print("Options:")
            print("  (none)    Upload flags without IPFS hashes")
            print("  --force   Re-upload ALL flags (overwrite existing)")
            print("  --status  Show upload status")
            print("  --help    Show this help")
        else:
            print(f"Unknown option: {cmd}")
            print("Run: python upload_to_ipfs.py --help")
    else:
        upload_all(force=False)
