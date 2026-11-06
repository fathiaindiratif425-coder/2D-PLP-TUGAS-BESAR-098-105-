# Kartu Desain

Tuliskan lima keputusan desain penting dalam pekerjaan kalian. Untuk tiap keputusan, sebutkan
alternatif yang ditolak dan alasannya. Contoh topik (boleh memilih yang lain):

- bagaimana parser membedakan `*` sebagai "semua kolom" dan sebagai perkalian;
- di mana dan bagaimana presedensi `AND`/`OR` dinyatakan;
- mengapa error recovery berhenti di `;`, bukan di keyword `SELECT` berikutnya;
- urutan pencarian scope dan akibatnya pada shadowing serta correlated subquery;
- mengapa kolom tanpa qualifier hanya dilihat di scope terdalam, dan apa kelemahannya;
- bagaimana implementasi `INSERT ... SELECT` atau komentar blok kalian.

| No | Keputusan | Alternatif yang ditolak | Alasan |
| --- | --- | --- | --- |
| 1 | Komentar blok dibaca di lexer: pada `_scan_token`, cabang `/*` memakai loop yang mengintip dengan `_peek()` dan `_peek(1)` sampai ketemu `*/`, membuang isinya tanpa membuat token, dan melempar `LexError("komentar blok tidak ditutup")` (dengan baris dan kolom pembuka) jika input habis. | Menghapus komentar dengan regex `/\*.*?\*/` (atau tahap praproses sebelum lexer). | Lexer ini membaca karakter demi karakter dan `_advance()` menjaga baris dan kolom tetap benar; praproses regex menggeser posisi token dan sulit mendeteksi komentar yang tidak ditutup. Karena komentar tidak menghasilkan token, `DELETE FROM pelanggan` di dalam komentar tidak pernah sampai ke parser, berbeda dengan baseline regex. |
| 2 | Panic mode: `_synchronize` membuang token sampai dan termasuk `;` berikutnya, lalu `parse_script` lanjut ke statement setelahnya. | Berhenti di keyword awal statement berikutnya (`SELECT`, `INSERT`, dan seterusnya). | Sesuai SPESIFIKASI §6, `;` adalah satu-satunya batas statement yang pasti. Keyword `SELECT` juga muncul di tengah statement (subquery dan `INSERT ... SELECT`), jadi berhenti di sana bisa membuat sisa statement rusak dibaca sebagai statement baru yang tampak valid dan menambah tabel palsu di matrix. Dengan `;`, satu statement rusak menghasilkan tepat satu error. |
| 3 | Presedensi dinyatakan lewat struktur fungsi, satu fungsi per tingkat: `_or` memanggil `_and`, lalu `_not`, `_comparison`, `_additive`, dan seterusnya. Operator tingkat lebih tinggi diikat lebih dulu karena dipanggil lebih dalam, sehingga `a = 1 OR b = 2 AND c = 3` menjadi `a = 1 OR (b = 2 AND c = 3)`. | Satu fungsi biner yang memperlakukan `AND` dan `OR` setara dan membaca kiri ke kanan (itu bug awal kami, Bug 9), atau tabel presedensi dengan precedence climbing. | Satu fungsi per tingkat meniru grammar di SPESIFIKASI §3 satu lawan satu, jadi mudah dicocokkan dan diperiksa. Tingkat hanya tujuh, sehingga tabel presedensi belum perlu. `BETWEEN a AND b` aman karena batas bawahnya dibaca `_additive`, bukan `_expr`, sehingga `AND` milik `BETWEEN` tidak diambil `_and`. |
| 4 | | | |
| 5 | | | |