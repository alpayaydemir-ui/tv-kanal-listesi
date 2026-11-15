# tv-kanal-listesi

Türkiye'deki ücretsiz TV kanallarının günlük güncellenen M3U listesi.

- Kaynak: [iptv-org/iptv](https://github.com/iptv-org/iptv), herkese açık yayın adresleri.
- `ek-kanallar.m3u`: iptv-org'da olmayan ya da sorunlu ücretsiz kanallar (Show TV, Star, Teve2, TV 8,5 vb.). Yalnızca yayıncıların kendi sunucularındaki adresler; aynı kanal iki listede varsa bu dosyadaki kullanılır.
- Keşif: bilinen Türkçe listeler ve GitHub'da son 90 günde güncellenmiş Türkçe m3u depoları her gün taranır. Bunlardan yalnızca yayıncıların kendi sunucularındaki (daioncdn, trt.com.tr, ercdn vb.) adresler alınır ve sadece listede olmayan kanallar eklenir.
- Normalde ücretli olan kanallar (S Sport, Eurosport, BBC, National Geographic, FX, Disney vb.) listeye alınmaz.
- Yayıncıya ait olmayan yeniden yayın / aktarma sunucularındaki adresler de çıkarılır.
- Dini yayın yapan kanallar ve TRT'nin yabancı dil kanalları listeye alınmaz.
- Sıra: haber, reyting listesindeki kanallar, spor, diğer kanallar, müzik, yabancı. Grup içinde reyting bilgisi varsa ona göre, yoksa alfabetik.
- GitHub Actions her gün `guncelle.py`'yi çalıştırır, liste değiştiyse kaydeder.

VLC'de açmak için: **Akış (Stream)** > adres:

```
https://raw.githubusercontent.com/alpayaydemir-ui/tv-kanal-listesi/main/turkiye-ucretsiz.m3u
```

Yayınlar burada test edilmez; bazı kanallar zaman zaman çalışmayabilir.
