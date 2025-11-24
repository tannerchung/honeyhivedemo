import os
import pytest
from pathlib import Path

from dotenv import load_dotenv


pytestmark = pytest.mark.integration


# Load .env so local keys are picked up even if not exported
load_dotenv(dotenv_path=Path(".env"), override=True)


def _missing_keys() -> bool:
    return not (os.getenv("HONEYHIVE_API_KEY") and os.getenv("OPENAI_API_KEY"))


@pytest.mark.skipif(_missing_keys(), reason="Requires HONEYHIVE_API_KEY and OPENAI_API_KEY for live trace")
def test_honeyhive_traces_openai_call():
    """Minimal live call to confirm HoneyHive tracer initializes and traces OpenAI."""
    try:
        from honeyhive import HoneyHiveTracer, trace
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - optional deps
        pytest.skip(f"Optional deps missing: {exc}")

    HoneyHiveTracer.init(
        api_key=os.environ["HONEYHIVE_API_KEY"],
        project=os.getenv("HONEYHIVE_PROJECT", "honeyhivedemo"),
        source=os.getenv("HONEYHIVE_SOURCE", "dev"),
        session_name=os.getenv("HONEYHIVE_SESSION", "Test Session"),
    )

    @trace
    def call_openai():
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
            temperature=0,
        )
        return completion.choices[0].message.content

    content = call_openai()
    assert isinstance(content, str) and len(content) > 0
