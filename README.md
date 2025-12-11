# Municipal Flag NFT Game

A functional demonstration of a web game based on NFTs, where players collect flags of real municipalities grouped by country and region. Each flag is an AI-generated NFT with pair acquisition mechanics and social features.

## Project Structure

```
municipal-flag-nft/
├── backend/           # FastAPI Python backend
├── frontend/          # React frontend
├── contracts/         # Hardhat smart contracts
├── ai-generator/      # Stable Diffusion image generation
├── docs/              # Documentation
└── .env.example       # Centralized configuration template
```

## Quick Start

### 1. Setup Environment

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration (API keys, wallet private key, etc.)

### 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed_data.py       # Seed demo data
python main.py            # Start server at http://localhost:8000
```

### 3. Smart Contracts Setup

```bash
cd contracts
npm install
npx hardhat compile
npx hardhat test
npx hardhat run scripts/deploy.js --network amoy  # Deploy to Polygon Amoy
```

### 4. Frontend Setup

```bash
cd frontend
npm install
npm start                 # Start at http://localhost:3000
```

### 5. Generate Images (Optional)

```bash
cd ai-generator
pip install -r requirements.txt
python generate_flags.py    # Generate flag images
python upload_to_ipfs.py    # Upload to IPFS via Pinata
```

## Configuration

All settings are centralized in the root `.env` file:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLite connection string |
| `ADMIN_API_KEY` | Admin panel authentication |
| `DEPLOYER_PRIVATE_KEY` | Wallet for contract deployment |
| `CONTRACT_ADDRESS` | Deployed contract address |
| `PINATA_API_KEY` | IPFS upload via Pinata |
| `REPLICATE_API_TOKEN` | AI image generation |

## Features

- **Geographic Navigation**: Country > Region > Municipality > Flags
- **NFT Pair System**: Claim first NFT free, purchase second to complete
- **Categories**: Standard, Plus (50% discount), Premium (75% discount)
- **Social Features**: Interest tracking, rankings, off-chain auctions
- **Admin Panel**: Manage countries, regions, municipalities, flags
- **MetaMask Integration**: Connect wallet, claim and purchase NFTs

## Tech Stack

- **Frontend**: React, ethers.js, React Router
- **Backend**: FastAPI (Python), SQLAlchemy, SQLite
- **Smart Contracts**: Solidity, Hardhat, OpenZeppelin ERC-721
- **Blockchain**: Polygon Amoy Testnet
- **Storage**: IPFS (Pinata)
- **AI**: Stable Diffusion (local or cloud API)

## API Endpoints

- `GET /api/countries` - List countries
- `GET /api/regions` - List regions
- `GET /api/municipalities` - List municipalities
- `GET /api/flags` - List flags
- `POST /api/flags/{id}/interest` - Register interest
- `POST /api/flags/{id}/claim` - Record first NFT claim
- `POST /api/flags/{id}/purchase` - Record second NFT purchase
- `GET /api/rankings/*` - Leaderboards
- `GET /api/admin/stats` - Admin statistics

## Smart Contract Functions

- `registerFlag(flagId, category, price)` - Admin: Register new flag
- `claimFirstNFT(flagId)` - Claim first NFT (free)
- `purchaseSecondNFT(flagId)` - Purchase second NFT (payable)
- `getPriceWithDiscount(flagId, buyer)` - Get discounted price

## Demo Data

The demo includes:
- 4 Countries (Spain, France, Germany, Italy)
- 4 Regions (one per country)
- 8 Municipalities (two per region)
- 64 Flags (eight per municipality)

## Testing

```bash
# Backend
cd backend && python -m pytest

# Smart Contracts
cd contracts && npx hardhat test

# Frontend
cd frontend && npm test
```

## License

Private - All rights reserved.

---

Built with Hardhat, FastAPI, and React.
