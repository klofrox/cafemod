# CafeMice

Transformice'in Café'sine ek özellikler: engelleme, favoriler, notlar, arşiv ve arama, resim önizleme, ekran görüntüsü, bildirim sesi, GIF avatar, koyu tema, beyaz isimler.

Oyunun kendisi değiştirilmez. Steam'deki Transformice'in yerine küçük bir **yükleyici** konur, oyun bu bilgisayardaki bir **proxy** üzerinden bağlanır. Café paketleri oyuna ulaşmadan önce proxy'de düzenlenir.

> Oyun istemcisini değiştirmek Transformice kurallarına aykırıdır. Kullanan, hesabıyla ilgili riski kendisi alır.

## Kullanım (CafeMice.exe)

1. Transformice Steam'den kurulu olmalı (ücretsiz).
2. `CafeMice.exe`'yi aç. Pencerede modun ve CafeMice'in durumu yazar.
3. **Modu kur ve oyna**: yükleyiciyi Steam klasörüne kurar (orijinali `Transformice.swf.orig` olarak saklar), CafeMice'i başlatır ve oyunu Steam'den açar.
4. Oynarken CafeMice penceresi açık kalmalı (simge durumuna küçültülebilir).
5. **Modu kaldır**: Steam'in kendi dosyasını geri koyar, oyun Steam'den normal açılır.

Komut satırından da çalışır:

| Komut | Ne yapar |
|---|---|
| `CafeMice.exe --kaldir` | Steam'in kendi dosyasını geri koyar |
| `CafeMice.exe --oyunu-acma` | Oyunu açmaz, sadece proxy'yi çalıştırır |
| `CafeMice.exe --oyun-klasoru "D:\...\Transformice"` | Oyun bulunamazsa klasörü elle verir |

Veriler (engel listesi, favoriler, notlar, arşiv) `%APPDATA%\CafeMice` klasöründe durur. Ekran görüntüleri ve indirilen profil resimleri `Resimler\Transformice SS` ve `Resimler\Transformice PP` klasörlerine kaydedilir.

Windows imzasız exe için "Bilinmeyen yayımcı" uyarısı gösterebilir: "Ek bilgi → Yine de çalıştır".

## Nasıl çalışıyor

```
Transformice (Steam/AIR)
  └─ Transformice.swf  = yamalı TFMProxyLoader (tools/loader)
        ├─ asıl oyunu transformice.com'dan indirip içinde çalıştırır
        ├─ oyunun bağlantısını localhost:11801'e çevirir  ──►  cafemice proxy  ──►  oyun sunucusu
        └─ Café arayüzüne butonları ve menüleri ekler, proxy ile 127.0.0.1:11810 üzerinden konuşur
```

### 1. Yükleyici (`tools/loader`)

Temel: [tfm-proxy-loader](https://github.com/friedkeenan/tfm-proxy-loader) 1.6.32 (MIT). Bu SWF oyunu yükler ve bağlantısını yerel proxy'ye yönlendirir.

`tools/loader/build.py`, SWF'i [JPEXS FFDec](https://github.com/jindrapetrik/jpexs-decompiler) ile açar, ActionScript dosyalarına aşağıdaki eklemeleri yapar ve yeniden derler:

- `cafe_sil.as`: Café gönderi menüsüne "Sil", "Favori", "PP indir", "Bildirim aç/kapat", "Not ekle".
- `cafe_panel.as`: arama, bildirim, kamera, yıldız ve engel butonları; arama ve favori panelleri.
- `cafe_extra.as`: beyaz isimler, Discord benzeri gönderi görünümü, alıntı çubukları, bahsetme vurgusu, resim önizleme, "Mesaja git", bildirim sesi, ekran görüntüsü.
- `dark_theme.as`, `flat_ui.as`: koyu tema ve düz arayüz.
- `gif_avatar.as`: GIF avatarların karelerini oynatır.

Yükleyici, oyunun sınıflarını çalışma anında arayıp bulur. Oyun güncellenince bazı özellikler bozulursa önce buraya bakılır.

### 2. Proxy (`cafemice/`)

[caseus](https://github.com/friedkeenan/caseus) üzerine kurulu (Transformice protokol kütüphanesi, `caseus/LICENSE`).

- `cafe_proxy.py`: Café paketlerini (gönderi listesi, konu listesi, yeni gönderi bildirimi) okur. Engellenen oyuncuların gönderilerini, açtıkları konuları, onları alıntılayan gönderileri ve bildirimlerini oyuna ulaşmadan çıkarır. Konu listesi konuyu kimin açtığını söylemez; proxy bunu arka planda konuyu açarak öğrenir.
- `cafe_block.py`: paket ayrıştırma; engel listesi, favoriler, takip listesi, notlar.
- `cafe_archive.py`: görülen her gönderinin SQLite arşivi ve arama (Türkçe harflere duyarlı).
- `cafe_gif.py`: GIF'i karelere bölüp yükleyiciye gönderir.
- `gui.py`: exe penceresi (Modu kur ve oyna / Modu kaldır / durum). Ahşap ve parşömen görünümü kodla çizilir; başlıktaki fare, oyuncunun kendi Steam klasöründeki oyun simgesidir (`icones/128.png`), repoya ya da exe ye girmez.
- `launcher.py`: exe.nin başlangıcı. Steam klasörünü bulur, yükleyiciyi kurar/kaldırır, proxy'yi başlatır, oyunu `steam://rungameid/335240` ile açar.

Yükleyici ile proxy arasındaki komutlar satır satır gider: `BLOCK`, `UNBLOCK`, `FAV`, `PP`, `WATCH`, `SHOT`, `NOTE`, `SEARCH`, `PREVIEW`, `GOTO`, `LIST`. Proxy `STATE`, `TOAST`, `NOTIFY`, `MENTION`, `LINK`, `RESULTS`, `PREVIEW`, `GIF` satırlarıyla cevap verir. Ayrıntılar `cafe_proxy.py`'nin başında.

## Kaynaktan derleme

Gerekenler: Python 3, Java (FFDec için), `pip install pak pillow pyinstaller`.

```powershell
# 1. Yükleyici: FFDec'i indir, yolunu tools/loader/build.py içindeki FFDEC'e yaz
python tools/loader/build.py            # -> build/TFMProxyLoader_sil.swf

# 2. İkon (isteğe bağlı, hazır olanı var)
python tools/exe/make_icon.py

# 3. Exe
python tools/exe/build.py               # -> dist/CafeMice.exe
```

Exe'siz çalıştırmak için: `python -m cafemice` (aynı launcher).

Testler: `python -m pytest tests`

## Lisanslar

- `caseus/`: friedkeenan, `caseus/LICENSE`.
- `tools/loader/TFMProxyLoader-1.6.32.swf`: friedkeenan/tfm-proxy-loader, MIT.
- Transformice ve tüm oyun içeriği Atelier 801'e aittir; bu repo oyun dosyası içermez.
