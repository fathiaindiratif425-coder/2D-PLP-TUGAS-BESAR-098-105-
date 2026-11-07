# Laporan Akhir

## 1. Hasil evaluasi

Tempel keluaran `python evaluate.py` setelah `data/ground_truth.csv` dilengkapi.

```
PS C:\Users\aihtaf\2D-PLP-TUGAS-BESAR-098-105-> py evaluate.py

Dievaluasi: audit.sql, campuran_error.sql, laporan_penjualan.sql, pemeliharaan.sql (27 triple)

Metode   Precision  Recall     F1
parser        1.00    1.00   1.00
regex         0.65    0.81   0.72

[regex]
  salah ditemukan (FP): ('audit.sql', 16, 'sesi', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 4, 'pesanan', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 8, 'keranjang', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'D')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pesanan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'rahasia', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 15, 'pesanan', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'crm.alamat', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'crm.pelanggan', 'R')
  salah ditemukan (FP): ('pemeliharaan.sql', 2, 'pelanggan_lama', 'U')
  salah ditemukan (FP): ('pemeliharaan.sql', 15, 'crm.alamat', 'R')
  terlewat (FN):       ('audit.sql', 2, 'pesanan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pelanggan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pesanan', 'R')
  terlewat (FN):       ('pemeliharaan.sql', 3, 'crm.alamat', 'R')
  terlewat (FN):       ('pemeliharaan.sql', 3, 'crm.pelanggan', 'R')
  
```

## 2. Tiga kasus di mana regex salah

Untuk tiap kasus: SQL-nya, kesalahan regex, dan mengapa parser benar (kaitkan dengan konsep
lexing, parsing, atau resolusi).

1. **Komentar yang berisi kata kunci** (`laporan_penjualan.sql`, baris 2 dan 3).

   ```sql
   -- Laporan penjualan bulanan
   -- DELETE FROM pelanggan   (baris ini komentar, bukan perintah)
   SELECT p.nama, SUM(o.total) AS omzet
   FROM pelanggan p
   JOIN pesanan o ON o.pelanggan_id = p.id
   ```

   *Kesalahan regex.* Regex memotong teks di `;` lalu menganggap kata `SELECT`/`INSERT`/`UPDATE`/`DELETE` pertama sebagai awal statement. Kata `DELETE` di dalam komentar baris 2 ikut terbaca, sehingga statement dianggap mulai di baris 2, bukan baris 3. Akibatnya `pelanggan R` dan `pesanan R` muncul di baris 2 (FP) dan hilang dari baris 3 (FN), dan komentar itu juga menghasilkan `pelanggan D` (FP) padahal baris itu hanya komentar.

   *Mengapa parser benar.* Ini soal **lexing**. Lexer membaca `--` sampai akhir baris dan membuangnya tanpa membuat token, sehingga token pertama statement adalah `SELECT` di baris 3 dan parser tidak pernah melihat isi komentar.

2. **Kata `FROM` di dalam string** (`laporan_penjualan.sql`, baris 2).

   ```sql
   WHERE o.status = 'LUNAS' AND o.catatan <> 'FROM rahasia'
   ```

   *Kesalahan regex.* Pola `FROM\s+nama` cocok dengan isi string, jadi regex melaporkan tabel `rahasia` dengan operasi R (FP), padahal tabel itu tidak ada.

   *Mengapa parser benar.* Ini juga soal **lexing**. Lexer membaca kutip tunggal sampai kutip penutup dan menghasilkan satu token `STRING` bernilai `FROM rahasia`. Bagi parser itu hanya literal di dalam ekspresi, bukan keyword, dan analyzer hanya mengambil tabel dari node tabel di AST.

3. **`DELETE FROM` terhitung dua kali** (`laporan_penjualan.sql` baris 15 dan `campuran_error.sql` baris 8).

   ```sql
   DELETE FROM pesanan WHERE tanggal < :batas;
   DELETE FROM keranjang WHERE dibuat < :batas;
   ```

   *Kesalahan regex.* Pola `DELETE FROM nama` menghasilkan `D` yang benar, tetapi pola `FROM nama` yang terpisah juga cocok pada kata yang sama, sehingga muncul `pesanan R` dan `keranjang R` (FP). Regex tidak punya konteks bahwa `FROM` itu bagian dari `DELETE`.

   *Mengapa parser benar.* Ini soal **parsing**. Grammar `delete_stmt = "DELETE" "FROM" table_name ...` menjadikan `FROM` bagian dari statement DELETE. `_delete` membuat satu node `Delete` dengan satu tabel target, dan analyzer menerapkan aturan SPESIFIKASI §5 (target DELETE hanya `D`).

## 3. Batas pendekatan kami

1. **Kolom tanpa qualifier saat ada lebih dari satu tabel.**

   ```sql
   SELECT nama FROM pelanggan, pesanan;
   ```

   Tanpa skema database, tool tidak tahu `nama` milik `pelanggan` atau `pesanan`. Resolver mengeluarkan warning `kolom 'nama' ambigu tanpa skema` dan `ColumnRef.resolved` tetap `None`. *Akibat pada CRUD matrix:* baris tabel tetap benar karena tabel diambil dari `FROM`, tetapi penggunaan kolom (`--kolom`) kehilangan entri untuk `nama` karena kolom itu tidak bisa ditautkan ke tabel. *Yang dibutuhkan:* skema, yaitu daftar kolom tiap tabel (misalnya dari DDL atau katalog database).

2. **View, trigger, dan stored procedure menyembunyikan efek sebenarnya.**

   ```sql
   SELECT * FROM v_pelanggan_aktif;
   INSERT INTO pesanan (...) VALUES (...);
   ```

   Tool memperlakukan `v_pelanggan_aktif` sebagai tabel biasa, jadi matrix mencatat `v_pelanggan_aktif R`, padahal yang dibaca sebenarnya tabel dasar di balik view itu. Jika `INSERT INTO pesanan` memicu trigger yang menulis ke `log_pesanan` atau mengubah tabel lain, efek C/U/D itu tidak tampak di statement dan tidak masuk matrix. *Akibat pada CRUD matrix:* hasilnya kurang lengkap (efek tersembunyi tidak tercatat) dan bisa memuat nama view sebagai tabel. *Yang dibutuhkan:* definisi view, trigger, dan procedure beserta grafik ketergantungannya. Semua itu DDL, yang di luar lingkup (SPESIFIKASI §9).

3. **`WITH` (CTE) dan `UNION` membuat seluruh statement hilang dari matrix.**

   ```sql
   WITH aktif AS (SELECT * FROM pelanggan) SELECT * FROM aktif;
   SELECT id FROM pelanggan UNION SELECT id FROM pemasok;
   ```

   Grammar tool tidak mengenal `WITH` maupun `UNION`. Statement diawali `WITH` ditolak di `_statement`, dan statement dengan `UNION` menghasilkan error sintaks. Menurut SPESIFIKASI §5, statement yang gagal di-parse tidak dihitung. *Akibat pada CRUD matrix:* semua tabel di dalamnya, termasuk bagian `SELECT` biasa yang sebenarnya bisa dibaca, hilang dari matrix dan hanya muncul sebagai error. *Yang dibutuhkan:* bukan informasi tambahan, melainkan perluasan grammar (CTE sebagai scope tambahan, `UNION` sebagai gabungan dua `SELECT`).

## 4. Pembagian kerja

Kami membagi kode menurut tahap pipeline. Bunga mengerjakan resolver (urutan pencarian scope, scope `DELETE`), parser `INSERT ... SELECT` dan `JOIN` (termasuk `LEFT OUTER JOIN`), kolom tanpa qualifier, serta analyzer. Fathia mengerjakan lexer (normalisasi keyword, komentar blok, `''` di dalam string), panic mode, dan presedensi `AND`/`OR`. Masing-masing bekerja di branch sendiri (`105_Bunga` dan `098_Fathia`) lalu digabung ke `main` lewat Pull Request, dan keduanya aktif sebagai kontributor di riwayat commit.

Supaya keduanya paham seluruh kode, kami memakai empat cara:

- Tiap perbaikan diawali test regresi yang merah, lalu kodenya diperbaiki sampai hijau, sehingga rekan bisa menjalankan test untuk melihat bug dan perbaikannya.
- Bagian akar masalah di `LAPORAN_BUG.md` ditulis dengan kata-kata sendiri, lalu dijelaskan ulang ke rekan.
- Ground truth: Fathia melabeli `audit.sql`, Bunga melabeli `pemeliharaan.sql`, lalu kami saling memeriksa.
