"""Write the generated OpenAPI document to api/openapi.json."""

from pathlib import Path

from kritzellm.api.app import render_openapi

SPEC_PATH = Path(__file__).resolve().parents[2] / "api" / "openapi.json"

if __name__ == "__main__":
    SPEC_PATH.write_text(render_openapi())
    print(f"Wrote {SPEC_PATH}")
