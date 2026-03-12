from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_example_dockerfile_explicitly_copies_model_and_weights():
    content = _read("blueprints/example/Dockerfile")
    assert "COPY app/ /app/app/" in content
    assert "COPY .mdp/weights/ /app/.mdp/weights/" in content
    assert "app.service.app:app" in content


def test_pai_example_dockerfile_explicitly_copies_model_and_weights():
    content = _read("blueprints/pai-example/Dockerfile")
    assert "COPY app/ /app/app/" in content
    assert "COPY .mdp/weights/ /app/.mdp/weights/" in content
    assert "app.service.app:app" in content
