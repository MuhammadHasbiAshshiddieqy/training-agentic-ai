# Kenapa Tidak Ada `main()` Seperti di Go?

Kalau Anda datang dari Go, wajar bertanya: `main.py` di modul ini isinya
cuma definisi `app = FastAPI(...)` dan kumpulan route — **tidak ada** fungsi
yang aktif "menjalankan" server, seperti `main()` yang memanggil
`server.ListenAndServe()` di Go. Dokumen ini menjelaskan kenapa itu memang
desain yang benar, bukan sesuatu yang kelupaan ditulis.

## Perbandingan Konsep

| | Go | FastAPI (`app/main.py` modul ini) |
|---|---|---|
| Yang dieksekusi saat file dijalankan | `main()` — aktif, memanggil `server.ListenAndServe(addr, handler)` | Cuma definisi `app` dan route — **pasif**, tidak ada kode yang "memicu jalan" |
| Cara start server | `go run main.go`, atau jalankan binary hasil compile | `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` — proses **terpisah** yang meng-import `app` |
| Kalau file dieksekusi langsung (`python main.py`) | — | Python jalan top-ke-bawah, definisikan semua, lalu file **selesai** — tidak ada server yang nyala |

## Kode yang Sebenarnya Ada

Di [app/main.py](app/main.py), baris 21:

```python
app = FastAPI(title="AI Knowledge Assistant - Modul 3", version="2.0.0")
```

`app` di sini adalah **objek murni** — kumpulan route (`/health`, `/ask`,
`/db-check`, dst) yang didaftarkan lewat decorator seperti `@app.get(...)`.
Objek ini tidak tahu dan tidak peduli bagaimana caranya nanti dijalankan.

Yang berperan sebagai pengganti `main()` + `server.Run()` di Go justru ada
di [Dockerfile](Dockerfile), baris terakhir:

```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Tapi ini **sengaja tidak dilakukan**, karena `app` sebagai objek murni perlu
dipakai ulang di banyak skenario yang **tidak pernah lewat blok
`__main__`**:

1. **Development** — `uvicorn main:app --reload` (dijalankan manual, dari
   terminal host, di modul 2)
2. **Container/production** — `CMD` di `Dockerfile` di atas, atau di server
   sungguhan biasanya `gunicorn -k uvicorn.workers.UvicornWorker main:app`
   dengan banyak worker process sekaligus
3. **Testing** — `from fastapi.testclient import TestClient` lalu
   `TestClient(app)`, meng-import `app` langsung tanpa ada server jaringan
   yang benar-benar menyala

Kalau logic start-server dipaksa masuk ke `main.py`, poin 2 dan 3 di atas
tetap tidak memakainya (gunicorn dan `TestClient` tidak pernah menjalankan
`python main.py` secara langsung) — jadi kodenya jadi mati (dead code)
untuk sebagian besar cara pakai yang sebenarnya. Karena itu komunitas
FastAPI/Python production umumnya **tidak** menulis blok
`if __name__ == "__main__": uvicorn.run(...)`, dan mendokumentasikan
perintah run di README/Dockerfile/Makefile — persis pola yang dipakai di
kit ini.

## Ringkasan

- `main.py` = **definisi** aplikasi (routes, validasi, dependency) — pasif.
- `uvicorn` (dipanggil dari `Dockerfile` atau terminal) = **entrypoint**
  yang aktif menjalankan server — perannya setara `main()` + `server.Run()`
  di Go, tapi posisinya di luar kode Python, sebagai command terpisah.
- Ini bukan gaya "kurang lengkap", tapi desain standar supaya `app` yang
  sama bisa dipakai untuk dev, production multi-worker, dan test tanpa
  perubahan kode.
