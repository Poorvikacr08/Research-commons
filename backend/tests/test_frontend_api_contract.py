import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"
BACKEND_ROUTERS = ROOT / "backend" / "app" / "routers"
API_CALL = re.compile(r"\bapi(?:Optional)?\(\s*([`\"'])(.*?)\1", re.DOTALL)
ROUTE = re.compile(r"@router\.(?:get|post|put|patch|delete)\(\s*([\"'])(.*?)\1", re.DOTALL)
PREFIX = re.compile(r"router\s*=\s*APIRouter\([^)]*?prefix\s*=\s*([\"'])(.*?)\1", re.DOTALL)


def normalize_path(path):
    path = re.sub(r"\$\{\w+\s*\?.*", "", path)
    path = path.split("?", 1)[0]
    path = re.sub(r"\$\{[^}]+\}", "{}", path)
    path = re.sub(r"\{[^}]+\}", "{}", path)
    return path.rstrip("/") or "/"


class FrontendApiContractTests(unittest.TestCase):
    def test_frontend_api_paths_have_backend_routes(self):
        frontend_paths = set()
        for source in list(FRONTEND_SRC.rglob("*.js")) + list(FRONTEND_SRC.rglob("*.jsx")):
            if source.name == "api.js":
                continue
            text = source.read_text(encoding="utf-8")
            for _, path in API_CALL.findall(text):
                if path.startswith("/"):
                    frontend_paths.add(normalize_path(path))

        backend_paths = set()
        for source in BACKEND_ROUTERS.glob("*.py"):
            text = source.read_text(encoding="utf-8")
            prefix_match = PREFIX.search(text)
            prefix = prefix_match.group(2) if prefix_match else ""
            for _, path in ROUTE.findall(text):
                backend_paths.add(normalize_path(prefix + path))

        missing = sorted(path for path in frontend_paths if path not in backend_paths)
        self.assertTrue(frontend_paths, "Expected to discover frontend API calls")
        self.assertEqual([], missing, f"Frontend paths missing from FastAPI routers: {missing}")

    def test_vite_api_proxy_targets_fastapi_service(self):
        vite_config = (ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")
        api_client = (FRONTEND_SRC / "api.js").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn('fetch(`/api${path}`', api_client)
        self.assertIn('"/api": process.env.VITE_API_PROXY || "http://localhost:8000"', vite_config)
        self.assertIn("VITE_API_PROXY: http://backend:8000", compose)


if __name__ == "__main__":
    unittest.main()
