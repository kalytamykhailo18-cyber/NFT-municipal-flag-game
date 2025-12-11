# Municipal Flag NFT Game

A functional demonstration of a web game based on NFTs where players collect flags of real municipalities grouped by country and region. Each flag is an AI-generated NFT with a dual-NFT pair acquisition mechanic and social features including auctions, rankings, and player interaction.

## Key Features

- **Geographic Navigation**: Country > Region > Municipality > Flags hierarchy
- **Dual-NFT Pair System**: Each flag has two NFTs - claim first free, purchase second to complete
- **Multi-NFT Flags**: Premium flags require 3 NFTs to complete (configurable 1-10)
- **Category Discounts**:
  - Standard: No discount
  - Plus: 50% discount on future Standard purchases
  - Premium: 75% permanent discount on Standard purchases
- **Off-Chain Auctions**: Buyout price, minimum price, category-based tie-breaking
- **Social Features**: Interest tracking, rankings, player connections
- **AI Image Generation**: Stable Diffusion via Replicate API
- **Coordinate-to-NFT**: Generate NFTs from Google Street View coordinates
- **IPFS Storage**: Images and metadata stored on IPFS via Pinata
- **SHA-256 Integrity**: Metadata hash verification

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React 18, Vite, Redux Toolkit, ethers.js 6, TailwindCSS |
| Backend | Python 3.10+, FastAPI, SQLAlchemy, SQLite/PostgreSQL |
| Smart Contracts | Solidity 0.8.20, Hardhat, OpenZeppelin 5.0 |
| Blockchain | Polygon Amoy Testnet (Chain ID: 80002) |
| Storage | IPFS (Pinata) |
| AI | Stable Diffusion (Replicate API) |

## Project Structure

```
municipal-flag-nft/
├── contracts/                 # Solidity smart contracts
│   ├── contracts/
│   │   └── MunicipalFlagNFT.sol    # Main ERC-721 contract
│   ├── scripts/
│   │   ├── deploy.js               # Deployment script
│   │   └── register-flags.js       # Flag registration script
│   ├── test/
│   │   └── MunicipalFlagNFT.test.js # 58 test cases
│   ├── hardhat.config.js
│   └── package.json
│
├── backend/                   # FastAPI Python backend
│   ├── routers/
│   │   ├── admin.py           # Admin endpoints + NFT generation
│   │   ├── auctions.py        # Auction system with buyout
│   │   ├── countries.py
│   │   ├── regions.py
│   │   ├── municipalities.py
│   │   ├── flags.py
│   │   ├── users.py
│   │   └── rankings.py
│   ├── services/
│   │   ├── google_maps.py     # Street View API
│   │   ├── ai.py              # Replicate AI integration
│   │   └── ipfs.py            # Pinata IPFS + SHA-256
│   ├── main.py                # FastAPI entry point
│   ├── models.py              # SQLAlchemy models
│   ├── schemas.py             # Pydantic schemas
│   ├── config.py              # Configuration
│   ├── seed_data.py           # Demo data seeder
│   └── requirements.txt
│
├── frontend/                  # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── Loading.jsx
│   │   │   └── FlagCard.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Countries.jsx
│   │   │   ├── CountryDetail.jsx
│   │   │   ├── RegionDetail.jsx
│   │   │   ├── MunicipalityDetail.jsx
│   │   │   ├── FlagDetail.jsx
│   │   │   ├── Profile.jsx
│   │   │   ├── Auctions.jsx
│   │   │   ├── AuctionDetail.jsx
│   │   │   ├── Rankings.jsx
│   │   │   └── Admin.jsx
│   │   ├── store/slices/
│   │   │   ├── walletSlice.js
│   │   │   ├── countriesSlice.js
│   │   │   ├── flagsSlice.js
│   │   │   ├── auctionsSlice.js
│   │   │   ├── adminSlice.js
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── api.js         # Backend API client
│   │   │   └── web3.js        # Blockchain interaction
│   │   └── contracts/
│   │       └── MunicipalFlagNFT.json  # Contract ABI
│   └── package.json
│
├── ai-generator/              # Standalone image generator
│   ├── generate_flags.py      # Image generation
│   ├── upload_to_ipfs.py      # IPFS upload
│   ├── config.py              # Configuration
│   └── requirements.txt
│
├── .env.example               # Environment template
├── COMPLETE_SETUP_GUIDE.txt   # Detailed setup instructions
└── README.md
```

## Quick Start

### Prerequisites

- Node.js v18+
- Python 3.10+
- MetaMask browser extension
- Polygon Amoy testnet POL (from [faucet](https://faucet.polygon.technology/))

### 1. Environment Setup

```bash
# Clone and setup
cp .env.example .env
# Edit .env with your API keys and private key
```

### 2. Smart Contracts

```bash
cd contracts
npm install
npx hardhat compile
npx hardhat test                                    # Run 58 tests
npx hardhat run scripts/deploy.js --network amoy   # Deploy to testnet
# Save CONTRACT_ADDRESS from output to .env
npx hardhat run scripts/register-flags.js --network amoy  # Register flags
```

### 3. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
python main.py                 # Starts at http://localhost:8000
```

The database auto-seeds with demo data on first startup.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev                    # Starts at http://localhost:5173
```

## Environment Variables

Create `.env` in project root:

```env
# Backend
DATABASE_URL=sqlite:///./nft_game.db
ADMIN_API_KEY=your-admin-key
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Blockchain
DEPLOYER_PRIVATE_KEY=your-wallet-private-key
POLYGON_AMOY_RPC_URL=https://rpc-amoy.polygon.technology
CONTRACT_ADDRESS=0x...

# IPFS (Pinata)
PINATA_API_KEY=your-key
PINATA_API_SECRET=your-secret
PINATA_JWT=your-jwt

# AI (Replicate)
REPLICATE_API_TOKEN=your-token

# Google Maps (for coordinate-to-NFT)
GOOGLE_MAPS_API_KEY=your-key

# Game Settings
DEFAULT_STANDARD_PRICE=0.01
DEFAULT_PLUS_PRICE=0.02
DEFAULT_PREMIUM_PRICE=0.05
```

## Smart Contract Functions

### Admin Functions (Owner Only)

| Function | Description |
|----------|-------------|
| `registerFlag(flagId, category, price, nftsRequired)` | Register flag with multi-NFT support |
| `registerFlagSimple(flagId, category, price)` | Register flag (nftsRequired=1) |
| `batchRegisterFlags(ids[], categories[], prices[], nftsRequired[])` | Batch register |
| `setMetadataHash(flagId, hash)` | Set SHA-256 metadata hash |
| `setBaseURI(uri)` | Update IPFS gateway |
| `withdraw()` | Withdraw contract balance |

### Public Functions

| Function | Description |
|----------|-------------|
| `claimFirstNFT(flagId)` | Claim first NFT(s) for free |
| `purchaseSecondNFT(flagId)` | Purchase second NFT(s) to complete pair |

### View Functions

| Function | Description |
|----------|-------------|
| `getFlagPair(flagId)` | Get complete flag data |
| `getPriceWithDiscount(flagId, buyer)` | Get discounted price per NFT |
| `getTotalPriceWithDiscount(flagId, buyer)` | Get total price (price * nftsRequired) |
| `getNftsRequired(flagId)` | Get NFTs needed for flag |
| `getTotalRegisteredFlags()` | Total flags registered |
| `isFlagRegistered(flagId)` | Check if flag exists |
| `hasPlus(address)` | Check Plus discount status |
| `hasPremium(address)` | Check Premium discount status |

## API Endpoints

### Public Endpoints

```
GET  /api/countries              # List all countries
GET  /api/countries/{id}         # Get country with regions
GET  /api/regions                # List all regions
GET  /api/regions/{id}           # Get region with municipalities
GET  /api/municipalities         # List all municipalities
GET  /api/municipalities/{id}    # Get municipality with flags
GET  /api/flags                  # List all flags
GET  /api/flags/{id}             # Get flag details
POST /api/flags/{id}/interest    # Register interest in flag
POST /api/flags/{id}/claim       # Record first NFT claim
POST /api/flags/{id}/purchase    # Record second NFT purchase

GET  /api/users/{wallet}         # Get user profile
GET  /api/rankings/collectors    # Top collectors
GET  /api/rankings/municipalities # Most popular municipalities

GET  /api/auctions               # List auctions
GET  /api/auctions/{id}          # Get auction details
POST /api/auctions               # Create auction
POST /api/auctions/{id}/bid      # Place bid
POST /api/auctions/{id}/buyout   # Instant purchase
```

### Admin Endpoints (X-Admin-Key header required)

```
GET  /api/admin/stats            # Dashboard statistics
POST /api/admin/seed             # Seed demo data
POST /api/admin/reset            # Reset database

# CRUD for all entities
POST   /api/admin/countries      # Create country
PUT    /api/admin/countries/{id} # Update country
DELETE /api/admin/countries/{id} # Delete country
# Same pattern for regions, municipalities, flags

# Demo User
POST /api/admin/create-demo-user     # Create demo user
GET  /api/admin/demo-user            # Get demo user
POST /api/admin/seed-demo-ownership  # Seed ownerships
DELETE /api/admin/demo-user          # Delete demo user

# NFT Generation from Coordinates
POST /api/admin/check-street-view       # Validate coordinates
POST /api/admin/nft-from-coordinates    # Full NFT pipeline
```

## Demo Data

The application seeds with:

| Entity | Count | Details |
|--------|-------|---------|
| Countries | 4 | Spain, France, Germany, Italy |
| Regions | 4 | Catalonia, Provence, Bavaria, Tuscany |
| Municipalities | 8 | Barcelona, Girona, Marseille, Nice, Munich, Nuremberg, Florence, Siena |
| Flags | 64 | 8 per municipality |

Flag Categories Distribution:
- **Premium** (Town Hall): 8 flags, require 3 NFTs each
- **Plus** (Fire Station, Church, Bridge): ~16 flags
- **Standard** (Bakery, Market, Fountain, Park): ~40 flags

## Testing

### Smart Contract Tests (58 tests)

```bash
cd contracts
npx hardhat test
```

Test categories:
- Deployment
- Flag Registration (including multi-NFT)
- First NFT Claim (single and multi-NFT)
- Second NFT Purchase (with discount verification)
- Discount System
- Withdrawal
- Metadata Hash
- View Functions
- ERC721 Enumerable

### API Testing

```bash
# Access Swagger UI
http://localhost:8000/docs
```

## MetaMask Setup

1. Install MetaMask extension
2. Add Polygon Amoy network:
   - Network Name: `Polygon Amoy Testnet`
   - RPC URL: `https://rpc-amoy.polygon.technology`
   - Chain ID: `80002`
   - Symbol: `POL`
   - Explorer: `https://amoy.polygonscan.com`
3. Get test POL from [faucet](https://faucet.polygon.technology/)

## Game Flow

```
1. Admin registers flags on smart contract
         |
         v
2. User connects MetaMask wallet
         |
         v
3. User browses: Countries -> Regions -> Municipalities -> Flags
         |
         v
4. User claims first NFT (free, shows interest)
         |
         v
5. User purchases second NFT (pays price x nftsRequired)
         |
         v
6. If Plus/Premium flag: User gets permanent discount
         |
         v
7. User can create auctions or view rankings
```

## Multi-NFT Feature

Some flags require multiple NFTs to complete:

| Category | NFTs Required | Effect |
|----------|---------------|--------|
| Standard | 1 | Basic flag |
| Plus | 1 | Grants 50% discount |
| Premium | 3 | Grants 75% discount |

When claiming/purchasing a multi-NFT flag:
- All NFTs are minted in a single transaction
- Total cost = price per NFT x nftsRequired
- Discount applies to each NFT individually

## Security Features

- **ReentrancyGuard**: Prevents reentrancy attacks on mint/withdraw
- **Custom Errors**: Gas-efficient error handling
- **Admin API Key**: Protects admin endpoints
- **CORS Middleware**: Configurable origin restrictions
- **Input Validation**: Pydantic schemas for all inputs

## Deployment

### Railway (Current)

Backend and frontend are configured for Railway deployment with:
- `Procfile` for backend
- `railway.json` for configuration
- Auto-seeding on startup

### AWS (Alternative)

See `AWS_DEPLOYMENT.md` for:
- EC2/Elastic Beanstalk for backend
- S3 + CloudFront for frontend
- RDS PostgreSQL for database

## Documentation

- `COMPLETE_SETUP_GUIDE.txt` - Step-by-step setup for training/courses
- `AWS_DEPLOYMENT.md` - AWS deployment guide
- `PROJECT_STATUS.md` - Development phase completion status
- `/docs` - API documentation (Swagger UI at http://localhost:8000/docs)

## License

Private - All rights reserved.

---

Built with Hardhat, FastAPI, React, and deployed on Polygon Amoy Testnet.
