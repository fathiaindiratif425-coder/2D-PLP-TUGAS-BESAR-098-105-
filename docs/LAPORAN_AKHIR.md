# Laporan Akhir

## 1. Hasil evaluasi

Tempel keluaran `python evaluate.py` setelah `data/ground_truth.csv` dilengkapi.

```
PS C:\Users\aihtaf\2D-PLP-TUGAS-BESAR-098-105->py evaluate.py
Belum berlabel (tidak dievaluasi): pemeliharaan.sql

Dievaluasi: audit.sql, campuran_error.sql, laporan_penjualan.sql (20 triple)

Metode   Precision  Recall     F1
parser        1.00    1.00   1.00
regex         0.68    0.85   0.76

[regex]
  salah ditemukan (FP): ('audit.sql', 16, 'sesi', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 4, 'pesanan', 'R')
  salah ditemukan (FP): ('campuran_error.sql', 8, 'keranjang', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'D')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pelanggan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'pesanan', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 2, 'rahasia', 'R')
  salah ditemukan (FP): ('laporan_penjualan.sql', 15, 'pesanan', 'R')
  terlewat (FN):       ('audit.sql', 2, 'pesanan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pelanggan', 'R')
  terlewat (FN):       ('laporan_penjualan.sql', 3, 'pesanan', 'R')
  
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

Minimal tiga hal yang **tidak bisa** ditangani dengan benar oleh tool ini meskipun semua bug
sudah diperbaiki. Untuk tiap batas: contoh SQL atau situasinya, akibatnya pada CRUD matrix,
dan informasi apa yang dibutuhkan untuk mengatasinya.

1.
2.
3.

## 4. Pembagian kerja

Siapa mengerjakan apa, dan bagaimana kalian memastikan keduanya memahami seluruh kode.