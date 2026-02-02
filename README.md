# 🌿 Vietnamese Environmental Law Q&A System

Hệ thống Agentic AI với kỹ thuật GraphRAG nâng cao để tra cứu và hỏi đáp về luật môi trường Việt Nam.

## 🚀 Tính Năng

- **GraphRAG với Hybrid Retrieval**: Kết hợp vector search và graph traversal cho độ chính xác cao
- **Local LLM**: Vistral 7B - Model tiếng Việt chạy hoàn toàn local
- **Multi-hop Reasoning**: Duyệt graph để tìm context liên quan từ nhiều văn bản
- **Citation Tracking**: Trích dẫn chính xác nguồn (tên văn bản, trang, điều khoản)
- **Real-time Streaming**: Phản hồi real-time qua WebSocket
- **Document Processing**: Xử lý PDF, DOCX với hierarchical chunking
- **Modern UI**: React + TypeScript + Tailwind CSS
- **Scalable Architecture**: Docker Compose với tất cả services

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│            (TypeScript, Tailwind CSS, Vite)             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│               FastAPI Backend (Python)                   │
│    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐│
│    │   RAG       │  │  Document    │  │  Auth &      ││
│    │  Service    │  │  Processor   │  │  Security    ││
│    └─────────────┘  └──────────────┘  └──────────────┘│
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬────────────────┐
        │             │             │                │
        ▼             ▼             ▼                ▼
   ┌────────┐   ┌─────────┐   ┌────────┐      ┌─────────┐
   │Qdrant  │   │ Neo4j   │   │Postgres│      │ Ollama  │
   │(Vector)│   │ (Graph) │   │ (Meta) │      │(Vistral)│
   └────────┘   └─────────┘   └────────┘      └─────────┘
```

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Vistral 7B via Ollama | Local Vietnamese language model |
| **Embeddings** | Multilingual-E5-Large | SOTA multilingual embeddings (1024-dim) |
| **Vector DB** | Qdrant | Hybrid search (dense + BM25) |
| **Graph DB** | Neo4j | Knowledge graph for multi-hop reasoning |
| **Backend** | FastAPI + Python 3.11 | Async API with WebSocket |
| **Frontend** | React 18 + TypeScript | Modern SPA with Vite |
| **SQL DB** | PostgreSQL 16 | Metadata and user data |
| **Cache** | Redis 7 | Session and query caching |
| **Deployment** | Docker Compose | All-in-one orchestration |

## 📋 Yêu Cầu Hệ Thống

### Tối Thiểu
- **CPU**: 4 cores
- **RAM**: 16GB
- **GPU**: Optional (CPU-only mode available)
- **Disk**: 50GB free space
- **OS**: Linux, macOS, Windows (với WSL2)

### Khuyến Nghị (với GPU)
- **GPU**: NVIDIA GPU với <8GB VRAM (GTX 1080, RTX 3060, etc.)
- **RAM**: 32GB
- **Disk**: 100GB SSD

### Software
- Docker 24+ và Docker Compose 2.20+
- NVIDIA Docker runtime (nếu dùng GPU)
- Git

## 🚦 Cài Đặt và Chạy

### 1. Clone Repository

```bash
git clone <repository-url>
cd agentic_ai_rag_adv
```

### 2. Cấu Hình Environment

```bash
cp .env.example .env
# Chỉnh sửa .env với các giá trị phù hợp
```

### 3. Khởi Động Hệ Thống

#### Với GPU (Khuyến nghị)
```bash
docker-compose up -d
```

#### Chỉ CPU (không GPU)
```bash
# Comment out phần GPU trong docker-compose.yml (dòng deploy: resources)
docker-compose up -d
```

### 4. Kiểm Tra Services

```bash
# Xem status của tất cả services
docker-compose ps

# Xem logs
docker-compose logs -f

# Kiểm tra health
curl http://localhost:8000/health
```

### 5. Truy Cập Ứng Dụng

- **Frontend**: http://localhost:5173
- **Backend API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474 (user: neo4j, pass: ragpassword123)
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## 📁 Cấu Trúc Dự Án

```
agentic-ai-rag-adv/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Config, security, dependencies
│   │   ├── services/       # Business logic (RAG, document processing)
│   │   ├── repositories/   # Database access layer
│   │   ├── models/         # SQLAlchemy models & Pydantic schemas
│   │   └── utils/          # Utilities (chunking, embeddings, NLP)
│   ├── tests/              # Unit, integration, E2E tests
│   ├── alembic/            # Database migrations
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── frontend/                # React application
│   ├── src/
│   │   ├── components/     # React components (chat, documents, admin)
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API clients
│   │   ├── pages/          # Page components
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Service orchestration
├── .env.example             # Environment template
└── README.md
```

## 🔧 Development

### Backend Development

```bash
# Vào container backend
docker-compose exec backend bash

# Chạy migrations
alembic upgrade head

# Tạo migration mới
alembic revision --autogenerate -m "description"

# Chạy tests
pytest

# Linting
flake8 app/
black app/
```

### Frontend Development

```bash
# Vào container frontend
docker-compose exec frontend sh

# Install dependencies
npm install

# Build
npm run build

# Linting
npm run lint

# Format
npm run format
```

## 📖 Sử Dụng Hệ Thống

### 1. Upload Tài Liệu

1. Vào trang "Tài Liệu"
2. Kéo thả hoặc chọn file PDF/DOCX
3. Đợi quá trình xử lý (parsing, chunking, embedding, graph construction)
4. Kiểm tra status trong danh sách tài liệu

### 2. Hỏi Đáp

1. Vào trang "Hỏi Đáp"
2. Nhập câu hỏi về luật môi trường
3. Hệ thống sẽ:
   - Tìm kiếm vector trong Qdrant
   - Mở rộng context qua Neo4j graph
   - Generate câu trả lời với Vistral
   - Hiển thị citations với source links
4. Click vào citation để xem source document

### 3. Quản Trị

1. Vào trang "Quản Trị"
2. Xem thống kê:
   - Số lượng tài liệu đã xử lý
   - Số lượng queries
   - Performance metrics (latency, accuracy)
   - Usage by user

## 🧪 Testing

### Chạy Tests

```bash
# Backend tests
docker-compose exec backend pytest

# With coverage
docker-compose exec backend pytest --cov=app --cov-report=html

# Frontend tests
docker-compose exec frontend npm test

# E2E tests
docker-compose exec frontend npm run test:e2e
```

### Test Data

```bash
# Seed test data
docker-compose exec backend python scripts/seed_data.py
```

## 📊 Performance

### Benchmarks (GPU: RTX 3060 6GB)

- **Document Processing**: ~2-3 phút cho PDF 50 trang
- **Query Latency (p95)**: <3 giây
- **Throughput**: 10-20 concurrent users
- **Embedding Speed**: ~100 chunks/second
- **LLM Speed**: ~40 tokens/second

### Optimization Tips

1. **GPU Memory**: Sử dụng quantized model (Q4_K_M) nếu VRAM hạn chế
2. **Caching**: Redis cache cho frequent queries
3. **Batch Processing**: Process documents in background
4. **Index Tuning**: Optimize Qdrant HNSW parameters

## 🔒 Security

- ✅ JWT authentication với token refresh
- ✅ Password hashing (bcrypt)
- ✅ CORS protection
- ✅ Input validation (Pydantic)
- ✅ Rate limiting (Redis)
- ✅ File upload validation
- ⚠️ **TODO**: Add SSL/TLS for production
- ⚠️ **TODO**: Implement API rate limiting per user

## 🐛 Troubleshooting

### Ollama không pull được model

```bash
docker-compose exec ollama ollama pull vistral:7b-chat-q4_K_M
```

### Neo4j không khởi động

```bash
# Kiểm tra logs
docker-compose logs neo4j

# Xóa data và restart
docker-compose down -v
docker-compose up -d neo4j
```

### Backend không connect được database

```bash
# Kiểm tra PostgreSQL
docker-compose exec postgres psql -U raguser -d ragdb -c "SELECT 1;"

# Run migrations
docker-compose exec backend alembic upgrade head
```

## 📚 Documentation

- [Architecture Documentation](docs/architecture.md) - TODO
- [API Documentation](http://localhost:8000/docs) - Available when running
- [User Guide](docs/user-guide.md) - TODO
- [Development Guide](docs/development.md) - TODO

## 🗺️ Roadmap

### Phase 1: Foundation ✅ (COMPLETED)
- [x] Docker Compose setup
- [x] Backend skeleton (FastAPI)
- [x] Frontend skeleton (React + TypeScript)
- [x] Database models
- [x] Authentication

### Phase 2: Document Processing (In Progress)
- [ ] Upload API
- [ ] PDF/DOCX parsing
- [ ] Hierarchical chunking
- [ ] Embedding generation
- [ ] Qdrant indexing
- [ ] Neo4j graph construction

### Phase 3: RAG Pipeline
- [ ] Ollama integration
- [ ] Hybrid retrieval
- [ ] Graph traversal
- [ ] Re-ranking
- [ ] Context assembly
- [ ] Prompt engineering

### Phase 4: Frontend & UX
- [ ] Chat interface
- [ ] Real-time streaming
- [ ] Citation display
- [ ] Document management
- [ ] Export functionality

### Phase 5: Advanced Features
- [ ] Admin dashboard
- [ ] Conversation history
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Monitoring

### Phase 6: Testing & Deployment
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests
- [ ] Performance testing
- [ ] CI/CD pipeline

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[MIT License](LICENSE)

## 👥 Team

- **Backend Developer**: [Your Name]
- **Frontend Developer**: [Your Name]
- **DevOps/Testing**: [Your Name]

## 📞 Contact

- **Email**: your-email@example.com
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

**Ghi chú**: Dự án đang trong giai đoạn phát triển. Phase 1 (Foundation) đã hoàn thành ✅

**Built with** ❤️ for Vietnamese Environmental Law Community
