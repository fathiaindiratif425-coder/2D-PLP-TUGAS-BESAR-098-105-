"""Test tambahan buatan kelompok.

Isi dengan:
1. Satu test regresi untuk setiap bug yang kalian perbaiki (gagal sebelum perbaikan,
   lulus sesudahnya). Beri nama yang menjelaskan bug-nya.
2. Lima test kasus tepi, masing-masing dengan komentar singkat mengapa kasus itu berisiko.
"""

import pytest
from crud.lexer import LexError
from crud.lexer import tokenize, TokenType as T


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