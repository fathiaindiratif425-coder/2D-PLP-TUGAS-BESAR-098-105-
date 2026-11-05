# Log Penggunaan AI

Catat setiap penggunaan AI atau coding agent yang memengaruhi kode atau laporan.

| No | Siapa | Prompt / tugas (ringkas) | Hasil: diterima, diubah, atau ditolak | Alasan | Cara verifikasi |
|---|---|---|---|---|---|
|1| Bunga | Minta penjelasan deskripsi tugas ETS dan SPESIFIKASI.md: apa yang dikerjakan, output, dan pembagian tugas berdua | Diterima, pembagian peran driver/navigator kami sesuaikan sendiri | Ringkasan sesuai dokumen soal; pembagian peran perlu disesuaikan dengan jadwal kami | Dicocokkan dengan Deskripsi Tugas dan SPESIFIKASI.md |
|2| Bunga |	Panduan setup repo, pytest, CLI, dan --ast, lalu memetakan 5 test yang gagal ke tahap pipeline | Diterima | Urutan kerja jelas dan sesuai alur lexer, parser, resolver, analyzer | Perintah dijalankan sendiri di laptop; hasil 5 failed dan 25 passed cocok dengan pemetaan |
|3| Bunga |	Menyusun test regresi bug <> dan menelusuri laporan_penjualan.sql baris 6| Diterima | Menunjukkan bahwa sumber bug ada di lexer, bukan parser | tokenize("a <> b") lewat coba.py menghasilkan dua token; tiga test baru merah sebelum perbaikan |
|4| Bunga |	Bentuk perbaikan cabang < di lexer.py (cek = lalu >)| Diterima | Sesuai SPESIFIKASI 2.5 (maximal munch) dan tidak mengubah a < > b | 10 test di test_tambahan.py hijau; error test_matrix_laporan_penjualan berpindah dari baris 6 ke baris 10 |
|5| Bunga |	Meninjau versi 2 kode kami terhadap spesifikasi untuk mencari bug tersisa dan kekurangan pengerjaan| Diterima sebagai daftar kerja | Setiap bug disertai input pemicu dan rujukan bagian spesifikasi |Untuk bug LEFT OUTER JOIN direproduksi sendiri lewat pemeliharaan.sql dan test. Bug lain direproduksi lewat test regresi masing-masing saat dikerjakan |
|6| Bunga |	Test regresi dan perbaikan LEFT OUTER JOIN (satu baris _match_kw("OUTER") di cabang LEFT)| Diterima; komentar test kami ubah sendiri | Cabang LEFT sesuai grammar dan tidak menerima OUTER JOIN atau INNER OUTER JOIN | python -m pytest penuh 45 passed; error pemeliharaan.sql berpindah dari baris 5 ke baris 6 |
|7| Bunga |Menyusun draf entri LAPORAN_BUG.md, baris LOG_AI.md, dan test regresi tambahan| Diterima, lalu dibaca ulang dan dicocokkan dengan kode | Bagian akar masalah harus kata-kata sendiri dan diuji lisan |Draf dibaca ulang dan dicocokkan dengan kode dan hasil test sebelum di-commit|
|8| Bunga |	Mengerjakan T1 (INSERT ... SELECT), perbaikan analyzer UPDATE, dan T2 (kolom tanpa qualifier) dengan bantuan AI| Diterima |	Sesuai SPESIFIKASI bagian 3 (insert_stmt), 4.3 (kolom tanpa qualifier), dan 5 (aturan CRUD) | Test terlihat test_insert_select, test_kolom_tanpa_qualifier_satu_tabel, dan test_matrix_laporan_penjualan yang awalnya gagal lalu lulus; ditambah test regresi di tests/test_tambahan.py |

**Refleksi (3-5 kalimat).** Di bagian mana AI paling membantu? Di mana AI keliru atau
menyesatkan, dan bagaimana kalian mengetahuinya?
