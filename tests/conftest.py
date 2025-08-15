import hashlib
import random
import re
import string
import textwrap
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="session")
def max_upload_size() -> int:
    return 10 * 1024 * 1024  # 10MB


@pytest.fixture(scope="session")
def allowed_extensions() -> list[str]:
    return ["pdf", "txt", "md"]


@pytest.fixture(scope="session")
def mime_by_extension() -> dict[str, str]:
    return {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
    }


@pytest.fixture(scope="session")
def policy_defaults() -> dict[str, Any]:
    return {"chunk_size": 800, "chunk_overlap": 100}


@pytest.fixture(scope="session")
def size_bytes_at_limit(max_upload_size: int) -> int:
    return max_upload_size


@pytest.fixture(scope="session")
def size_bytes_below_limit(size_bytes_at_limit: int) -> int:
    return size_bytes_at_limit - 1


@pytest.fixture(scope="session")
def size_bytes_above_limit(size_bytes_at_limit: int) -> int:
    return size_bytes_at_limit + 1


@pytest.fixture
def make_file_meta(mime_by_extension: dict[str, str]) -> Callable[..., dict[str, Any]]:
    def _make(
        *,
        name: str = "sample",
        ext: str = "txt",
        size: int = 1024,
        mime: str | None = None,
        collection: str = "default",
    ) -> dict[str, Any]:
        filename = f"{name}.{ext}" if ext else name
        return {
            "filename": filename,
            "size": size,
            "mime_type": mime or mime_by_extension.get(ext, "application/octet-stream"),
            "collection": collection,
            "uploaded_at": datetime.now(UTC),
        }

    return _make


@pytest.fixture
def sample_plain_text() -> str:
    return textwrap.dedent(
        """
        Hello,  world!
        This is   a   sample   text.

        It contains   multiple   spaces, tabs\t\t, and newlines.

        End.
        """
    ).strip()


@pytest.fixture
def header_markdown_text() -> str:
    # 헤더 인식 기반 청킹 테스트용
    return textwrap.dedent(
        """
        # Title

        Intro paragraph.

        ## Section A
        A content line 1.
        A content line 2.

        ## Section B
        B content line 1.
        B content line 2.
        """
    ).strip()


@pytest.fixture
def whitespace_noise_variants() -> Iterable[tuple[str, str]]:
    """
    canonicalization 후 동일해야 하는 (원본, 기대의미) 쌍들.
    실제 canonicalization은 도메인 정책에서 수행하되,
    여기서는 '의도된 동등성'을 데이터로 제공.
    """
    pairs = [
        ("Hello   world", "Hello world"),
        ("Hello\tworld", "Hello world"),
        (" Hello  world \n", "Hello world"),
        ("\ufeffHello  world", "Hello world"),
        ("Hello \r\n world", "Hello world"),
    ]
    return pairs


@pytest.fixture
def gen_words() -> Callable[[int], str]:
    def _gen(n: int) -> str:
        words = []
        for _ in range(n):
            length = random.randint(3, 8)
            token = "".join(random.choices(string.ascii_lowercase, k=length))
            words.append(token)
        return " ".join(words)

    return _gen


@pytest.fixture
def gen_text_of_approx_tokens(gen_words: Callable[[int], str]) -> Callable[[int], str]:
    """
    대략적인 '토큰 수'를 단어 수로 모사한 텍스트 생성기.
    """
    return gen_words


@pytest.fixture
def simple_canonicalize() -> Callable[[str], str]:
    """
    테스트 편의를 위한 간단한 정규화: 공백/개행 정리 + BOM/제어문자 제거.
    실제 정책 canonicalization과 달라질 수 있으니,
    테스트에서는 '정책에서 제공하는 함수'를 주로 검증 대상으로 삼으세요.
    """
    ws_re = re.compile(r"\s+", re.MULTILINE)

    def _canon(text: str) -> str:
        if text is None:
            return ""
        # BOM/제어문자 제거(간단 버전)
        text = text.replace("\ufeff", "")
        text = "".join(ch for ch in text if ch.isprintable() or ch.isspace())
        # 공백/개행 축약
        text = ws_re.sub(" ", text).strip()
        return text

    return _canon


@pytest.fixture
def sha256_hash() -> Callable[[str], str]:
    def _h(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    return _h


@pytest.fixture
def idempotency_keys() -> tuple[str, str]:
    return (str(uuid.uuid4()), str(uuid.uuid4()))


@dataclass
class FakeClock:
    now_: datetime

    def now(self) -> datetime:
        return self.now_

    def advance(self, *, seconds: int = 0, minutes: int = 0, hours: int = 0) -> None:
        delta = timedelta(seconds=seconds, minutes=minutes, hours=hours)
        self.now_ = self.now_ + delta


@pytest.fixture
def fake_clock() -> FakeClock:
    # 고정된 UTC 시간에서 시작
    return FakeClock(now_=datetime(2025, 8, 12, 12, 0, 0, tzinfo=UTC))


@pytest.fixture
def temp_upload_dir(tmp_path: Path) -> Path:
    path = tmp_path / "uploads" / "2025" / "08" / "12"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def unsafe_filenames() -> list[str]:
    return [
        "../../etc/passwd",
        r"..\..\Windows\System32",
        "normal.pdf",
        " spaced name .txt ",
        "control-\x00-chars.md",
    ]


@pytest.fixture(autouse=True)
def _seed_random() -> None:
    # 랜덤 시퀀스 결정론 보장(스냅샷 테스트 안정성)
    random.seed(42)
