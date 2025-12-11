"""
Configuration for AI Image Generation.
Loads settings from the centralized .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
ROOT_DIR = Path(__file__).parent.parent
ENV_FILE = ROOT_DIR / ".env"
load_dotenv(ENV_FILE)


class Config:
    """Configuration class for AI generator."""

    # Paths
    ROOT_DIR = ROOT_DIR
    OUTPUT_DIR = Path(__file__).parent / "output"
    METADATA_DIR = Path(__file__).parent / "metadata"

    # AI Generation settings
    SD_LOCAL_ENABLED = os.getenv("SD_LOCAL_ENABLED", "false").lower() == "true"
    SD_MODEL_PATH = os.getenv("SD_MODEL_PATH", "stabilityai/stable-diffusion-2-1")
    SD_USE_CLOUD_API = os.getenv("SD_USE_CLOUD_API", "true").lower() == "true"

    # API Keys
    REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
    STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")

    # Image settings
    IMAGE_WIDTH = int(os.getenv("SD_IMAGE_WIDTH", "512"))
    IMAGE_HEIGHT = int(os.getenv("SD_IMAGE_HEIGHT", "512"))
    NUM_INFERENCE_STEPS = int(os.getenv("SD_NUM_INFERENCE_STEPS", "50"))
    GUIDANCE_SCALE = float(os.getenv("SD_GUIDANCE_SCALE", "7.5"))

    # Game settings
    FLAGS_PER_MUNICIPALITY = int(os.getenv("FLAGS_PER_MUNICIPALITY", "8"))

    @classmethod
    def ensure_directories(cls):
        """Create output directories if they don't exist."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.METADATA_DIR.mkdir(parents=True, exist_ok=True)


# Municipality data for generation
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

# Location types for flags
LOCATION_TYPES = [
    "Town Hall",
    "Fire Station",
    "Bakery",
    "Church",
    "Market Square",
    "Fountain",
    "Bridge",
    "Park"
]

# Categories assignment (index matches LOCATION_TYPES)
# 0=Standard, 1=Plus, 2=Premium
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
