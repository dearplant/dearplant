# 📄 File: README.md
#
# 🧭 Purpose (Layman Explanation):
# The main instruction manual for our Plant Care app that explains what it does,
# how to set it up, and how other developers can work on it.
#
# 🧪 Purpose (Technical Summary):
# Comprehensive project documentation covering setup, development workflow,
# architecture overview, and contribution guidelines for the Plant Care backend API.
#
# 🔗 Dependencies:
# - Project documentation files
# - Development environment setup
# - API documentation links
#
# 🔄 Connected Modules / Calls From:
# - GitHub repository homepage
# - Developer onboarding process
# - Documentation generation tools

# 🌱 Plant Care Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.3-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat&logo=python)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-316192.svg?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.2+-DC382D.svg?style=flat&logo=redis)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?style=flat&logo=docker)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **AI-Powered Plant Care Management System** - A comprehensive backend API for managing plant collections, care schedules, health monitoring, and community features with intelligent recommendations.

## 🌟 Features

### 🔐 **Admin Management System**
- **Dynamic Configuration**: Change system settings without deployments
- **Multi-language Support**: Real-time content translation management
- **API Provider Control**: Intelligent rotation and fallback systems
- **Real-time Monitoring**: System health and performance dashboards

### 👥 **User Management**
- **Supabase Authentication**: OAuth integration (Google, Apple)
- **Freemium Model**: Dynamic subscription plans and feature access
- **Profile Management**: Customizable user preferences and settings
- **Family Sharing**: Premium feature for household plant management

### 🌿 **Plant Management**
- **AI Plant Identification**: Multi-provider API rotation system
- **Comprehensive Library**: 10,000+ plant species database
- **Personal Collections**: Custom plant tracking and organization
- **Smart Recommendations**: Personalized plant suggestions

### 📅 **Care Management** 
- **Smart Scheduling**: Weather-based care adjustments
- **Multi-channel Reminders**: Push, email, and Telegram notifications
- **Care History**: Photo documentation and progress tracking
- **Seasonal Adaptations**: Climate-aware care modifications

### 🏥 **Health Monitoring**
- **AI Diagnosis**: Photo-based disease and pest identification
- **Treatment Tracking**: Progress monitoring and effectiveness rating
- **Health Analytics**: Trend analysis and predictive insights
- **Expert Consultations**: Premium professional advice system

### 📈 **Growth Documentation**
- **Visual Journals**: Photo timelines and milestone tracking  
- **Growth Analysis**: Measurement tracking and insights
- **Time-lapse Generation**: Premium feature for growth visualization
- **Progress Comparisons**: Before/after analysis tools

### 🌐 **Community & Social**
- **Social Feed**: Share plants, ask questions, get tips
- **Expert Advice**: Verified expert consultation system
- **Content Moderation**: AI-powered community guidelines enforcement
- **Interactive Features**: Likes, comments, shares, and follows

### 🤖 **AI & Smart Features**
- **Plant Care Chatbot**: Context-aware plant advice
- **Smart Recommendations**: Machine learning-based suggestions
- **Automation Rules**: Weather and sensor-triggered actions
- **Multi-LLM Integration**: OpenAI, Gemini, and Claude APIs

### 🌤️ **Weather Integration**
- **Multi-provider APIs**: Intelligent weather data aggregation
- **Environmental Monitoring**: Indoor condition tracking
- **Climate Adaptations**: Seasonal care schedule adjustments
- **Weather-triggered Automation**: Smart care recommendations

### 📊 **Analytics & Insights**
- **User Behavior Tracking**: Comprehensive engagement analytics
- **Plant Care Analytics**: Success rate and pattern analysis
- **Business Intelligence**: Revenue, churn, and growth metrics
- **Performance Monitoring**: Real-time system health tracking

### 💳 **Payment & Subscriptions**
- **Multi-gateway Support**: Razorpay (India) and Stripe (Global)
- **Dynamic Plan Management**: Admin-configurable subscription tiers
- **Revenue Analytics**: Comprehensive financial tracking
- **Dunning Management**: Automated payment retry system

### 📚 **Content Management**
- **Educational Library**: Rich multimedia content system
- **Knowledge Base**: Searchable FAQ and help system
- **Multi-language Support**: Dynamic translation management
- **Content Moderation**: AI-powered screening and approval

## 🏗️ Architecture

### **Modular Monolith Design**
```
🏢 Application Structure
├── 🧠 Admin Management      # System control and configuration
├── 👤 User Management       # Authentication and profiles
├── 🌱 Plant Management      # Plant library and collections
├── 📅 Care Management       # Scheduling and reminders
├── 🏥 Health Monitoring     # Diagnosis and treatment
├── 📈 Growth Tracking       # Documentation and analysis
├── 🌐 Community & Social    # Social features and interactions
├── 🤖 AI Smart Features     # ML and intelligent automation
├── 🌤️ Weather & Environment # Climate data and adaptations
├── 📊 Analytics & Insights  # Metrics and business intelligence
├── 📢 Notifications         # Multi-channel communication
├── 💳 Payment & Billing     # Subscription management
└── 📚 Content Management    # Educational resources
```

### **Technology Stack**
```
🚀 Backend Framework
├── FastAPI 0.111.3          # High-performance async API framework
├── SQLAlchemy 2.0           # Async ORM with PostgreSQL
├── Pydantic V2              # Data validation and serialization
├── Redis                    # Caching and session management
└── Celery                   # Background task processing

🗄️ Database & Storage
├── PostgreSQL 15+           # Primary database (via Supabase)
├── Redis 7.2+               # Cache and message broker
├── Supabase Storage         # File storage and CDN
└── Multi-level Caching      # L1: Memory, L2: Redis, L3: DB

🔐 Authentication & Security
├── Supabase Auth            # Authentication service
├── JWT Tokens               # Stateless authentication
├── OAuth Integration        # Google, Apple Sign-in
├── Rate Limiting            # Per-user and global limits
└── Row Level Security       # Database-level permissions

🤖 AI & External APIs
├── Plant Identification     # PlantNet, Trefle, Plant.id, Kindwise
├── Weather Data             # OpenWeather, Tomorrow.io, Weatherstack
├── AI Chat                  # OpenAI GPT-4, Google Gemini, Claude
├── Translation Services     # Google Translate, DeepL, Azure
└── Content Moderation       # OpenAI Moderation, Perspective API

💳 Payment Processing
├── Razorpay                 # India market
├── Stripe                   # Global markets
├── Subscription Management  # Dynamic plan configuration
└── Webhook Processing       # Real-time payment events

📱 Communication
├── Firebase FCM             # Push notifications
├── SendGrid                 # Email delivery
├── Telegram Bot API         # Alternative notifications
└── Twilio                   # SMS notifications

🐳 Deployment & DevOps
├── Docker & Docker Compose  # Containerization
├── Multi-stage Builds       # Optimized container images
├── Health Checks            # Service monitoring
├── Nginx                    # Reverse proxy and load balancing
└── CI/CD Ready              # GitHub Actions integration
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose**
- **PostgreSQL 15+** (or use Docker)
- **Redis 7.2+** (or use Docker)

### 1. Clone Repository
```bash
git clone https://github.com/plantcare/backend.git
cd plant-care-backend
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 3. Docker Development Environment
```bash
# Start all services
docker-compose up -d

# Start with development tools
docker-compose --profile dev-tools up -d

# Start with monitoring stack
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f api
```

### 4. Manual Setup (Alternative)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Seed initial data
python scripts/seed_database.py

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify Installation
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## 📖 API Documentation

### **Interactive Documentation**
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### **Core Endpoints**
```
🔐 Authentication
POST   /api/v1/auth/register          # User registration
POST   /api/v1/auth/login             # User login
POST   /api/v1/auth/refresh           # Token refresh
POST   /api/v1/auth/logout            # User logout

👤 User Management  
GET    /api/v1/users/profile          # Get user profile
PUT    /api/v1/users/profile          # Update profile
GET    /api/v1/users/subscription     # Subscription status
POST   /api/v1/users/subscription     # Upgrade subscription

🌱 Plant Management
GET    /api/v1/plants                 # List user plants
POST   /api/v1/plants                 # Add new plant
GET    /api/v1/plants/{id}            # Get plant details
PUT    /api/v1/plants/{id}            # Update plant
DELETE /api/v1/plants/{id}            # Delete plant
POST   /api/v1/plants/identify        # AI plant identification

📅 Care Management
GET    /api/v1/care/schedules         # Get care schedules
POST   /api/v1/care/schedules         # Create schedule
POST   /api/v1/care/tasks/complete    # Mark task complete
GET    /api/v1/care/history           # Care history

🏥 Health Monitoring
POST   /api/v1/health/assess          # Health assessment
POST   /api/v1/health/diagnose        # AI diagnosis
GET    /api/v1/health/treatments      # Treatment tracking
POST   /api/v1/health/treatments      # Start treatment

🌐 Community
GET    /api/v1/community/feed         # Community feed
POST   /api/v1/community/posts        # Create post
POST   /api/v1/community/posts/{id}/like  # Like post
POST   /api/v1/community/posts/{id}/comment  # Comment

🤖 AI Features
POST   /api/v1/ai/chat                # AI chat
GET    /api/v1/ai/recommendations     # Smart recommendations
POST   /api/v1/ai/automation          # Create automation rule

🔧 Admin (Restricted)
GET    /api/v1/admin/dashboard        # Admin dashboard
POST   /api/v1/admin/config           # Update configuration
GET    /api/v1/admin/users            # User management
POST   /api/v1/admin/content          # Content management
```

## 🧪 Development

### **Project Structure**
```
plant-care-backend/
├── 📁 app/                          # Application source code
│   ├── 📁 shared/                   # Shared utilities and infrastructure
│   ├── 📁 modules/                  # Feature modules (DDD structure)
│   ├── 📁 api/                      # API layer and middleware  
│   ├── 📁 background_jobs/          # Celery tasks and workers
│   └── 📄 main.py                   # FastAPI application entry point
├── 📁 migrations/                   # Database migrations
├── 📁 config/                       # Configuration files
├── 📁 scripts/                      # Utility scripts
├── 📁 tests/                        # Test suite
├── 📁 docs/                         # Documentation
└── 📁 docker/                       # Docker configuration
```

### **Module Architecture (Domain-Driven Design)**
```
📦 modules/{module_name}/
├── 📁 domain/                       # Business logic and rules
│   ├── 📁 models/                   # Domain entities
│   ├── 📁 services/                 # Domain services
│   ├── 📁 repositories/             # Repository interfaces
│   └── 📁 events/                   # Domain events
├── 📁 infrastructure/               # External concerns
│   ├── 📁 database/                 # Database implementations
│   └── 📁 external/                 # External API clients
├── 📁 application/                  # Use cases and orchestration
│   ├── 📁 commands/                 # Command objects
│   ├── 📁 queries/                  # Query objects  
│   ├── 📁 handlers/                 # Command/Query handlers
│   └── 📁 dto/                      # Data transfer objects
└── 📁 presentation/                 # API interfaces
    ├── 📁 api/v1/                   # FastAPI routes
    ├── 📁 schemas/                  # Pydantic schemas
    └── 📄 dependencies.py           # Route dependencies
```

### **Development Commands**
```bash
# Code formatting
black app/ tests/
isort app/ tests/

# Type checking  
mypy app/

# Linting
flake8 app/ tests/

# Run tests
pytest

# Test with coverage
pytest --cov=app --cov-report=html

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
alembic downgrade -1

# Celery worker (development)
celery -A app.background_jobs.celery_app worker --loglevel=info

# Celery beat scheduler
celery -A app.background_jobs.celery_app beat --loglevel=info
```

### **Environment Variables**
Key configuration variables (see `.env.example` for complete list):

```bash
# Application
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/plantcare_db
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# External APIs
OPENAI_API_KEY=your-openai-key
PLANTNET_API_KEY=your-plantnet-key
OPENWEATHER_API_KEY=your-weather-key

# Payment Gateways
RAZORPAY_KEY_ID=your-razorpay-key
STRIPE_SECRET_KEY=your-stripe-key
```

## 📊 Monitoring & Observability

### **Health Checks**
```bash
# Application health
GET /health

# Detailed health status  
GET /health/detailed

# Database connectivity
GET /health/database

# External services status
GET /health/external
```

### **Monitoring Stack**
```bash
# Prometheus metrics
http://localhost:9090

# Grafana dashboards  
http://localhost:3000

# Flower (Celery monitoring)
http://localhost:5555

# Redis Commander
http://localhost:8081
```

### **Logging**
Structured logging with multiple levels:
- **ERROR**: System errors and exceptions
- **WARN**: Performance and configuration warnings  
- **INFO**: Request/response and business events
- **DEBUG**: Detailed debugging information

## 🧪 Testing

### **Test Categories**
```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests  
pytest tests/e2e/

# Tests with specific markers
pytest -m "not slow"          # Skip slow tests
pytest -m "external_api"      # External API tests only
pytest -m "database"          # Database tests only
```

### **Test Coverage**
```bash
# Generate coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Coverage requirements
# - Minimum: 80%
# - Target: 90%+
```

## 🚀 Deployment

### **Production Environment**
```bash
# Build production image
docker build --target production -t plantcare-api:latest .

# Run with production compose
docker-compose -f docker-compose.prod.yml up -d

# Health verification
curl https://api.plantcare.app/health
```

### **Environment-Specific Configs**
- **Development**: Full debugging, auto-reload, dev tools
- **Staging**: Production-like, with additional monitoring  
- **Production**: Optimized performance, security hardened

## 📈 Performance Optimization

### **Caching Strategy**
- **L1 Cache**: In-memory application cache
- **L2 Cache**: Redis distributed cache  
- **L3 Cache**: Database query cache
- **CDN**: Static assets and images

### **Database Optimization**
- Connection pooling (read/write separation)
- Strategic indexing on frequently queried columns
- Query optimization with EXPLAIN ANALYZE
- Partitioning for analytics tables

### **API Rate Limiting**
- Global: 1000 requests/hour per user
- Premium: 5000 requests/hour per user
- Admin: 10000 requests/hour per user
- Endpoint-specific limits for resource-intensive operations

## 🛡️ Security

### **Authentication & Authorization**
- JWT-based stateless authentication
- Row Level Security (RLS) in PostgreSQL
- OAuth integration (Google, Apple)
- Admin role-based access control

### **Data Protection**
- Encryption at rest and in transit
- Sensitive data field encryption
- Input validation and sanitization
- SQL injection prevention (parameterized queries)

### **API Security**
- CORS configuration
- Rate limiting per user/endpoint
- Request/response size limits
- Security headers middleware

## 🤝 Contributing

### **Development Workflow**
1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** Pull Request

### **Code Standards**
- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain 90%+ test coverage
- Use meaningful commit messages

### **Pull Request Requirements**
- [ ] All tests pass
- [ ] Code coverage maintained
- [ ] Documentation updated
- [ ] Migration scripts included (if needed)
- [ ] Security review completed

## 📚 Documentation

### **Available Documentation**
- **API Docs**: Interactive Swagger/ReDoc interfaces
- **Architecture**: High-level system design
- **Module Docs**: Detailed feature documentation  
- **Deployment**: Production setup guides
- **Contributing**: Development workflow

### **Generate Documentation**
```bash
# API documentation
python scripts/generate_api_docs.py

# Module documentation
python scripts/generate_module_docs.py

# Deploy documentation
mkdocs build
mkdocs serve
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI** - High-performance web framework
- **Supabase** - Backend-as-a-Service platform
- **Plant Identification APIs** - PlantNet, Trefle, Plant.id, Kindwise
- **Weather APIs** - OpenWeatherMap, Tomorrow.io, Weatherstack
- **AI Providers** - OpenAI, Google, Anthropic

## 📞 Support

### **Getting Help**
- 📧 **Email**: dev@plantcare.app
- 💬 **Discord**: [Plant Care Community](https://discord.gg/plantcare)
- 🐛 **Issues**: [GitHub Issues](https://github.com/plantcare/backend/issues)
- 📖 **Documentation**: [docs.plantcare.app](https://docs.plantcare.app)

### **Enterprise Support**
For enterprise deployments, custom integrations, or priority support:
- 📧 **Enterprise**: enterprise@plantcare.app
- 📅 **Schedule Call**: [calendly.com/plantcare-enterprise](https://calendly.com/plantcare-enterprise)

---

<div align="center">

**[🌱 Plant Care App](https://plantcare.app)** | **[📚 Documentation](https://docs.plantcare.app)** | **[🔗 API Reference](https://api.plantcare.app/docs)**

*Made with ❤️ for plant enthusiasts worldwide* 🌍

</div>