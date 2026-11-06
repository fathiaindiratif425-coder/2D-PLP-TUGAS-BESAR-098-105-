# Laporan Bug

## Bug 1: Keyword huruf kecil dikenali sebagai IDENT

**Ditemukan oleh:** Fathia (driver) dan Bunga (navigator) **Diperbaiki oleh:** Fathia

**Gejala.** `tokenize("select id from t")` menghasilkan token pertama bertipe `IDENT` dengan nilai `select`. Menurut SPESIFIKASI.md bagian 2.2, pencocokan keyword tidak peka huruf besar/kecil dan nilai token keyword disimpan dalam huruf besar, jadi seharusnya `KEYWORD` dengan nilai `SELECT`. Test terlihat `test_keyword_huruf_kecil` gagal.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
select 1
```

**Akar masalah.** Lexer membaca satu kata utuh (select), lalu mengecek apakah kata itu ada di daftar KEYWORDS. Isi daftar itu semuanya huruf besar ("SELECT"). Python membandingkan huruf apa adanya, jadi "select" dianggap beda dari "SELECT", tidak ketemu di daftar, dan jatuh jadi IDENT. Kode lupa mengubah kata ke huruf besar dulu sebelum dicek. Bahasa Lox peka huruf besar kecil tapi SQL tidak, jadi harus dibenarkan.

**Perbaikan.** Di lexer.py fungsi `_word`, teks kata diubah ke huruf besar (`upper = text.upper()`) sebelum dicek ke `KEYWORDS`. Token keyword disimpan dengan nilai huruf besar, tapi `IDENT` tetap memakai teks asli. Alternatif yang dipertimbangkan adalah memeriksa awalan kata. Tidak dipilih karena `selection` dan `fromage` bakal salah dikenali sebagai keyword, kata dibaca utuh dulu, baru dicocokkan.

**Test regresi.** test_regresi_keyword_campur_huruf_dinormalisasi` (gagal sebelum perbaikan, lulus sesudahnya) dan `test_ident_berawalan_keyword_tetap_ident` (kasus tepi).


**Peran AI.** AI membantu menunjuk lokasi bug di `_word` dan menyarankan bentuk perbaikan. Diverifikasi dengan menjalankan test regresi sebelum perbaikan (merah) dan sesudahnya (hijau), serta `python -m pytest` penuh.

---

## Bug 2: Komentar blok `/* ... */` belum didukung (TODO T3)

**Ditemukan oleh:** Fathia (driver) dan Bunga (navigator) **Diperbaiki oleh:** Fathia

**Gejala.** `tokenize("/* komentar\n dua baris */ SELECT")` melempar `LexError: komentar blok belum didukung`. Menurut SPESIFIKASI.md bagian 2.3, komentar blok boleh lintas baris, tidak bersarang, tidak menghasilkan token, dan yang tidak ditutup adalah `LexError`. Test terlihat `test_komentar_blok` gagal.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
/* a */ SELECT 1
```

**Akar masalah.** Ini bukan bug logika, tapi bagian yang memang belum ditulis. Di _scan_token, ketika lexer ketemu /*, kodenya langsung raise LexError karena isinya masih TODO(T3). Padahal komentar itu cuma lexeme yang harus dibaca sampai penutup */, lalu dibuang tanpa menambah token. Bedanya dengan komentar -- (berhenti di akhir baris): komentar blok berhenti di */, bisa lintas baris, dan harus melempar error kalau file habis sebelum penutup ketemu.

**Perbaikan.** Di `crud/lexer.py` fungsi `_scan_token`, cabang `/*` diganti dengan loop yang membaca karakter sampai menemukan `*/` memakai `_peek()` dan `_peek(1)` (mengintip dua karakter tanpa maju). Jika input habis sebelum penutup, dilempar `LexError("komentar blok tidak ditutup")`. Setelah penutup ditemukan, fungsi `return` tanpa menambah token. Alternatif: regular expression `/\*.*?\*/`. Tidak dipilih karena lexer ini dibangun karakter demi karakter dan pelacakan baris/kolom lewat `_advance() ` tetap benar.


**Test regresi.** `test_regresi_komentar_blok_lintas_baris_tidak_jadi_token`,
`test_komentar_blok_tidak_ditutup_adalah_lexerror`, dan
`test_komentar_blok_boleh_berisi_bintang` (kasus tepi).

**Peran AI.** AI membantu menjelaskan spesifikasi 2.3 dan menyusun kerangka loop. Diverifikasi dengan test: tiga test regresi merah sebelum perbaikan (kecuali kasus tidak ditutup yang lulus kebetulan karena semua komentar blok melempar `LexError`), hijau sesudahnya.

---
## Bug 3: Panic mode membuang seluruh sisa input

**Ditemukan oleh:** Fathia (driver) dan Bunga (navigator) **Diperbaiki oleh:** Fathia

**Gejala.** `parse_sql("SELECT FROM x; DELETE FROM log; INSERT INTO a VALUES (1);")` menghasilkan 1 error dan **0 statement**. Menurut SPESIFIKASI.md bagian 6, setelah error parser membuang token sampai dan termasuk `;` berikutnya lalu melanjutkan, sehingga dua statement valid setelahnya harus tetap diproses (1 error, 2 statement). Bug ini tidak tertangkap test terlihat.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
SELECT FROM x; DELETE FROM log;
```

**Akar masalah.** Setelah error, parser perlu “pulih” supaya bisa lanjut membaca. Caranya: lompati token sampai ketemu titik aman. Di SQL, titik aman adalah ; karena itu pemisah antar statement. Tapi _synchronize yang lama tidak punya titik berhenti, jadi ia membuang token sampai akhir file. Akibatnya DELETE FROM log; yang sebenarnya valid ikut terbuang. Parser sengaja melompat ke batas statement supaya bisa melaporkan error lain yang nyata, bukan error berantai atau hilang total.

**Perbaikan.** Di `crud/parser.py` fungsi `_synchronize`, loop kini berhenti setelah membuang token `;` (`if self._advance().type == T.SEMICOLON: return`). Alternatif: berhenti *sebelum* `;`. Tidak dipilih karena spesifikasi bagian 6 meminta `;` ikut dibuang.


**Test regresi.** `test_regresi_panic_mode_lanjut_setelah_titik_koma` (awalnya sempat gagal karena `NameError`; setelah import `parse_sql` ditambahkan gagal dengan `assert 0 == 2`, lulus sesudah perbaikan).

**Peran AI.** AI membantu menemukan bug dengan membandingkan `_synchronize` dengan spesifikasi bagian 6 dan menyarankan bentuk perbaikan. Diverifikasi dengan test yang gagal dulu karena alasan yang benar, lalu `python -m pytest` penuh hijau.

---

## Bug 4: Operator `<>` dipecah menjadi dua token

**Ditemukan oleh:** Bunga (driver) dan Fathia (navigator) **Diperbaiki oleh:** Bunga

**Gejala.** `tokenize("a <> b")` menghasilkan empat token (`a`, `<`, `>`, `b`). Menurut SPESIFIKASI.md bagian 2.5, `<>` adalah satu token `OP` (maximal munch), jadi seharusnya tiga token. Akibatnya `analyze_source` pada `laporan_penjualan.sql` gagal dengan `Baris 6, kolom 41: diharapkan ekspresi, ditemukan '>'`, dan test terlihat `test_matrix_laporan_penjualan` gagal.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
SELECT id FROM t WHERE x <> 'a'
```

**Akar masalah.** Di `_scan_token`, cabang untuk karakter `<` hanya mengecek satu kemungkinan perpanjangan, yaitu `=` (menjadi `<=`). Kemungkinan `>` (menjadi `<>`) tidak dicek. Menurut konsep maximal munch (Crafting Interpreters bab 4), lexer harus mengambil lexeme terpanjang yang cocok, dan `<>` lebih panjang daripada `<`. Karena `<` sudah dikeluarkan sendiri, karakter `>` diproses sebagai token baru. Parser hanya menerima token dari lexer, jadi ia tidak pernah melihat `<>`; ia melihat `<` lalu `>`, dan mengeluh karena `>` tidak bisa memulai ekspresi. Gejalanya muncul di parser, tetapi penyebabnya ada di lexer.

**Perbaikan.** Di `crud/lexer.py`, fungsi `_scan_token`, cabang `<` sekarang mengecek `=` lalu `>`: `<=` jika diikuti `=`, `<>` jika diikuti `>`, selain itu `<`. `_match` hanya melihat karakter yang persis di sebelah `<`, jadi `a < > b` (berspasi) tetap menjadi dua token. Alternatif yang dipertimbangkan: (1) menambal parser agar menerima `<` yang diikuti `>` sebagai "tidak sama". Tidak dipilih karena akar masalahnya di lexer, dan parser seharusnya tidak menebak gabungan token. (2) tabel operator yang dicocokkan dari yang terpanjang. Tidak dipilih karena terlalu berat untuk satu operator tambahan dan mengubah banyak kode yang sudah benar.

**Test regresi.** `test_regresi_tidak_sama_dengan_satu_token` dan `test_regresi_tidak_sama_dengan_di_where_tidak_error_parser` (gagal sebelum perbaikan, lulus sesudahnya). Kasus tepi yang menjaga perilaku: `test_tidak_sama_dengan_tanpa_spasi_dan_posisinya`, `test_kurang_dari_spasi_lebih_dari_tetap_dua_token`, dan `test_operator_lain_tidak_rusak_oleh_perbaikan_tidak_sama_dengan`.

**Peran AI.** AI membantu menunjukkan bahwa sumber bug ada di lexer (bukan parser) dengan cara menghitung kolom 41 dan membandingkan hasil `tokenize` dengan spesifikasi 2.5, menyusun test regresi, dan mengusulkan bentuk perbaikan. Diverifikasi dengan menjalankan test sebelum perbaikan (tiga test `<>` merah, dua test penjaga hijau) dan sesudahnya (10 test di `test_tambahan.py` hijau). Selain itu, error `test_matrix_laporan_penjualan` berpindah dari baris 6 ke baris 10 (`INSERT ... SELECT`), yang menandakan bug `<>` sudah beres.

---

## Bug 5: `INSERT ... SELECT` belum didukung (TODO T1)

**Ditemukan oleh:** Bunga dan Fathia (dari hasil `pytest` awal di kedua laptop dan penanda `TODO(T1)` di kode) **Diperbaiki oleh:** Bunga

**Gejala.** `parse_sql("INSERT INTO arsip (id) SELECT id FROM pesanan")` menghasilkan `ParseError: INSERT ... SELECT belum didukung, ditemukan 'SELECT'` dan nol statement. Menurut SPESIFIKASI.md bagian 3 (`insert_stmt`), setelah daftar kolom boleh diikuti `VALUES ...` atau `select_stmt`, dan menurut bagian 5, tabel target dihitung C dan tabel sumber R. Test terlihat `test_insert_select` gagal, dan `test_matrix_laporan_penjualan` ikut gagal dengan `Baris 10, kolom 1: INSERT ... SELECT belum didukung`.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
INSERT INTO a SELECT x FROM b
```

**Akar masalah.** Ini bukan bug logika, tetapi bagian yang memang belum ditulis (TODO T1). Grammar `insert_stmt` punya dua alternatif setelah daftar kolom, tetapi `_insert` baru menerjemahkan alternatif `VALUES`. Pada cabang `SELECT`, kode hanya melempar `ParseError`. Dalam recursive descent (Crafting Interpreters bab 6), tiap aturan grammar menjadi satu fungsi dan aturan boleh memanggil aturan lain. `select_stmt` sudah punya fungsi `_select`, sehingga alternatif kedua cukup memanggilnya.

**Perbaikan.** Di `crud/parser.py`, fungsi `_insert`, cabang `SELECT` sekarang mengembalikan `ast.Insert(table, columns, [], self._select(), line=start.line)` (`values` kosong, `query` berisi `Select`). Resolver dan analyzer sudah menangani `ins.query`: resolver memberi `SELECT` itu scope sendiri (SPESIFIKASI 4.1), dan analyzer menghitung target C serta sumber R. Alternatif: menulis ulang pengurai `SELECT` khusus untuk `INSERT`. Tidak dipilih karena menduplikasi kode dan berisiko berbeda dari `_select` yang sudah teruji.

**Test regresi.** Test terlihat `test_insert_select` (di `tests/test_parser.py`) dan `test_matrix_laporan_penjualan`. Di `tests/test_tambahan.py`: `test_regresi_insert_select_diurai_dan_dihitung_c_dan_r` (gagal sebelum perbaikan, lulus sesudahnya).

**Peran AI.** AI dipakai untuk membantu menyelesaikan bagian ini (cabang `SELECT` di `_insert`). Diverifikasi dengan test terlihat `test_insert_select` dan `test_matrix_laporan_penjualan` yang awalnya gagal lalu lulus, serta test regresi di `tests/test_tambahan.py` yang gagal pada kode asli dan lulus sesudah perbaikan, ditambah `python -m pytest` penuh hijau.

---

## Bug 6: Subquery di `SET` dan `WHERE` pada `UPDATE` dihitung U, bukan R

**Ditemukan oleh:** Bunga dan Fathia **Diperbaiki oleh:** Bunga

**Gejala.** `analyze_source("UPDATE t SET a = (SELECT max(x) FROM u) WHERE id IN (SELECT id FROM v)").matrix()` menghasilkan `{'t': 'U', 'u': 'U', 'v': 'U'}`. Menurut SPESIFIKASI.md bagian 5, tabel target `UPDATE` dihitung U, sedangkan tabel yang dibaca lewat subquery (di `SET` maupun `WHERE`) selalu R, apa pun jenis statement luarnya. Seharusnya `{'t': 'U', 'u': 'R', 'v': 'R'}`. Bug ini tidak tertangkap test terlihat.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
UPDATE t SET a = 1 WHERE id IN (SELECT id FROM t)
```

(hasil lama `U`, seharusnya `RU`, karena `t` ditulis dan juga dibaca lewat subquery.)

**Akar masalah.** Di `analyze_statement`, cabang `ast.Update` memanggil `_collect(..., "U")` untuk ekspresi di `SET` dan `WHERE`. `_collect` menandai **semua** tabel di subquery dengan operasi yang diberikan, sehingga tabel subquery ikut ditandai U. Operasi U hanya berlaku untuk tabel target. Tabel di dalam subquery hanya dibaca, jadi operasinya R. Kesalahannya ada pada operasi yang diteruskan ke penelusur AST, bukan pada penelusurannya.

**Perbaikan.** Di `crud/analyzer.py`, fungsi `analyze_statement`, cabang `ast.Update`: dua pemanggilan `_collect` diubah dari `"U"` menjadi `"R"`. Tabel target tetap ditandai `U` lewat `usage[stmt.table.name].add("U")`. Alternatif: membuat `_collect` bisa membedakan target dan sumber sendiri. Tidak dipilih karena perubahan sekecil mengganti argumen sudah cukup dan tidak menyentuh struktur fungsi.

**Test regresi.** `test_regresi_update_subquery_di_set_dan_where_dihitung_r` (gagal sebelum perbaikan dengan hasil `{'t': 'U', 'u': 'U', 'v': 'U'}`, lulus sesudahnya) dan kasus tepi `test_update_subquery_ke_tabel_yang_sama_menjadi_ru`.

**Peran AI.** AI dipakai untuk membantu menemukan dan memperbaiki bug ini. Diverifikasi dengan test regresi di `tests/test_tambahan.py` yang gagal pada kode asli dan lulus sesudah perbaikan, serta `python -m pytest` penuh hijau.

---

## Bug 7: Kolom tanpa qualifier tidak di-resolve (TODO T2)

**Ditemukan oleh:** Bunga dan Fathia (dari hasil `pytest` awal di kedua laptop dan penanda `TODO(T2)` di kode) **Diperbaiki oleh:** Bunga

**Gejala.** Pada `SELECT nama FROM pelanggan WHERE aktif = 1`, `ColumnRef.resolved` bernilai `None` untuk `nama` dan `aktif`. Menurut SPESIFIKASI.md bagian 4.3, kolom tanpa qualifier hanya melihat scope terdalam: bila tepat satu tabel, kolom di-resolve ke tabel itu (di sini `pelanggan`), bila lebih dari satu tabel muncul warning `kolom 'nama' ambigu tanpa skema` dengan `resolved` tetap `None`, dan bila tidak ada tabel muncul warning. Test terlihat `test_kolom_tanpa_qualifier_satu_tabel` gagal.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
SELECT nama FROM pelanggan
```

**Akar masalah.** Ini bagian yang memang belum ditulis (TODO T2). Di `Resolver._column`, kolom dengan qualifier sudah ditangani lalu fungsi `return`. Untuk kolom tanpa qualifier, fungsi hanya berisi komentar dan `pass`, sehingga tidak ada yang mengisi `resolved` maupun diagnostik. Konsepnya adalah lexical scope (Crafting Interpreters bab 11): nama dicari di scope yang berlaku. Untuk kolom tanpa qualifier, aturannya hanya scope terdalam. Itu bisa ditentukan dari jumlah entri di scope tersebut, yaitu satu, banyak, atau nol.

**Perbaikan.** Di `crud/resolver.py`, fungsi `_column`: ambil entri milik scope terdalam (`self.scope.entries`). Bila tepat satu, isi `col.resolved = _target_of(entry)`. Bila lebih dari satu, beri warning ambigu. Bila kosong, beri warning "tidak punya tabel". Alternatif: bila tidak ketemu di scope terdalam, lanjut mencari ke scope luar. Tidak dipilih karena spesifikasi 4.3 tegas bahwa kolom tanpa qualifier hanya melihat scope terdalam. Kelemahannya: kolom correlated yang ditulis tanpa qualifier tidak bisa di-resolve ke tabel di luar.

**Test regresi.** Test terlihat `test_kolom_tanpa_qualifier_satu_tabel` (di `tests/test_resolver.py`). Di `tests/test_tambahan.py`: `test_regresi_kolom_tanpa_qualifier_satu_tabel_teresolusi` (gagal sebelum perbaikan, lulus sesudahnya), serta kasus tepi `test_kolom_tanpa_qualifier_dua_tabel_ambigu` dan `test_kolom_tanpa_qualifier_hanya_scope_terdalam`.

**Peran AI.** AI dipakai untuk membantu menyelesaikan bagian ini (cabang kolom tanpa qualifier di `_column`). Diverifikasi dengan test terlihat `test_kolom_tanpa_qualifier_satu_tabel` yang awalnya gagal lalu lulus, serta test regresi di `tests/test_tambahan.py` yang gagal pada kode asli dan lulus sesudah perbaikan.

---

## Bug 8: `LEFT OUTER JOIN` ditolak parser

**Ditemukan oleh:** Bunga (driver) dan Fathia (navigator); ditemukan lewat tinjauan AI terhadap kode, lalu direproduksi dengan test regresi dan `pemeliharaan.sql` **Diperbaiki oleh:** Bunga

**Gejala.** `parse_sql("SELECT a FROM t LEFT OUTER JOIN u ON u.id = t.id")` menghasilkan `ParseError: diharapkan JOIN, ditemukan 'OUTER'` dan nol statement. Menurut SPESIFIKASI.md bagian 3, aturan `join = [ "INNER" | "LEFT" [ "OUTER" ] ] "JOIN" ...` membolehkan `OUTER` opsional setelah `LEFT`. Karena error ini, seluruh statement hilang dari CRUD matrix; pada `data/sample/pemeliharaan.sql` baris 5 muncul `Baris 5, kolom 6: diharapkan JOIN, ditemukan 'OUTER'`. Bug ini tidak tertangkap test terlihat.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
SELECT a FROM t LEFT OUTER JOIN u ON u.id = t.id
```

**Akar masalah.** Parser recursive descent menerjemahkan grammar ke kode (Crafting Interpreters bab 5 dan 6): tiap elemen opsional `[ ... ]` menjadi `match` yang tidak dituntut, sedangkan elemen wajib menjadi `expect`. Di `_join`, setelah `LEFT` dimakan, kode langsung memanggil `_expect_kw("JOIN")` dan tidak menerjemahkan `[ "OUTER" ]`. Akibatnya token `OUTER` dianggap salah, parser melempar error, dan statement yang memuat join itu gagal seluruhnya sehingga tidak dihitung di CRUD matrix.

**Perbaikan.** Di `crud/parser.py`, fungsi `_join`: satu baris `self._match_kw("OUTER")` ditambahkan **di dalam cabang `LEFT`**, sebelum `_expect_kw("JOIN")`. Penempatan di dalam cabang penting supaya `OUTER` hanya diterima setelah `LEFT`, sesuai grammar. Alternatif: menaruh `_match_kw("OUTER")` di luar `if`, sebelum `_expect_kw("JOIN")`. Tidak dipilih karena `OUTER JOIN` dan `INNER OUTER JOIN` yang salah menurut grammar ikut diterima.

**Test regresi.** `test_regresi_left_outer_join_diterima_parser` dan `test_regresi_left_outer_join_berulang_huruf_kecil_dan_crud` (gagal sebelum perbaikan, lulus sesudahnya). Penjaga kasus tepi: `test_jenis_join_lain_tidak_rusak` (LEFT, INNER, dan JOIN polos tidak berubah) dan `test_outer_hanya_boleh_setelah_left` (OUTER tanpa LEFT, setelah INNER, atau ganda tetap error).

**Peran AI.** AI menemukan bug ini saat meninjau kode terhadap spesifikasi, menyusun test, dan mengusulkan bentuk perbaikan. Diverifikasi dengan menjalankan test sebelum perbaikan (dua test regresi merah, dua test penjaga hijau) dan sesudahnya (`python -m pytest` penuh hijau, 45 passed). Error `pemeliharaan.sql` juga berpindah dari baris 5 (`OUTER`) ke baris 6 (`'O''Brien'`), yaitu bug lain yang berbeda.

---


## Bug 9: AND dan OR diperlakukan setara (presedensi salah)

**Ditemukan oleh:** Fathia (driver) dan Bunga (navigator) **Diperbaiki oleh:** Fathia

**Gejala.**  `a = 1 OR b = 2 AND c = 3` dibaca parser sebagai `(a = 1 OR b = 2) AND c = 3` (operator paling luar `AND`). Menurut SPESIFIKASI.md bagian 3.1, `AND` mengikat lebih kuat daripada `OR`, jadi seharusnya `a = 1 OR (b = 2 AND c = 3)` (operator paling luar `OR`). Pohon AST yang dihasilkan salah. Bug ini tidak tertangkap test terlihat 

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
SELECT x FROM t WHERE a = 1 OR b = 2 AND c = 3
```

**Akar masalah.** Pada fungsi _logical di parser.py, operator AND dan OR diproses dalam satu loop yang sama, sehingga keduanya diperlakukan setara dan dibaca dari kiri ke kanan. Akibatnya, ekspresi a = 1 OR b = 2 AND c = 3 terbaca sebagai (a = 1 OR b = 2) AND c = 3, padahal pada SQL AND memiliki presedensi lebih tinggi daripada OR, seperti perkalian terhadap penjumlahan, sehingga seharusnya terbaca a = 1 OR (b = 2 AND c = 3).

**Perbaikan.** Di `crud/parser.py`, `_logical` dipecah menjadi dua fungsi: `_or` yang memanggil `_and` untuk kedua sisinya, dan `_and` yang memanggil `_not`. `_expr` kini memanggil `_or`. Dengan begitu `AND` selalu terikat lebih dulu daripada `OR`, sesuai grammar (`or_expr` dibangun dari `and_expr`, yang dibangun dari `not_expr`). Alternatif yang dipertimbangkan: precedence climbing atau parser Pratt dengan tabel binding power. Tidak dipilih karena fungsi lain di parser ini (`_additive`, `_multiplicative`) sudah memakai pola satu fungsi per tingkat, jadi perbaikannya konsisten dan lebih mudah dicocokkan dengan grammar.

**Test regresi.** `test_regresi_and_lebih_kuat_dari_or` (gagal sebelum perbaikan dengan `assert 'AND' == 'OR'`, lulus sesudahnya). Kasus tepi: `test_and_lalu_or_dibaca_and_dulu` dan `test_not_lebih_kuat_dari_and`.

**Peran AI.** AI membantu menunjukkan lokasi bug di `_logical` dengan membandingkan kode dengan spesifikasi 3.1 dan menyarankan bentuk perbaikan. Diverifikasi dengan test yang gagal dulu karena alasan yang benar (`AND` vs `OR`), lalu `python -m pytest` penuh hijau (50 passed).

---
## Bug 10: Qualifier dicari dari scope terluar, bukan dari scope terdalam

**Ditemukan oleh:** Bunga (driver) dan Fathia (navigator); ditemukan lewat tinjauan AI terhadap kode, lalu direproduksi dengan test regresi **Diperbaiki oleh:** Bunga

**Gejala.** Pada `SELECT x.id FROM pelanggan x WHERE x.id IN (SELECT x.pelanggan_id FROM pesanan x WHERE x.total > 5)`, `x.pelanggan_id` dan `x.total` di dalam subquery ter-resolve ke `pelanggan` (tabel di luar), padahal alias `x` di subquery milik `pesanan`. Pada tiga tingkat subquery dengan alias yang sama, ketiganya ter-resolve ke tabel paling luar (`['a', 'a', 'a']`, seharusnya `['a', 'b', 'c']`). Menurut SPESIFIKASI.md bagian 4.3, qualifier dicari mulai dari scope terdalam ke luar dan yang pertama ditemukan dipakai, sehingga alias di subquery menutupi alias yang sama di luar (shadowing). Bug ini muncul di `data/sample/audit.sql` baris 14 dan tidak tertangkap test terlihat. CRUD matrix tidak berubah, tetapi `ColumnRef.resolved` salah sehingga keluaran `--kolom` (penggunaan kolom per tabel) ikut salah.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
SELECT 1 FROM a x WHERE x.i IN (SELECT 1 FROM b x WHERE x.i = 1)
```

**Akar masalah.** Di `Resolver._lookup`, daftar scope (`chain`) disusun dari scope aktif lalu naik lewat `parent`, jadi urutannya terdalam dulu. Tetapi daftar itu kemudian diperiksa dengan `reversed(chain)`, sehingga yang diperiksa pertama justru scope terluar. Karena fungsi mengembalikan entri pertama yang cocok, alias di scope luar selalu menang dan alias di subquery tidak pernah sempat diperiksa. Konsepnya adalah scope chain pada resolver (Crafting Interpreters bab 11): variabel dicari mulai dari scope terdalam lalu naik ke luar, sehingga deklarasi yang paling dekat menutupi yang lebih jauh.

**Perbaikan.** Di `crud/resolver.py`, fungsi `_lookup`: `for scope in reversed(chain)` diubah menjadi `for scope in chain`. Rantai sudah berurutan benar (terdalam dulu), jadi cukup dibaca apa adanya. Correlated subquery tetap bekerja, karena alias yang tidak ada di scope dalam tetap ditemukan di scope luar. Alternatif: menelusuri `parent` langsung dalam satu loop tanpa daftar `chain`. Tidak dipilih karena perubahannya lebih besar dan tidak memberi manfaat tambahan.

**Test regresi.** `test_regresi_alias_di_subquery_menutupi_alias_luar` dan `test_alias_sama_di_tiga_tingkat_memakai_yang_terdalam` (gagal sebelum perbaikan, lulus sesudahnya). Penjaga perilaku yang sudah benar: `test_correlated_subquery_tetap_melihat_alias_luar` dan `test_alias_tidak_dikenal_tetap_error`.

**Peran AI.** AI menemukan bug ini saat meninjau kode terhadap spesifikasi 4.3, menyusun test regresi, dan mengusulkan bentuk perbaikan. Diverifikasi dengan menjalankan test sebelum perbaikan (dua test merah dengan hasil `['a', 'a', 'a']` dan `pelanggan_id` ter-resolve ke `pelanggan`, dua test penjaga hijau) dan sesudahnya (`python -m pytest` penuh hijau).

---

## Bug 11: `DELETE` tidak menutup scope-nya, alias bocor ke statement berikutnya

**Ditemukan oleh:** Bunga (driver) dan Fathia (navigator); ditemukan lewat tinjauan AI terhadap kode, lalu direproduksi dengan test regresi **Diperbaiki oleh:** Bunga

**Gejala.** Setelah `DELETE FROM sesi s WHERE s.k < 1;`, statement berikutnya `SELECT s.id FROM pengguna u WHERE u.aktif = 1;` tidak menghasilkan diagnostik apa pun, padahal alias `s` tidak ada di statement itu. Menurut SPESIFIKASI.md bagian 4.5, setiap statement berdiri sendiri: setelah satu statement selesai di-resolve tidak boleh ada scope tersisa, dan alias statement sebelumnya tidak boleh terlihat. Seharusnya muncul `error: alias 's' tidak terdefinisi`. Kasus ini ada di `data/sample/audit.sql` baris 16 dan 18. Setelah `DELETE`, `Resolver.scope` juga tidak bernilai `None`. Bug ini tidak tertangkap test terlihat.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
DELETE FROM sesi s WHERE s.k < 1;
SELECT s.id FROM pengguna u;
```

**Akar masalah.** `Resolver._select` dan `Resolver._update` memanggil `_push()` di awal dan `_pop()` di akhir, tetapi `_delete` hanya memanggil `_push()` dan lupa `_pop()`. Scope milik `DELETE` tertinggal sebagai `self.scope`, lalu scope statement berikutnya dibuat sebagai anaknya. Akibatnya alias dari `DELETE` masih ditemukan lewat rantai induk, seolah-olah statement berikutnya berada di dalam `DELETE`. Konsepnya adalah scope sebagai tumpukan (stack) pada resolver (Crafting Interpreters bab 11): setiap `beginScope` harus berpasangan dengan `endScope`, kalau tidak, scope menumpuk dan kebocoran terbawa ke bagian lain.

**Perbaikan.** Di `crud/resolver.py`, fungsi `_delete`: ditambahkan `self._pop()` di akhir fungsi, sehingga sama seperti `_select` dan `_update`. Alternatif: mengatur ulang `self.scope = None` di awal tiap statement dalam `resolve_script`. Tidak dipilih karena itu hanya menyembunyikan gejala tanpa memperbaiki fungsi yang menyebabkannya, dan bisa merusak scope bersarang di tempat lain.

**Test regresi.** `test_regresi_alias_delete_tidak_bocor_ke_statement_berikutnya` dan `test_tidak_ada_scope_tersisa_setelah_statement_selesai` (parametrize untuk SELECT, INSERT ... SELECT, UPDATE, dan dua bentuk DELETE; kasus DELETE gagal sebelum perbaikan, lulus sesudahnya). Penjaga: `test_alias_update_tidak_bocor_ke_statement_berikutnya` (UPDATE sudah benar sejak awal).

**Peran AI.** AI menemukan bug ini saat meninjau kode terhadap spesifikasi 4.5, menyusun test regresi, dan mengusulkan bentuk perbaikan. Diverifikasi dengan membuktikan test merah sebelum perbaikan: baris `self._pop()` dinonaktifkan sementara dengan tanda `#`, hasilnya 3 failed dan 34 passed (`assert ... in []` dan `assert <Scope object> is None`), lalu baris dikembalikan dan `python -m pytest` penuh hijau.

---

## Bug 12: Dua tanda kutip tunggal berurutan ('') di dalam string memutus string

**Ditemukan oleh:** Fathia (driver) dan Bunga (navigator) **Diperbaiki oleh:** Fathia

**Gejala.** `tokenize("'O''Brien'")` menghasilkan dua token `STRING` (`O` dan `Brien`), padahal SPESIFIKASI.md bagian 2.4 menyatakan `''` di dalam string berarti satu tanda kutip, sehingga seharusnya satu token bernilai `O'Brien`. Dampak lanjutannya, kueri `SELECT id FROM pelanggan WHERE nama = 'O''Brien'` ditolak parser dengan pesan
`diharapkan ';' di akhir statement, ditemukan 'Brien'`, sehingga statement itu hilang dari CRUD matrix. Bug ini tidak tertangkap test terlihat.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
SELECT 'O''Brien'
```

**Akar masalah.** Di _string yang lama, begitu lexer membaca ', ia langsung berhenti, tanpa melihat karakter sesudahnya. Jadi di 'O''Brien', kutip pertama sesudah O dianggap penutup, dan kutip yang langsung menyusul dianggap pembuka string baru (Brien). Hasilnya dua token STRING berurutan, dan parser tidak tahu apa yang harus dilakukan dengan dua string yang berdempetan. Di Lox, string berakhir di kutip pertama dan memang tidak ada escape, jadi cara langsung berhenti sudah cukup. SQL berbeda: '' berarti satu kutip di dalam string, jadi lexer harus mengintip dulu sebelum memutuskan.

**Perbaikan.** Di `crud/lexer.py` fungsi `_string`, saat membaca `'`, lexer mengintip karakter berikutnya dengan `_peek()`. Jika karakter berikutnya juga `'`, keduanya dibaca dan satu `'` ditambahkan ke isi string, lalu loop dilanjutkan. Jika bukan, `'` itu adalah penutup string. Alternatif yang dipertimbangkan: menangani `\'` (escape dengan backslash) seperti bahasa lain. Tidak dipilih karena spesifikasi 2.4 menetapkan `''` sebagai aturan escape SQL.

**Test regresi.** `test_regresi_kutip_ganda_di_dalam_string` (gagal sebelum perbaikan dengan `assert 'O' == "O'Brien"`, lulus sesudahnya). Kasus tepi:
`test_string_kosong_dan_kutip_di_ujung` dan `test_dua_string_berdampingan_tetap_dua_token`.

**Peran AI.** AI membantu menunjukkan lokasi bug di `_string` dengan membandingkannya dengan spesifikasi 2.4 dan menyarankan bentuk perbaikan. Diverifikasi dengan test yang gagal dulu karena alasan yang benar (hasil `'O'` bukan `"O'Brien"`), lalu `python -m pytest` penuh hijau (70 passed).


---
