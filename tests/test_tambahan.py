"""Test tambahan buatan kelompok.

Isi dengan:
1. Satu test regresi untuk setiap bug yang kalian perbaiki (gagal sebelum perbaikan,
   lulus sesudahnya). Beri nama yang menjelaskan bug-nya.
2. Lima test kasus tepi, masing-masing dengan komentar singkat mengapa kasus itu berisiko.
"""

import pytest
from crud.lexer import LexError
from crud.lexer import tokenize, TokenType as T
from crud.pipeline import analyze_source


def test_regresi_keyword_campur_huruf_dinormalisasi():
    # Bug: lexer membandingkan teks mentah dengan KEYWORDS (huruf besar),
    # jadi 'select' atau 'sElEcT' dianggap IDENT, bukan KEYWORD.
    for kata in ["select", "Select", "sElEcT"]:
        tok = tokenize(kata)[0]
        assert tok.type == T.KEYWORD
        assert tok.value == "SELECT"


def test_ident_berawalan_keyword_tetap_ident():
    # Kasus tepi: 'selection' dan 'fromage' cuma DIAWALI keyword, jadi harus tetap IDENT.
    for kata in ["selection", "fromage"]:
        tok = tokenize(kata)[0]
        assert tok.type == T.IDENT
        assert tok.value == kata


def test_regresi_komentar_blok_lintas_baris_tidak_jadi_token():
    # TODO(T3): sebelumnya komentar blok langsung memicu LexError.
    toks = tokenize("/* satu\n dua */ SELECT")
    assert [t.value for t in toks if t.type != T.EOF] == ["SELECT"]


def test_komentar_blok_tidak_ditutup_adalah_lexerror():
    # Kasus tepi: file habis sebelum '*/' ketemu.
    with pytest.raises(LexError):
        tokenize("SELECT /* belum ditutup")


def test_komentar_blok_boleh_berisi_bintang():
    # Kasus tepi: '*' di dalam komentar tidak boleh dianggap penutup.
    toks = tokenize("/* a * b ** c */ SELECT")
    assert toks[0].value == "SELECT"

def _nilai(src):
    return [t.value for t in tokenize(src) if t.type != T.EOF]


def test_regresi_tidak_sama_dengan_satu_token():
    # Bug: '<>' dipecah jadi '<' lalu '>' (melanggar maximal munch, SPESIFIKASI 2.5).
    toks = [t for t in tokenize("a <> b") if t.type != T.EOF]
    assert [(t.type, t.value) for t in toks] == [
        (T.IDENT, "a"), (T.OP, "<>"), (T.IDENT, "b"),
    ]


def test_regresi_tidak_sama_dengan_di_where_tidak_error_parser():
    # Gejala bug '<>': parser mengeluh "diharapkan ekspresi, ditemukan '>'".
    res = analyze_source("SELECT id FROM t WHERE x <> 'a'")
    assert res.lex_error is None and res.parse_errors == []


def test_tidak_sama_dengan_tanpa_spasi_dan_posisinya():
    # Kasus tepi: tanpa spasi, dan kolom token sesudahnya harus tetap benar.
    toks = [t for t in tokenize("a<>b") if t.type != T.EOF]
    assert [t.value for t in toks] == ["a", "<>", "b"]
    assert [t.col for t in toks] == [1, 2, 4]


def test_kurang_dari_spasi_lebih_dari_tetap_dua_token():
    # Kasus tepi: '< >' berspasi BUKAN '<>'; perbaikan tidak boleh terlalu agresif.
    assert _nilai("a < > b") == ["a", "<", ">", "b"]


def test_operator_lain_tidak_rusak_oleh_perbaikan_tidak_sama_dengan():
    # Kasus tepi: operator 1 dan 2 karakter lain harus tetap utuh.
    assert _nilai("a < b > c = d <= e >= f != g") == [
        "a", "<", "b", ">", "c", "=", "d", "<=", "e", ">=", "f", "!=", "g",
    ]