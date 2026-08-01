# Kenapa Tidak Ada `main()` Seperti di Go?

Kalau Anda datang dari Go, wajar bertanya: `main.py` di modul ini isinya
cuma definisi `app = FastAPI(...)` dan kumpulan route — **tidak ada** fungsi
yang aktif "menjalankan" server, seperti `main()` yang memanggil
`server.ListenAndServe()` di Go. Dokumen ini menjelaskan kenapa itu memang
desain yang benar, bukan sesuatu yang kelupaan ditulis.

## Perbandingan Konsep

| | Go | FastAPI (`main.py` modul ini) |
|---|---|---|
| Yang dieksekusi saat file dijalankan | `main()` — aktif, memanggil `server.ListenAndServe(addr, handler)` | Cuma definisi `app` dan route — **pasif**, tidak ada kode yang "memicu jalan" |
| Cara start server | `go run main.go`, atau jalankan binary hasil compile | `uvicorn main:app --reload` — proses **terpisah** yang meng-import `app` |
| Kalau file dieksekusi langsung (`python main.py`) | — | Python jalan top-ke-bawah, definisikan semua, lalu file **selesai** — tidak ada server yang nyala |

## Kode yang Sebenarnya Ada

Di [main.py](main.py), baris 20:

```python
app = FastAPI(title="AI Knowledge Assistant - Modul 2", version="1.0.0")
```

`app` di sini adalah **objek murni** — kumpulan route (`/health`, `/ask`,
`/documents/{doc_id}`, dst) yang didaftarkan lewat decorator seperti
`@app.get(...)`. Objek ini tidak tahu dan tidak peduli bagaimana caranya
nanti dijalankan — tidak ada baris kode di file ini yang membuka socket
atau menerima koneksi.

Yang berperan sebagai pengganti `main()` + `server.Run()` di Go justru ada
di **command yang dipakai untuk menjalankannya** (lihat [README.md](README.md)
atau panduan per OS):

```bash
uvicorn main:app --reload
```

`main:app` artinya "import variabel `app` dari file `main.py`". **Uvicorn**
(ASGI server) yang membuka socket, menerima koneksi TCP, mem-parsing HTTP
request, lalu memanggil `app` untuk tiap request yang masuk — ini persis
tugas `http.ListenAndServe` di Go, hanya saja dijalankan sebagai **command
line tool terpisah dari kode aplikasi**, bukan baris kode di dalam
`main.py` itu sendiri.

## Kenapa Harus Dipisah Begini (Bukan Ditulis Manual)

Kalau mau meniru gaya Go persis, bisa saja ditambahkan di akhir `main.py`:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

Tapi ini **sengaja tidak dilakukan**, karena `app` sebagai objek murni perlu
dipakai ulang di banyak skenario yang **tidak pernah lewat blok
`__main__`**:

1. **Development** — `uvicorn main:app --reload` (yang dipakai di modul ini)
2. **Container/production** (mulai Modul 3) — `CMD` di `Dockerfile`, atau di
   server sungguhan biasanya `gunicorn -k uvicorn.workers.UvicornWorker
   main:app` dengan banyak worker process sekaligus
3. **Testing** — `from fastapi.testclient import TestClient` lalu
   `TestClient(app)`, meng-import `app` langsung tanpa ada server jaringan
   yang benar-benar menyala. Contoh konkretnya ada di
   [test_main_demo.py](test_main_demo.py):

   ```python
   from fastapi.testclient import TestClient
   from main import app

   client = TestClient(app)

   def test_documents_404():
       response = client.get("/documents/999")
       assert response.status_code == 404
   ```

   `TestClient` butuh `pytest` dan `httpx` (belum ada di `requirements.txt`
   utama karena ini demo opsional, bukan bagian materi inti):

   ```bash
   uv pip install pytest httpx
   uv run pytest test_main_demo.py -v -s
   ```

   Test ini tetap
   lolos **walaupun tidak ada `uvicorn` yang jalan dan port 8000 kosong** —
   `TestClient` mensimulasikan request HTTP langsung ke `app` di memori
   (lewat ASGI transport), tanpa membuka socket TCP sungguhan. Ini bukti
   paling jelas kenapa `app` harus tetap jadi objek yang bisa di-import
   sendiri, terlepas dari cara menjalankannya — kalau start-server dipaksa
   masuk ke blok `__main__`, `TestClient` tidak akan pernah menyentuhnya.

Kalau logic start-server dipaksa masuk ke `main.py`, poin 2 dan 3 di atas
tetap tidak memakainya (gunicorn dan `TestClient` tidak pernah menjalankan
`python main.py` secara langsung) — jadi kodenya jadi mati (dead code)
untuk sebagian besar cara pakai yang sebenarnya. Karena itu komunitas
FastAPI/Python production umumnya **tidak** menulis blok
`if __name__ == "__main__": uvicorn.run(...)`, dan mendokumentasikan
perintah run di README — persis pola yang dipakai di kit ini.

## Ringkasan

- `main.py` = **definisi** aplikasi (routes, validasi, dependency) — pasif.
- `uvicorn` (dipanggil dari terminal, atau nanti dari `Dockerfile` di Modul
  3/4) = **entrypoint** yang aktif menjalankan server — perannya setara
  `main()` + `server.Run()` di Go, tapi posisinya di luar kode Python,
  sebagai command terpisah.
- Ini bukan gaya "kurang lengkap", tapi desain standar supaya `app` yang
  sama bisa dipakai untuk dev, production multi-worker, dan test tanpa
  perubahan kode.
