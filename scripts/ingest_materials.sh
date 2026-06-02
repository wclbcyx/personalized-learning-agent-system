#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"
source .venv/bin/activate 2>/dev/null || true

python - <<'PY'
from app.services.material_service import MaterialService

service = MaterialService()
status = service.get_index_status()
print("materials:", len(service.list_materials()))
print("documents:", status["document_count"])
print("chunks:", status["chunk_count"])
print("mode:", status["retrieval_mode"])
PY
