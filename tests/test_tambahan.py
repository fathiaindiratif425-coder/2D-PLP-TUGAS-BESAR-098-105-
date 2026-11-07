"""Test tambahan buatan kelompok.

Isi dengan:
Test regresi untuk setiap bug yang diperbaiki, ditambah kasus tepi
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


# Presedensi (SPEK 3.1): AND lebih kuat dari OR, jadi a OR b AND c dibaca a OR (b AND c).
def test_regresi_and_lebih_kuat_dari_or():
    script = parse_sql("SELECT x FROM t WHERE a = 1 OR b = 2 AND c = 3")
    where = script.statements[0].where
    assert where.op == "OR"
    assert where.right.op == "AND"


def test_and_lalu_or_dibaca_and_dulu():
    # Kasus tepi: urutannya dibalik, AND tetap diikat duluan.
    script = parse_sql("SELECT x FROM t WHERE a = 1 AND b = 2 OR c = 3")
    where = script.statements[0].where
    assert where.op == "OR"
    assert where.left.op == "AND"


def test_not_lebih_kuat_dari_and():
    # Kasus tepi: NOT mengikat paling kuat, jadi NOT a AND b dibaca (NOT a) AND b.
    script = parse_sql("SELECT x FROM t WHERE NOT a = 1 AND b = 2")
    where = script.statements[0].where
    assert where.op == "AND"
    assert where.left.op == "NOT"


def _resolve_kolom(sql):
    """Parse, resolve, lalu kembalikan ([(nama_kolom, resolved)], [(level, pesan)])."""
    script = parse_sql(sql)
    diag = Resolver().resolve_script(script)
    kolom = [(c.name, c.resolved) for c in iter_nodes(script.statements)
             if isinstance(c, ColumnRef)]
    return kolom, [(d.level, d.message) for d in diag]


# Regresi T1: INSERT ... SELECT sebelumnya ditolak parser ("belum didukung")
# sehingga statement hilang dari CRUD matrix (SPESIFIKASI bagian 3 dan 5).
def test_regresi_insert_select_diurai_dan_dihitung_c_dan_r():
    res = analyze_source("INSERT INTO a (x) SELECT y FROM b WHERE y > 1")
    assert res.parse_errors == []
    assert res.matrix() == {"a": "C", "b": "R"}


# Regresi analyzer: tabel di subquery UPDATE dihitung U, padahal hanya dibaca
# (SPESIFIKASI bagian 5: membaca lewat subquery selalu R).
def test_regresi_update_subquery_di_set_dan_where_dihitung_r():
    res = analyze_source(
        "UPDATE t SET a = (SELECT max(x) FROM u) WHERE id IN (SELECT id FROM v)"
    )
    assert res.matrix() == {"t": "U", "u": "R", "v": "R"}


# Kasus tepi: tabel target juga dibaca lewat subquery, jadi gabungannya "RU"
# (urutan C, R, U, D), bukan "UR" atau hanya "U".
def test_update_subquery_ke_tabel_yang_sama_menjadi_ru():
    res = analyze_source("UPDATE t SET a = 1 WHERE id IN (SELECT id FROM t)")
    assert res.matrix() == {"t": "RU"}


# Regresi T2: kolom tanpa qualifier tidak pernah di-resolve (resolved tetap None).
def test_regresi_kolom_tanpa_qualifier_satu_tabel_teresolusi():
    kolom, diag = _resolve_kolom("SELECT nama FROM crm.pelanggan")
    assert kolom == [("nama", "crm.pelanggan")]
    assert diag == []


# Kasus tepi: dua tabel di scope terdalam -> ambigu, resolved tetap None.
def test_kolom_tanpa_qualifier_dua_tabel_ambigu():
    kolom, diag = _resolve_kolom("SELECT nama FROM a, b")
    assert kolom == [("nama", None)]
    assert any("ambigu" in pesan for _, pesan in diag)


# Kasus tepi: kolom tanpa qualifier hanya melihat scope terdalam, jadi 'k' di
# subquery (dua tabel) tidak boleh "meminjam" tabel dari scope luar.
def test_kolom_tanpa_qualifier_hanya_scope_terdalam():
    kolom, diag = _resolve_kolom(
        "SELECT 1 FROM a x WHERE EXISTS (SELECT 1 FROM b y, c z WHERE k = 1)"
    )
    assert kolom == [("k", None)]
    assert any("ambigu" in pesan for _, pesan in diag)


# Regresi: alias di subquery harus menutupi alias yang sama di luar (shadowing,
# SPESIFIKASI bagian 4.3). Dulu qualifier ter-resolve ke tabel di scope TERLUAR.
def test_regresi_alias_di_subquery_menutupi_alias_luar():
    kolom, diag = _resolve_kolom(
        "SELECT x.id FROM pelanggan x WHERE x.id IN "
        "(SELECT x.pelanggan_id FROM pesanan x WHERE x.total > 5)"
    )
    assert kolom == [("id", "pelanggan"), ("id", "pelanggan"),
                     ("pelanggan_id", "pesanan"), ("total", "pesanan")]
    assert diag == []


# Kasus tepi: tiga tingkat bersarang dengan alias yang sama; yang dipakai
# selalu scope paling dalam, bukan yang paling luar atau tengah.
def test_alias_sama_di_tiga_tingkat_memakai_yang_terdalam():
    kolom, _ = _resolve_kolom(
        "SELECT 1 FROM a x WHERE x.i IN (SELECT 1 FROM b x WHERE x.i IN "
        "(SELECT 1 FROM c x WHERE x.i = 1))"
    )
    assert [t for _, t in kolom] == ["a", "b", "c"]


# Kasus tepi: alias yang tidak ada di subquery tetap dicari ke luar (correlated).
def test_correlated_subquery_tetap_melihat_alias_luar():
    kolom, diag = _resolve_kolom(
        "SELECT p.nama FROM pelanggan p WHERE EXISTS "
        "(SELECT 1 FROM pembayaran b WHERE b.pid = p.id)"
    )
    assert ("id", "pelanggan") in kolom and ("pid", "pembayaran") in kolom
    assert diag == []


# Kasus tepi: alias yang tidak ada di scope mana pun tetap error.
def test_alias_tidak_dikenal_tetap_error():
    kolom, diag = _resolve_kolom("SELECT z.id FROM a x")
    assert diag == [("error", "alias 'z' tidak terdefinisi")]


# Regresi: DELETE membuat scope tetapi tidak pernah menutupnya, sehingga alias
# 's' dari DELETE masih terlihat oleh statement berikutnya (SPESIFIKASI 4.5).
def test_regresi_alias_delete_tidak_bocor_ke_statement_berikutnya():
    kolom, diag = _resolve_kolom(
        "DELETE FROM sesi s WHERE s.k < 1;\n"
        "SELECT s.id FROM pengguna u WHERE u.aktif = 1;"
    )
    assert ("error", "alias 's' tidak terdefinisi") in diag
    assert ("id", None) in kolom


# Kasus tepi: setelah SEMUA jenis statement selesai di-resolve, tidak boleh ada
# scope tersisa (SPESIFIKASI 4.5).
@pytest.mark.parametrize("sql", [
    "SELECT a FROM t",
    "INSERT INTO a (x) SELECT y FROM b",
    "UPDATE t x SET a = 1 WHERE x.id = 2",
    "DELETE FROM t x WHERE x.id = 2",
    "DELETE FROM a x WHERE x.i IN (SELECT 1 FROM b y WHERE y.i = x.i)",
])
def test_tidak_ada_scope_tersisa_setelah_statement_selesai(sql):
    resolver = Resolver()
    resolver.resolve_script(parse_sql(sql))
    assert resolver.scope is None


# Kasus tepi (penjaga): UPDATE juga membuat scope dan sudah menutupnya dengan benar.
def test_alias_update_tidak_bocor_ke_statement_berikutnya():
    kolom, diag = _resolve_kolom("UPDATE t x SET a = 1;\nSELECT x.b FROM u;")
    assert ("error", "alias 'x' tidak terdefinisi") in diag


# String (SPEK 2.4): '' di dalam string berarti satu tanda kutip, bukan akhir string.
def test_regresi_kutip_ganda_di_dalam_string():
    toks = tokenize("'O''Brien'")
    assert toks[0].type == T.STRING
    assert toks[0].value == "O'Brien"


def test_string_kosong_dan_kutip_di_ujung():
    # Kasus tepi: '' sebagai string kosong, dan 'a''' berisi a lalu satu kutip.
    assert tokenize("''")[0].value == ""
    assert tokenize("'a'''")[0].value == "a'"


def test_dua_string_berdampingan_tetap_dua_token():
    # Kasus tepi: 'a' 'b' berspasi BUKAN 'a''b'; perbaikan tidak boleh terlalu agresif.
    toks = [t for t in tokenize("'a' 'b'") if t.type != T.EOF]
    assert [t.value for t in toks] == ["a", "b"]