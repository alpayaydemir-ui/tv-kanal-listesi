#!/usr/bin/env python3
"""Ücretsiz Türk TV kanal listesini üretir.

iptv-org'un Türkiye listesini indirir, normalde ücretli olan kanalları çıkarır,
kanalları türlerine ve reytinge göre sıralar ve turkiye-ucretsiz.m3u dosyasına yazar.
Yayınlar burada test edilmez: GitHub sunucuları yurt dışında olduğu için
Türkiye'ye kısıtlı birçok kanal oradan ölü görünür.
"""
import pathlib
import re
import sys
import urllib.request

KAYNAK = "https://iptv-org.github.io/iptv/countries/tr.m3u"
CIKTI = pathlib.Path(__file__).resolve().parent / "turkiye-ucretsiz.m3u"
EN_AZ_KANAL = 50  # kaynak bozuk gelirse mevcut liste korunur

UCRETLI = re.compile(
    r"^(S Sport|Eurosport|BBC (First|Earth)|National Geographic|Viasat|FX \(|Cartoon Network|"
    r"Disney|BabyTV|MovieSmart|CNBC-e)",
    re.I,
)
# Yayıncıya ait olmayan yeniden yayın / aktarma sunucuları
ARACI_SUNUCU = re.compile(
    r"(siteyaptim\.live|onrender\.com|raw\.githubusercontent\.com|smartplaytv\.in|"
    r"digitalbox\.xyz|radyotvonline\.net)(:\d+)?$",
    re.I,
)
# Dini yayın yapan kanallar (Religious etiketi olmayanlar) ve TRT'nin yabancı dil kanalları
LISTE_DISI = {
    "Ilke TV", "Kanal Hayat", "Luys TV", "Sat 7 Turk", "Semerkand TV", "Sercem TV",
    "TRT Arabi", "TRT Avaz", "TRT Diyanet Cocuk", "TRT Kurdi", "Vav TV",
}
# Reyting sırası: canlitv.com aylık tablosu (tarihi doğrulanamadı). Listede olmayanlar alfabetik gelir.
HABER_REYTING = ["TRT Haber", "Halk TV SD", "A Haber", "Haberturk TV", "NTV (Turkiye)",
                 "Haber Global", "TGRT Haber"]
HABER_EK = {"Tele 1", "TVNET (Turkiye)", "Ulke TV"}  # kaynakta News etiketi olmayan haber kanalları
GENEL_REYTING = ["TRT 1", "Kanal D (Turkiye)", "TV8 (Turkiye)"]
GENEL_ALFABETIK = {"ATV (Turkiye)", "Beyaz TV", "Kanal 7", "NOW", "Star TV (Turkiye)"}
MUZIK_EK = {"Power TV (Turkiye)", "PowerTurk TV"}
YABANCI = {"Almahriah TV", "Elsharq TV", "Mekameleen TV", "Persiana Turkiye", "Qaf TV",
           "RTG int.", "Zarok TV"}


def ayristir(metin):
    """Her kanal için (EXTINF satırı, ek satırlar, adres) döndürür."""
    satirlar = metin.splitlines()
    kanallar, i = [], 0
    while i < len(satirlar):
        if satirlar[i].startswith("#EXTINF"):
            j = i + 1
            while j < len(satirlar) and satirlar[j].startswith("#"):
                j += 1
            if j < len(satirlar) and satirlar[j].strip():
                kanallar.append((satirlar[i], satirlar[i + 1:j], satirlar[j].strip()))
            i = j + 1
        else:
            i += 1
    return kanallar


def ad(kanal):
    return kanal[0].rsplit(",", 1)[-1].strip()


def sunucu(kanal):
    return kanal[2].split("/")[2] if kanal[2].count("/") >= 2 else ""


def temiz_ad(kanal):
    return re.sub(r"\s*(\(\d+p\)|\[[^\]]*\])", "", ad(kanal)).strip()


def etiketler(kanal):
    m = re.search(r'group-title="([^"]*)"', kanal[0])
    return set(m.group(1).split(";")) if m else set()


def istenmeyen(kanal):
    return "Religious" in etiketler(kanal) or temiz_ad(kanal) in LISTE_DISI


def sira(kanal):
    """Haber, reyting listesi, spor, diğer, müzik, yabancı; grup içinde reyting ya da alfabe."""
    n, tur = temiz_ad(kanal), etiketler(kanal)
    alfabe = n.casefold()
    if n in YABANCI:
        return (5, 0, alfabe)
    if n in HABER_REYTING:
        return (0, HABER_REYTING.index(n), alfabe)
    if "News" in tur or n in HABER_EK:
        return (0, len(HABER_REYTING), alfabe)
    if n in GENEL_REYTING:
        return (1, GENEL_REYTING.index(n), alfabe)
    if n in GENEL_ALFABETIK:
        return (1, len(GENEL_REYTING), alfabe)
    if "Sports" in tur:
        return (2, 0, alfabe)
    if "Music" in tur or n in MUZIK_EK:
        return (4, 0, alfabe)
    return (3, 0, alfabe)


def main():
    istek = urllib.request.Request(KAYNAK, headers={"User-Agent": "tv-kanal-listesi"})
    with urllib.request.urlopen(istek, timeout=60) as yanit:
        metin = yanit.read().decode("utf-8", errors="replace")
    tum = ayristir(metin)
    ucretsiz = [k for k in tum if not UCRETLI.match(ad(k))]
    resmi = [k for k in ucretsiz if not ARACI_SUNUCU.search(sunucu(k))]
    secili = sorted((k for k in resmi if not istenmeyen(k)), key=sira)
    if len(secili) < EN_AZ_KANAL:
        print(f"Kaynakta yalnızca {len(secili)} kanal var, liste değiştirilmedi.")
        return 1
    with open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        for inf, ekler, adres in secili:
            f.write("\n".join([inf, *ekler, adres]) + "\n")
    print(f"kaynak {len(tum)}, ücretli çıkarıldı {len(tum) - len(ucretsiz)}, "
          f"aracı sunucu çıkarıldı {len(ucretsiz) - len(resmi)}, "
          f"dini/TRT yabancı dil çıkarıldı {len(resmi) - len(secili)}, liste {len(secili)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
