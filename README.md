# ⬡ Vault — File Storage Service

> **Production-grade file storage API** — a self-hosted S3 + Cloudinary alternative with MinIO, signed URLs, per-user quotas, image processing pipelines, and a full-stack Docker deployment.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)
![MinIO](https://img.shields.io/badge/MinIO-S3%20Compatible-C72E49?style=flat-square&logo=minio&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=flat-square&logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📤 **File Upload** | Images, PDFs, docs up to 50MB with type validation |
| 🖼 **Image Pipeline** | Auto-generates thumbnail, medium, large variants via Celery |
| 🔗 **Signed URLs** | Time-limited secure download links (S3-compatible) |
| 📊 **Storage Quotas** | Per-user 5GB quota with real-time tracking |
| 🗄 **MinIO Storage** | Self-hosted S3-compatible object storage |
| 🎨 **Vault Frontend** | Drag & drop UI with file browser, preview modal, quota bar |
| 🐳 **Docker** | One-command full-stack deployment |

---

## 🏗 Architecture

```
Browser
   │
   ▼
┌──────────────────┐
│   Nginx :3001    │  ← serves frontend + proxies API
└─────────┬────────┘
          │ /api/*
          ▼
┌──────────────────┐
│  FastAPI :8001   │  ← file upload, signed URLs, quotas
└──────┬───────────┘
       │
  ┌────┼──────────┐
  ▼    ▼          ▼
┌────┐ ┌───────┐ ┌────────┐
│ PG │ │ Redis │ │ MinIO  │
│:5432│ │:6379 │ │ :9000  │
└────┘ └───┬───┘ └────────┘
           │
           ▼
     ┌──────────┐
     │  Celery  │  ← async image resizing worker
     └──────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose

### Run in one command

```bash
git clone https://github.com/yourusername/file-storage-service
cd file-storage-service
docker-compose up --build
```

| Service | URL |
|---|---|
| 🎨 Frontend | http://localhost:3001 |
| 📖 API Docs | http://localhost:8001/docs |
| 🗄 MinIO Console | http://localhost:9001 |

**MinIO login:** `minioadmin` / `minioadmin123`

---

## 📁 Project Structure

```
file-storage-service/
├── app/
│   ├── main.py                    # FastAPI app, lifespan, CORS
│   ├── config.py                  # Pydantic settings
│   ├── database.py                # Async SQLAlchemy engine
│   ├── models/
│   │   ├── user.py                # User model with quota fields
│   │   └── file.py                # File model with variants JSON
│   ├── schemas/
│   │   └── file.py                # Response models
│   ├── routers/
│   │   ├── files.py               # Upload, list, signed URL, delete
│   │   └── admin.py               # Platform stats
│   ├── services/
│   │   ├── storage_service.py     # MinIO client wrapper
│   │   ├── file_service.py        # Upload orchestration
│   │   └── quota_service.py       # Quota check + update
│   ├── workers/
│   │   └── image_processor.py     # Celery image resize tasks
│   └── core/
│       └── security.py            # JWT + password hashing
├── frontend/                      # Vault HTML/CSS/JS
├── celery_worker.py
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.frontend
├── nginx.conf
└── requirements.txt
```

---

## 🔌 API Endpoints

### Files
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/files/upload` | Upload file to MinIO | ✅ |
| `GET` | `/api/v1/files/` | List user's files | ✅ |
| `GET` | `/api/v1/files/{id}/url` | Generate signed URL | ✅ |
| `DELETE` | `/api/v1/files/{id}` | Delete file + free quota | ✅ |
| `GET` | `/api/v1/files/quota/me` | Get quota usage | ✅ |

### Auth
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/files/auth/register` | Create account |
| `POST` | `/api/v1/files/auth/login` | Get JWT token |

### Admin
| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/v1/admin/stats` | Platform-wide stats | ✅ |

---

## 📤 Upload Flow

```
Client uploads file
        │
        ▼
  Validate type + size
        │
        ▼
  Check user quota
        │
        ▼
  Upload to MinIO ──────────────────────┐
        │                               │
        ▼                               ▼
  Save metadata to PostgreSQL     Is image?
        │                               │
        ▼                          Yes ─┘
  Update used_bytes                     │
        │                               ▼
        ▼                    Celery: generate variants
  Return FileResponse         thumbnail / medium / large
```

---

## 🖼 Image Processing Pipeline

When an image is uploaded, Celery automatically generates 3 variants:

| Variant | Max Size | Use Case |
|---|---|---|
| `thumbnail` | 150×150px | Grid previews |
| `medium` | 600×600px | Standard display |
| `large` | 1200×1200px | Full resolution |

All variants are stored in MinIO under `{user_id}/variants/`.

---

## 🔗 Signed URLs

Signed URLs provide **time-limited secure access** to files without exposing MinIO credentials:

```
GET /api/v1/files/{id}/url?expires=3600
→ {
    "url": "http://localhost:9000/file-storage/..?X-Amz-Signature=...",
    "expires_in": 3600,
    "filename": "photo.jpg"
  }
```

URL expires after `expires` seconds (default: 1 hour, max: 24 hours).

---

## 📊 Storage Quota

Each user gets **5GB free storage** by default:

```json
{
  "used_bytes": 95553,
  "quota_bytes": 5368709120,
  "used_gb": 0.091,
  "quota_gb": 5.0,
  "percent_used": 0.003
}
```

Quota is updated on every upload and delete. Exceeding quota returns `400 Storage quota exceeded`.

---


## 🎨 Supported File Types

| Category | Types |
|---|---|
| 🖼 Images | JPEG, PNG, GIF, WebP |
| 📄 Documents | PDF, DOC, DOCX |
| 📊 Data | CSV, TXT |

---

## 🖥 Frontend — Vault

A sleek file manager UI with:

- **Drag & drop** upload zone with progress bar
- **Grid / List** view toggle
- **Image preview** modal with signed URL
- **One-click download** via signed URL
- **Delete** with confirmation dialog
- **Live quota bar** that animates after upload
- **Toast notifications** for all actions

---

## 🛠 Tech Stack

- **Backend:** FastAPI, SQLAlchemy (async), asyncpg
- **Storage:** MinIO (S3-compatible object storage)
- **Queue:** Celery + Redis
- **Image Processing:** Pillow
- **Database:** PostgreSQL 16
- **Auth:** python-jose (JWT), passlib (bcrypt)
- **Frontend:** Vanilla HTML/CSS/JS, Nginx
- **Container:** Docker, Docker Compose

---

## 🔧 Running Celery Worker

To enable image processing, start the Celery worker:

```bash
# locally
celery -A celery_worker worker --loglevel=info

# or add to docker-compose as a separate service
```

---


