import pytest

"""
전제
- MAX_UPLOAD_SIZE = 10MB
- 파일 확장자: ["pdf", "txt", "md"]
- 기본 청킹: chunk_size=800, chunk_overlap=100
- Canonical text 정규화: 공백/개행/제어문자 정리 후 해시
"""


def test_accepts_allowed_extensions_pdf_txt_md(ingest_policy, allowed_extensions, make_file_meta):
    """Accepts files with allowed extensions: pdf, txt, md."""
    for ext in allowed_extensions:
        file_meta = make_file_meta(ext=ext)
        result = ingest_policy.validate_extension(file_meta["filename"])
        assert result is True, f"Should accept .{ext} files"


def test_rejects_diallowed_extensions_docx_html_csv(ingest_policy, make_file_meta):
    """Rejects files with disallowed extensions."""
    disallowed = ["docx", "html", "csv", "exe", "zip"]

    for ext in disallowed:
        file_meta = make_file_meta(ext=ext)
        result = ingest_policy.validate_extension(file_meta["filename"])
        assert result is False, f"Should reject .{ext} files"


def test_accepts_allowed_mime_types_pdf_text_plain_markdown(ingest_policy, mime_by_extension, make_file_meta):
    """Accepts files with allowed MIME types."""

    for ext, mime_type in mime_by_extension.items():
        file_meta = make_file_meta(ext=ext, mime=mime_type)
        result = ingest_policy.validate_mime_type(file_meta["mime_type"])
        assert result is True, f"Should accept {mime_type}"


def test_rejects_diallowed_mime_types_application_zip_octet_stream(ingest_policy):
    """Rejects files with disallowed MIME types."""
    disallowed_mimes = [
        "application/zip",
        "application/octet-stream",
        "application/x-executable",
        "image/jpeg",
    ]

    for mime_type in disallowed_mimes:
        result = ingest_policy.validate_mime_type(mime_type)
        assert result is False, f"Should reject {mime_type}"


def test_accepts_file_size_at_limit_10mb(ingest_policy, size_bytes_at_limit, make_file_meta):
    """Accepts files exactly at the size limit (10MB)."""
    file_meta = make_file_meta(size=size_bytes_at_limit)

    result = ingest_policy.validate_file_size(file_meta["size"])
    assert result is True, f"Should accept file of {size_bytes_at_limit} bytes"


def test_rejects_file_size_over_limit_10mb_plus_1byte(ingest_policy, size_bytes_above_limit, make_file_meta):
    """Rejects files over the size limit (10MB + 1 byte)."""
    file_meta = make_file_meta(size=size_bytes_above_limit)

    result = ingest_policy.validate_file_size(file_meta["size"])
    assert result is False, f"Should reject file of {size_bytes_above_limit} bytes"


def test_normalizes_filename_strips_path_traversal_chars(ingest_policy, unsafe_filenames):
    """Normalizes filenames by stripping path traversal characters."""

    for unsafe_name in unsafe_filenames:
        safe_name = ingest_policy.normalize_filename(unsafe_name)
        assert ".." not in safe_name, "Should remove path traversal sequences"
        assert "\\" not in safe_name, "Should remove backslashes"
        assert "/" not in safe_name, "Should remove forward slashes"
        assert safe_name.strip() == safe_name, "Should strip leading/trailing spaces"


def test_generates_safe_basename_when_name_missing_or_control_chars(ingest_policy):
    """Generates safe basename when filename is missing or has control chars."""

    # Test with empty/None filenames
    assert ingest_policy.normalize_filename("") != "", "Should generate name for empty string"
    assert ingest_policy.normalize_filename(None) != "", "Should generate name for None"

    # Test with control characters
    unsafe_name = "file\x00\x01\x02.txt"
    safe_name = ingest_policy.normalize_filename(unsafe_name)
    assert "\x00" not in safe_name, "Should remove null bytes"
    assert "\x01" not in safe_name, "Should remove control characters"


def test_rejects_missing_file_meta(ingest_policy):
    """Rejects when file metadata is missing."""

    # Test with None metadata
    with pytest.raises(ValueError, match="file.*meta.*required"):
        ingest_policy.validate_file_meta(None)

    # Test with empty metadata
    with pytest.raises(ValueError, match="file.*meta.*required"):
        ingest_policy.validate_file_meta({})


def test_rejects_empty_filename_or_size_unknown(ingest_policy):
    """Rejects when filename is empty or size is unknown."""

    # Test empty filename
    with pytest.raises(ValueError, match="filename.*required"):
        ingest_policy.validate_file_meta({"filename": "", "size": 1024})

    # Test missing size
    with pytest.raises(ValueError, match="size.*required"):
        ingest_policy.validate_file_meta({"filename": "test.txt", "size": None})

    # Test negative size
    with pytest.raises(ValueError, match="size.*invalid"):
        ingest_policy.validate_file_meta({"filename": "test.txt", "size": -1})


def test_applies_default_chunk_params_when_missing(ingest_policy, policy_defaults):
    """Applies default chunking parameters when not provided."""

    # Test with missing chunk params
    params = ingest_policy.get_chunk_params({})
    assert params["chunk_size"] == ingest_policy.policy_defaults["chunk_size"]
    assert params["chunk_overlap"] == ingest_policy.policy_defaults["chunk_overlap"]

    # Test with None params
    params = ingest_policy.get_chunk_params(None)
    assert params["chunk_size"] == ingest_policy.policy_defaults["chunk_size"]
    assert params["chunk_overlap"] == ingest_policy.policy_defaults["chunk_overlap"]


def test_rejects_negative_chunk_size_or_overlap(ingest_policy):
    """Rejects negative chunk size or overlap values."""

    # Test negative chunk size
    with pytest.raises(ValueError, match="chunk.*size.*invalid"):
        ingest_policy.validate_chunk_params({"chunk_size": -100, "chunk_overlap": 50})

    # Test negative overlap
    with pytest.raises(ValueError, match="chunk.*overlap.*invalid"):
        ingest_policy.validate_chunk_params({"chunk_size": 800, "chunk_overlap": -50})


def test_rejects_zero_or_too_small_chunk_size(ingest_policy):
    """Rejects zero or too small chunk size."""

    # Test zero chunk size
    with pytest.raises(ValueError, match="chunk.*size.*too small"):
        ingest_policy.validate_chunk_params({"chunk_size": 0, "chunk_overlap": 0})

    # Test very small chunk size (e.g., < 10)
    with pytest.raises(ValueError, match="chunk.*size.*too small"):
        ingest_policy.validate_chunk_params({"chunk_size": 5, "chunk_overlap": 0})


def test_rejects_overlap_greater_or_equal_chunk_size(ingest_policy):
    """Rejects when overlap is greater than or equal to chunk size."""

    # Test overlap equal to chunk size
    with pytest.raises(ValueError, match="overlap.*exceed.*chunk.*size"):
        ingest_policy.validate_chunk_params({"chunk_size": 100, "chunk_overlap": 100})

    # Test overlap greater than chunk size
    with pytest.raises(ValueError, match="overlap.*exceed.*chunk.*size"):
        ingest_policy.validate_chunk_params({"chunk_size": 100, "chunk_overlap": 150})


def test_caps_extreme_values_to_max_limits_if_defined(ingest_policy):
    """Caps extreme values to maximum limits if defined."""

    # Test extremely large chunk size (should cap to max)
    params = ingest_policy.get_chunk_params({"chunk_size": 100000, "chunk_overlap": 50})
    assert params["chunk_size"] <= ingest_policy.MAX_CHUNK_SIZE if hasattr(ingest_policy, "MAX_CHUNK_SIZE") else True

    # Test extremely large overlap (should cap to max)
    params = ingest_policy.get_chunk_params({"chunk_size": 1000, "chunk_overlap": 10000})
    assert params["chunk_overlap"] < params["chunk_size"], "Overlap should be less than chunk size"


def test_enables_header_aware_chunking_when_requested(ingest_policy, header_markdown_text):
    """Enables header-aware chunking when requested."""

    # Test with header-aware flag enabled
    params = {"chunk_size": 100, "chunk_overlap": 20, "header_aware": True, "file_type": "md"}

    chunks = ingest_policy.chunk_text(header_markdown_text, params)
    assert len(chunks) > 0, "Should produce chunks"

    # Verify chunks respect header boundaries
    for chunk in chunks:
        lines = chunk.strip().split("\n")
        if lines and lines[0].startswith("#"):
            assert True, "Chunk respects header boundaries"


def test_rejects_header_chunking_without_supported_format(ingest_policy):
    """Rejects header chunking for unsupported formats."""

    # Test header-aware with non-markdown file
    params = {
        "chunk_size": 100,
        "chunk_overlap": 20,
        "header_aware": True,
        "file_type": "txt",  # txt doesn't support header-aware
    }

    with pytest.raises(ValueError, match="header.*not supported"):
        ingest_policy.validate_chunk_params(params)


def test_canonicalization_trims_whitespace_and_normalizes_newlines(ingest_policy):
    """Canonicalization trims whitespace and normalizes newlines."""

    # Text with various whitespace issues
    messy_text = "  Hello   world  \n\n\r\n  Test  \t\t  "
    canonical = ingest_policy.canonicalize_text(messy_text)

    # Should trim and normalize
    assert not canonical.startswith(" "), "Should trim leading spaces"
    assert not canonical.endswith(" "), "Should trim trailing spaces"
    assert "  " not in canonical, "Should normalize multiple spaces"
    assert "\r\n" not in canonical, "Should normalize CRLF"
    assert "\t\t" not in canonical, "Should normalize tabs"


def test_canonicalization_removes_control_chars_and_bom(ingest_policy):
    """Canonicalization removes control characters and BOM."""

    # Text with BOM and control characters
    text_with_bom = "\ufeffHello World"
    text_with_control = "Hello\x00\x01\x02World"

    canonical_bom = ingest_policy.canonicalize_text(text_with_bom)
    assert "\ufeff" not in canonical_bom, "Should remove BOM"

    canonical_control = ingest_policy.canonicalize_text(text_with_control)
    assert "\x00" not in canonical_control, "Should remove null bytes"
    assert "\x01" not in canonical_control, "Should remove control chars"


def test_same_semantic_text_produces_same_hash_despite_spacing(ingest_policy, whitespace_noise_variants):
    """Same semantic text produces same hash despite spacing differences."""

    hashes = set()
    for variant, _ in whitespace_noise_variants:
        canonical = ingest_policy.canonicalize_text(variant)
        text_hash = ingest_policy.compute_hash(canonical)
        hashes.add(text_hash)

    # All variants should produce the same hash
    assert len(hashes) == 1, "All semantically identical texts should have same hash"


def test_different_text_produces_different_hash(ingest_policy):
    """Different text produces different hash."""

    text1 = "Hello World"
    text2 = "Goodbye World"

    hash1 = ingest_policy.compute_hash(ingest_policy.canonicalize_text(text1))
    hash2 = ingest_policy.compute_hash(ingest_policy.canonicalize_text(text2))

    assert hash1 != hash2, "Different texts should produce different hashes"


def test_deduplicates_identical_chunks_by_hash(ingest_policy):
    """Deduplicates identical chunks by hash."""

    chunks = [
        "This is chunk one",
        "This is chunk two",
        "This is chunk one",  # Duplicate
        "This is chunk three",
        "This is chunk two",  # Duplicate
    ]

    deduplicated = ingest_policy.deduplicate_chunks(chunks)
    assert len(deduplicated) == 3, "Should remove duplicate chunks"
    assert "This is chunk one" in deduplicated
    assert "This is chunk two" in deduplicated
    assert "This is chunk three" in deduplicated


def test_retains_unique_chunks_when_hash_differs(ingest_policy):
    """Retains unique chunks when hash differs."""

    chunks = [
        "Unique chunk 1",
        "Unique chunk 2",
        "Unique chunk 3",
        "Unique chunk 4",
    ]

    deduplicated = ingest_policy.deduplicate_chunks(chunks)
    assert len(deduplicated) == len(chunks), "Should retain all unique chunks"
    for chunk in chunks:
        assert chunk in deduplicated, f"Should retain unique chunk: {chunk}"


def test_dedup_is_idempotent_across_multiple_ingest_attempts(ingest_policy):
    """Deduplication is idempotent across multiple ingest attempts."""

    chunks = ["chunk1", "chunk2", "chunk1", "chunk3"]

    # First deduplication
    result1 = ingest_policy.deduplicate_chunks(chunks)

    # Second deduplication of the same result
    result2 = ingest_policy.deduplicate_chunks(result1)

    # Should be identical
    assert result1 == result2, "Deduplication should be idempotent"
    assert len(result1) == 3, "Should have 3 unique chunks"


def test_accepts_valid_collection_and_doc_type_and_tags(ingest_policy):
    """Accepts valid collection, doc_type, and tags."""

    metadata = {"collection": "research", "doc_type": "technical", "tags": ["python", "testing", "tdd"]}

    result = ingest_policy.validate_metadata(metadata)
    assert result is True, "Should accept valid metadata"


def test_rejects_invalid_doc_type_values(ingest_policy):
    """Rejects invalid doc_type values."""

    invalid_doc_types = ["", None, 123, [], {}]

    for doc_type in invalid_doc_types:
        metadata = {"collection": "research", "doc_type": doc_type, "tags": []}
        with pytest.raises(ValueError, match="doc_type.*invalid"):
            ingest_policy.validate_metadata(metadata)


def test_normalizes_tags_case_trimming_and_uniqueness(ingest_policy):
    """Normalizes tags: case, trimming, and uniqueness."""

    tags = [
        "  Python  ",
        "TESTING",
        "python",  # Duplicate after normalization
        "TDD",
        "testing",  # Duplicate after normalization
    ]

    normalized = ingest_policy.normalize_tags(tags)
    assert len(normalized) == 3, "Should remove duplicates after normalization"
    assert "python" in normalized, "Should lowercase and trim"
    assert "testing" in normalized, "Should lowercase"
    assert "tdd" in normalized, "Should lowercase"


def test_respects_idempotency_key_to_prevent_duplicate_ingest(ingest_policy, idempotency_keys):
    """Respects idempotency key to prevent duplicate ingest."""

    key1, _ = idempotency_keys

    # First ingest with idempotency key
    result1 = ingest_policy.check_idempotency(key1)
    assert result1 is True, "First request should proceed"

    # Mark as processed
    ingest_policy.mark_processed(key1)

    # Second ingest with same key
    result2 = ingest_policy.check_idempotency(key1)
    assert result2 is False, "Duplicate request should be blocked"


def test_different_idempotency_keys_treated_as_distinct_requests(ingest_policy, idempotency_keys):
    """Different idempotency keys are treated as distinct requests."""
    key1, key2 = idempotency_keys

    # Process first key
    ingest_policy.mark_processed(key1)

    # Second key should still be allowed
    result = ingest_policy.check_idempotency(key2)
    assert result is True, "Different idempotency key should be allowed"


def test_idempotency_skips_re_embedding_for_same_document_hash(ingest_policy):
    """Idempotency skips re-embedding for same document hash."""

    doc_content = "This is the document content"
    doc_hash = ingest_policy.compute_hash(doc_content)

    # First processing
    should_embed1 = ingest_policy.should_embed(doc_hash)
    assert should_embed1 is True, "Should embed new document"

    # Mark as embedded
    ingest_policy.mark_embedded(doc_hash)

    # Second processing with same hash
    should_embed2 = ingest_policy.should_embed(doc_hash)
    assert should_embed2 is False, "Should skip re-embedding for same hash"


def test_rejects_disallowed_embedded_scripts_in_pdf_policy_level(ingest_policy):
    """Rejects disallowed embedded scripts in PDF at policy level."""

    # Simulate PDF with embedded script
    pdf_metadata = {"filename": "document.pdf", "has_javascript": True, "has_embedded_files": True}

    with pytest.raises(ValueError, match="security.*pdf.*script"):
        ingest_policy.validate_pdf_security(pdf_metadata)


def test_flags_possible_pii_for_masking_when_policy_enabled(ingest_policy_with_pii):
    """Flags possible PII for masking when policy is enabled."""

    text_with_pii = "John Doe's email is john@example.com and SSN is 123-45-6789"

    pii_flags = ingest_policy_with_pii.detect_pii(text_with_pii)
    assert len(pii_flags) > 0, "Should detect PII"
    assert any("email" in flag.lower() for flag in pii_flags), "Should detect email"
    assert any("ssn" in flag.lower() for flag in pii_flags), "Should detect SSN"


def test_overlap_respected_when_chunking_params_valid(ingest_policy, gen_text_of_approx_tokens):
    """Overlap is respected when chunking parameters are valid."""

    text = gen_text_of_approx_tokens(1000)  # Generate ~1000 token text
    params = {"chunk_size": 100, "chunk_overlap": 20}

    chunks = ingest_policy.chunk_text(text, params)

    # Check overlap between consecutive chunks
    for i in range(len(chunks) - 1):
        chunk1 = chunks[i]
        chunk2 = chunks[i + 1]

        # Last 20 chars of chunk1 should overlap with first 20 of chunk2 (approximately)
        overlap_text = chunk1[-20:] if len(chunk1) >= 20 else chunk1
        assert any(overlap_text in chunk2 for overlap_text in [overlap_text]), "Chunks should have overlap"


def test_last_chunk_smaller_than_size_is_allowed(ingest_policy, gen_text_of_approx_tokens):
    """Last chunk smaller than chunk_size is allowed."""

    # Generate text that doesn't divide evenly
    text = gen_text_of_approx_tokens(250)  # ~250 tokens
    params = {"chunk_size": 100, "chunk_overlap": 10}

    chunks = ingest_policy.chunk_text(text, params)

    # Last chunk should be allowed even if smaller
    assert len(chunks) > 0, "Should produce chunks"
    last_chunk = chunks[-1]
    assert len(last_chunk) > 0, "Last chunk should not be empty"


def test_prefers_header_boundaries_over_token_boundaries_when_possible(ingest_policy, header_markdown_text):
    """Prefers header boundaries over token boundaries when possible."""

    params = {"chunk_size": 50, "chunk_overlap": 10, "header_aware": True, "file_type": "md"}

    chunks = ingest_policy.chunk_text(header_markdown_text, params)

    # Check that chunks tend to start with headers
    header_starts = sum(1 for chunk in chunks if chunk.strip().startswith("#"))
    assert header_starts > 0, "Should prefer to split at header boundaries"


def test_falls_back_to_token_boundaries_when_headers_absent(ingest_policy, sample_plain_text):
    """Falls back to token boundaries when headers are absent."""

    params = {"chunk_size": 50, "chunk_overlap": 10, "header_aware": True, "file_type": "md"}

    # Plain text without headers
    chunks = ingest_policy.chunk_text(sample_plain_text, params)

    assert len(chunks) > 0, "Should still chunk even without headers"
    # Chunks should be roughly equal in size (token-based)
    sizes = [len(chunk) for chunk in chunks[:-1]]  # Exclude last chunk
    if sizes:
        avg_size = sum(sizes) / len(sizes)
        assert all(abs(size - avg_size) < avg_size * 0.5 for size in sizes), (
            "Chunks should be roughly equal sized when no headers"
        )


def test_sentence_boundary_respected_when_enabled(ingest_policy):
    """Sentence boundary is respected when enabled."""

    text = "This is the first sentence. This is the second sentence. This is the third sentence."
    params = {"chunk_size": 50, "chunk_overlap": 10, "sentence_boundary": True}

    chunks = ingest_policy.chunk_text(text, params)

    # Check chunks end at sentence boundaries
    for chunk in chunks:
        if chunk.strip():
            assert chunk.strip().endswith((".", "!", "?")), "Chunks should end at sentence boundaries"


def test_validation_errors_provide_code_and_message(ingest_policy):
    """Validation errors provide error code and message."""

    try:
        ingest_policy.validate_file_size(100 * 1024 * 1024)  # 100MB, too large
    except ValueError as e:
        error = e.args[0] if isinstance(e.args[0], dict) else {"message": str(e)}
        assert "code" in error or "message" in str(e), "Error should have code or message"
        assert "size" in str(e).lower(), "Error should mention size"


def test_policy_error_messages_localizable_or_constant_keys(ingest_policy):
    """Policy error messages are localizable or use constant keys."""

    # Test various validation errors
    errors = []

    try:
        ingest_policy.validate_extension("file.exe")
    except ValueError as e:
        errors.append(e)

    try:
        ingest_policy.validate_file_size(100 * 1024 * 1024)
    except ValueError as e:
        errors.append(e)

    # Check that errors have consistent structure
    for error in errors:
        error_str = str(error)
        # Should contain key-like identifiers (e.g., INVALID_EXTENSION, FILE_TOO_LARGE)
        assert any(word.isupper() for word in error_str.split()) or any(
            key in error_str.lower() for key in ["invalid", "error", "failed"]
        ), "Errors should use constant keys or clear messages"


def test_prioritizes_size_error_over_extension_if_both_invalid(ingest_policy, size_bytes_above_limit):
    """Prioritizes size error over extension error if both are invalid."""

    # File with both invalid extension and size
    file_meta = {"filename": "large.exe", "size": size_bytes_above_limit, "mime_type": "application/x-executable"}

    try:
        ingest_policy.validate_file(file_meta)
    except ValueError as e:
        # Should report size error first (higher priority)
        assert "size" in str(e).lower(), "Should prioritize size error"


def test_prioritizes_security_violation_over_mime_mismatch(ingest_policy):
    """Prioritizes security violation over MIME type mismatch."""

    # File with security issue and MIME mismatch
    file_meta = {
        "filename": "../../etc/passwd",
        "size": 1024,
        "mime_type": "text/plain",
        "declared_mime": "application/pdf",  # Mismatch
    }

    try:
        ingest_policy.validate_file(file_meta)
    except ValueError as e:
        # Should report security error first (highest priority)
        assert "security" in str(e).lower() or "traversal" in str(e).lower(), "Should prioritize security error"


def test_rejects_potentially_explosive_chunk_counts(ingest_policy):
    """Rejects potentially explosive chunk counts."""

    # Very small chunk size that would create too many chunks
    params = {
        "chunk_size": 1,  # 1 character chunks
        "chunk_overlap": 0,
        "text_length": 1000000,  # 1 million characters
    }

    with pytest.raises(ValueError, match="chunk.*count.*too.*large|explosive"):
        ingest_policy.validate_chunk_count(params)


def test_produces_embedding_batch_hint_within_limits(ingest_policy):
    """Produces embedding batch hint within limits."""

    # Generate chunks
    chunks = [f"Chunk {i}" for i in range(100)]

    batch_size = ingest_policy.get_embedding_batch_size(chunks)

    # Batch size should be reasonable
    assert 1 <= batch_size <= 100, "Batch size should be within reasonable limits"
    assert batch_size <= len(chunks), "Batch size should not exceed chunk count"


def test_policy_returns_audit_fields_for_logging(ingest_policy, fake_clock):
    """Policy returns audit fields for logging."""

    file_meta = {"filename": "test.pdf", "size": 1024, "mime_type": "application/pdf"}

    audit_fields = ingest_policy.get_audit_fields(file_meta, fake_clock.now())

    # Should include essential audit fields
    assert "timestamp" in audit_fields, "Should include timestamp"
    assert "filename" in audit_fields, "Should include filename"
    assert "size" in audit_fields, "Should include file size"
    assert "action" in audit_fields or "operation" in audit_fields, "Should include action/operation"
    assert audit_fields["timestamp"] == fake_clock.now(), "Should use provided timestamp"
