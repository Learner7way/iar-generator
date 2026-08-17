"""Тесты utils.file_reader: чтение файлов, детекция кодировок и бинарности."""

from utils.file_reader import (
    DEFAULT_ENCODINGS,
    exceeds_size_limit,
    is_binary_by_content,
    is_binary_by_extension,
    is_binary_file,
    read_text,
)


class TestReadText:
    def test_utf8_file(self, tmp_path):
        f = tmp_path / "main.c"
        f.write_text("int main(void) { return 0; }\n", encoding="utf-8")
        content, encoding = read_text(f)
        assert encoding == "utf-8"
        assert "int main" in content

    def test_cp1251_file(self, tmp_path):
        f = tmp_path / "russian.txt"
        f.write_bytes("Привет мир".encode("cp1251"))
        content, encoding = read_text(f)
        assert encoding == "cp1251"
        assert "Привет мир" in content

    def test_cp866_file(self, tmp_path):
        # Байт 0x98 валиден в cp866, но не в utf-8 и cp1251
        f = tmp_path / "legacy.txt"
        f.write_bytes(b"\x98")
        content, encoding = read_text(f)
        assert encoding == "cp866"
        assert isinstance(content, str)

    def test_latin1_fallback(self, tmp_path):
        f = tmp_path / "binary_safe.txt"
        f.write_bytes(b"\xff\xfe")
        content, encoding = read_text(f, encodings=["utf-8", "latin-1"])
        assert encoding == "latin-1"
        assert isinstance(content, str)

    def test_missing_file_returns_error(self, tmp_path):
        content, error = read_text(tmp_path / "nope.txt")
        assert content is None
        assert error

    def test_size_limit_returns_error(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 1024, encoding="utf-8")
        content, error = read_text(f, max_size_mb=0.000001)
        assert content is None
        assert "лимит" in error

    def test_default_encodings_include_fallbacks(self):
        assert "utf-8" in DEFAULT_ENCODINGS
        assert "latin-1" in DEFAULT_ENCODINGS
        # latin-1 — последняя страховка
        assert DEFAULT_ENCODINGS[-1] == "latin-1"


class TestExceedsSizeLimit:
    def test_under_limit_is_false(self, tmp_path):
        f = tmp_path / "small.txt"
        f.write_text("hello", encoding="utf-8")
        assert exceeds_size_limit(f, max_size_mb=1.0) is False

    def test_over_limit_is_true(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 1024, encoding="utf-8")
        assert exceeds_size_limit(f, max_size_mb=0.000001) is True

    def test_zero_limit_never_exceeds(self, tmp_path):
        f = tmp_path / "any.txt"
        f.write_text("x", encoding="utf-8")
        assert exceeds_size_limit(f, max_size_mb=0) is False

    def test_missing_file_is_over_limit(self, tmp_path):
        assert exceeds_size_limit(tmp_path / "nope.txt") is True


class TestIsBinary:
    def test_binary_by_extension(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_text("not really png", encoding="utf-8")
        assert is_binary_by_extension(f) is True
        assert is_binary_file(f) is True

    def test_binary_by_null_byte(self, tmp_path):
        f = tmp_path / "data.c"
        f.write_bytes(b"int x = 0;\x00\x01\x02;")
        assert is_binary_by_content(f) is True
        assert is_binary_file(f) is True

    def test_binary_by_pdf_signature(self, tmp_path):
        f = tmp_path / "doc.pdf.txt"
        f.write_bytes(b"%PDF-1.4 ...")
        assert is_binary_by_content(f) is True

    def test_text_file_is_not_binary(self, tmp_path):
        f = tmp_path / "main.c"
        f.write_text("int main(void) { return 0; }\n", encoding="utf-8")
        assert is_binary_by_content(f) is False
        assert is_binary_file(f) is False

    def test_empty_file_is_not_binary(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        assert is_binary_by_content(f) is False
