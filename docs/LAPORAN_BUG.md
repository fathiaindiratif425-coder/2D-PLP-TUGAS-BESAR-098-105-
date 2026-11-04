# Laporan Bug

Salin blok di bawah untuk setiap bug. Bagian **Akar masalah** wajib ditulis dengan kata-kata
sendiri dan memakai konsep dari *Crafting Interpreters* (sebutkan bab). Bagian ini diuji lisan.

---

## Bug 1: (judul singkat)

**Ditemukan oleh:** (nama) · **Diperbaiki oleh:** (nama)

**Gejala.** Input, output yang didapat, dan output yang diharapkan menurut SPESIFIKASI.md
(sebutkan bagiannya).

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql

```

**Akar masalah.** Mengapa kode lama salah? Konsep apa yang dilanggar?

**Perbaikan.** File dan fungsi yang diubah, serta alasannya. Sebutkan juga perbaikan
alternatif yang kalian pertimbangkan dan alasan tidak memilihnya.

**Test regresi.** Nama test di `tests/test_tambahan.py` yang gagal sebelum perbaikan dan lulus
sesudahnya.

**Peran AI.** Apakah AI membantu menemukan atau memperbaiki bug ini? Bagaimana kalian
memverifikasinya?

---

## Bug 1: Keyword huruf kecil dikenali sebagai IDENT

**Ditemukan oleh:** Fathia (driver) dan Bunga (navigator) **Diperbaiki oleh:** Fathia

**Gejala.** `tokenize("select id from t")` menghasilkan token pertama bertipe `IDENT` dengan nilai `select`. Menurut SPESIFIKASI.md bagian 2.2, pencocokan keyword tidak peka huruf besar/kecil dan nilai token keyword disimpan dalam huruf besar, jadi seharusnya `KEYWORD` dengan nilai `SELECT`. Test terlihat `test_keyword_huruf_kecil` gagal.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
select 1
```

**Akar masalah.** Lexer membaca satu kata utuh (select), lalu mengecek apakah kata itu ada di daftar KEYWORDS. Isi daftar itu semuanya huruf besar ("SELECT"). Python membandingkan huruf apa adanya, jadi "select" dianggap beda dari "SELECT", tidak ketemu di daftar, dan jatuh jadi IDENT. Kode lupa mengubah kata ke huruf besar dulu sebelum dicek. Bahasa Lox peka huruf besar kecil tapi SQL tidak, jadi harus dibenarkan.

**Perbaikan.** Di lexer.py fungsi `_word`, teks kata diubah ke huruf besar (`upper = text.upper()`) sebelum dicek ke `KEYWORDS`. Token keyword disimpan dengan nilai huruf besar, tapi `IDENT` tetap memakai teks asli. Alternatif yang dipertimbangkan adalah memeriksa awalan kata. Tidak dipilih karena `selection` dan `fromage` bakal salah dikenali sebagai keyword, kata dibaca utuh dulu, baru dicocokkan.

**Test regresi.** est_regresi_keyword_campur_huruf_dinormalisasi` (gagal sebelum perbaikan, lulus sesudahnya) dan `test_ident_berawalan_keyword_tetap_ident` (kasus tepi).


**Peran AI.** AI membantu menunjuk lokasi bug di `_word` dan menyarankan bentuk perbaikan. Diverifikasi dengan menjalankan test regresi sebelum perbaikan (merah) dan sesudahnya (hijau), serta `python -m pytest` penuh.

---

## Bug 1: Komentar blok `/* ... */` belum didukung (TODO T3)

**Ditemukan oleh:** Fathia (driver) dan Bunga (navigator) **Diperbaiki oleh:** Fathia

**Gejala.** `tokenize("/* komentar\n dua baris */ SELECT")` melempar `LexError: komentar blok belum didukung`. Menurut SPESIFIKASI.md bagian 2.3, komentar blok boleh lintas baris, tidak bersarang, tidak menghasilkan token, dan yang tidak ditutup adalah `LexError`. Test terlihat `test_komentar_blok` gagal.

**Reproduksi minimal.** SQL terpendek yang memicu bug:

```sql
/* a */ SELECT 1
```

**Akar masalah.** Ini bukan bug logika, tapi bagian yang memang belum ditulis. Di _scan_token, ketika lexer ketemu /*, kodenya langsung raise LexError karena isinya masih TODO(T3). Padahal komentar itu cuma lexeme yang harus dibaca sampai penutup */, lalu dibuang tanpa menambah token. Bedanya dengan komentar -- (berhenti di akhir baris): komentar blok berhenti di */, bisa lintas baris, dan harus melempar error kalau file habis sebelum penutup ketemu.

**Perbaikan.** Di `crud/lexer.py` fungsi `_scan_token`, cabang `/*` diganti dengan loop yang membaca karakter sampai menemukan `*/` memakai `_peek()` dan `_peek(1)` (mengintip dua karakter tanpa maju). Jika input habis sebelum penutup, dilempar `LexError("komentar blok tidak ditutup")`. Setelah penutup ditemukan, fungsi `return` tanpa menambah token. Alternatif: regular expression `/\*.*?\*/`. Tidak dipilih karena lexer ini dibangun karakter demi karakter dan pelacakan baris/kolom lewat `_advance( ` tetap benar.


**Test regresi.** `test_regresi_komentar_blok_lintas_baris_tidak_jadi_token`,
`test_komentar_blok_tidak_ditutup_adalah_lexerror`, dan
`test_komentar_blok_boleh_berisi_bintang` (kasus tepi).

**Peran AI.** AI membantu menjelaskan spesifikasi 2.3 dan menyusun kerangka loop. Diverifikasi dengan test: tiga test regresi merah sebelum perbaikan (kecuali kasus tidak ditutup yang lulus kebetulan karena semua komentar blok melempar `LexError`), hijau sesudahnya.

---

---
## Bug 1: Panic mode membuang seluruh sisa input

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
