# Getting Started with BRICS Pay

Welcome to the BRICS Pay project! This guide will help you set up and start developing on the platform.

## Prerequisites

- **Rust** (1.70 or later) - [Install Rust](https://rustup.rs/)
- **Node.js** (18.x or later) - For API and client applications
- **Git** - Version control

## Project Structure

```
brics-pay/
├── core/                    # Core blockchain protocol
│   ├── crypto/              # Cryptographic primitives
│   ├── ledger/              # Blockchain ledger
│   ├── network/             # P2P networking
│   └── consensus/           # Consensus mechanism
├── api/                     # API services
│   ├── rest/                # RESTful HTTP API
│   ├── graphql/             # GraphQL API
│   └── websocket/           # Real-time updates
├── clients/                 # Client applications
│   ├── web/                 # Web dashboard
│   ├── mobile/              # Mobile apps
│   └── sdk/                 # Developer SDKs
├── contracts/               # Smart contracts
├── tests/                   # Test suites
├── docs/                    # Documentation
└── deployments/             # Deployment configurations
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/brics-pay.git
cd brics-pay
```

### 2. Build Core Components

```bash
# Build cryptographic library
cd core/crypto
cargo build

# Build ledger module
cd ../ledger
cargo build
```

### 3. Run the REST API

```bash
cd api/rest
cargo run
```

The API server will start on `http://localhost:8080`

### 4. Test the API

```bash
# Health check
curl http://localhost:8080/health

# Get account balance
curl http://localhost:8080/api/v1/accounts/ACC123/balance

# Create a transaction
curl -X POST http://localhost:8080/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "from": "sender_account",
    "to": "receiver_account",
    "amount": 1000,
    "currency": "BRL"
  }'
```

## Architecture Overview

### Core Protocol Layer

The core protocol implements:
- **Cryptographic Primitives**: Ed25519 signatures, SHA-256 hashing
- **Blockchain Ledger**: Block structure, validation, storage
- **Consensus**: pBFT-based consensus for transaction finality
- **P2P Network**: Decentralized node communication

### Currency Support

BRICS Pay supports all BRICS national currencies:
- 🇧🇷 BRL - Brazilian Real
- 🇷🇺 RUB - Russian Ruble
- 🇮🇳 INR - Indian Rupee
- 🇨🇳 CNY - Chinese Yuan
- 🇿🇦 ZAR - South African Rand
- 🌐 XBR - Future BRICS Reserve Currency

### Security Features

- End-to-end encryption
- Multi-signature transactions
- Threshold signature schemes
- Hardware Security Module (HSM) support

## Development Workflow

### Running Tests

```bash
# Run all tests
cargo test --workspace

# Run specific module tests
cd core/crypto
cargo test

# Run with coverage
cargo tarpaulin --workspace
```

### Code Style

```bash
# Format code
cargo fmt --workspace

# Lint code
cargo clippy --workspace
```

## Contributing

We welcome contributions from developers worldwide! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Ways to Contribute

1. **Core Development**: Improve protocol, consensus, or cryptography
2. **API Development**: Build and enhance APIs
3. **Client Applications**: Develop web/mobile interfaces
4. **Documentation**: Improve docs and tutorials
5. **Testing**: Write tests and improve coverage
6. **Security Audits**: Help identify vulnerabilities

## Roadmap

### Phase 1 - Foundation (Current)
- [x] Basic cryptographic primitives
- [x] Blockchain ledger structure
- [x] REST API skeleton
- [ ] P2P networking
- [ ] Consensus implementation

### Phase 2 - Advanced Features
- [ ] Smart contract support
- [ ] Cross-chain bridges
- [ ] Mobile applications
- [ ] Merchant gateway

### Phase 3 - Enterprise
- [ ] Central bank integrations
- [ ] Regulatory compliance tools
- [ ] High-frequency trading support
- [ ] Institutional custody

## Community & Support

- **Discord**: [Join our server](#)
- **Twitter**: [@BRICSPay](#)
- **Email**: dev@bricspay.org

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

**Building financial independence for BRICS nations through open-source technology.**
