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
from crud.parser import parse_sql
from crud.resolver import Resolver
from crud.ast_nodes import iter_nodes, ColumnRef


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


# Panic mode (SPEK bagian 6): setelah error, parser membuang token sampai dan
# termasuk ';' lalu lanjut, jadi statement valid sesudahnya tidak ikut hilang.
def test_regresi_panic_mode_lanjut_setelah_titik_koma():
    script = parse_sql("SELECT FROM x; DELETE FROM log; INSERT INTO a VALUES (1);")
    assert len(script.errors) == 1
    assert len(script.statements) == 2


def test_dua_statement_rusak_berurutan_masing_masing_satu_error():
    # Kasus tepi: dua statement rusak berturut-turut, tiap error dilaporkan sendiri.
    script = parse_sql("SELECT FROM a; SELECT FROM b;")
    assert len(script.errors) == 2
    assert len(script.statements) == 0


def test_error_tepat_di_titik_koma_tidak_menelan_statement_berikutnya():
    # Kasus tepi: token yang salah adalah ';' itu sendiri.
    script = parse_sql("SELECT ; DELETE FROM log;")
    assert len(script.errors) == 1
    assert len(script.statements) == 1


# Regresi: LEFT OUTER JOIN ditolak parser ("diharapkan JOIN, ditemukan 'OUTER'"),
# padahal grammar (SPESIFIKASI bagian 3, aturan `join`) membolehkan OUTER opsional
# setelah LEFT.

def test_regresi_left_outer_join_diterima_parser():
    # Bug: _join langsung menuntut JOIN setelah LEFT, padahal grammar
    # (SPESIFIKASI bagian 3) memperbolehkan OUTER opsional.
    script = parse_sql("SELECT a FROM t LEFT OUTER JOIN u ON u.id = t.id")
    assert script.errors == []
    assert [j.kind for j in script.statements[0].joins] == ["LEFT"]


def test_regresi_left_outer_join_berulang_huruf_kecil_dan_crud():
    # Gejala bug: satu join gagal membuat SELURUH statement hilang dari CRUD matrix.
    res = analyze_source(
        "select a from t left outer join u on u.id = t.id "
        "left outer join v on v.id = t.id"
    )
    assert res.parse_errors == []
    assert res.matrix() == {"t": "R", "u": "R", "v": "R"}


def test_jenis_join_lain_tidak_rusak():
    # Kasus tepi: perbaikan tidak boleh mengubah LEFT, INNER, dan JOIN polos.
    kasus = [
        ("SELECT a FROM t LEFT JOIN u ON u.id = t.id", "LEFT"),
        ("SELECT a FROM t INNER JOIN u ON u.id = t.id", "INNER"),
        ("SELECT a FROM t JOIN u ON u.id = t.id", "INNER"),
    ]
    for sql, jenis in kasus:
        script = parse_sql(sql)
        assert script.errors == []
        assert script.statements[0].joins[0].kind == jenis


def test_outer_hanya_boleh_setelah_left():
    # Kasus tepi: grammar `[ "INNER" | "LEFT" [ "OUTER" ] ]`, jadi OUTER
    # tanpa LEFT, atau dua kali OUTER, tetap error.
    for sql in [
        "SELECT a FROM t OUTER JOIN u ON u.id = t.id",
        "SELECT a FROM t INNER OUTER JOIN u ON u.id = t.id",
        "SELECT a FROM t LEFT OUTER OUTER JOIN u ON u.id = t.id",
    ]:
        assert len(parse_sql(sql).errors) == 1