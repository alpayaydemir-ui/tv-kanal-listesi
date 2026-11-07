#!/usr/bin/env python3
"""Ücretsiz Türk TV kanal listesini üretir.

iptv-org'un Türkiye listesini indirir, normalde ücretli olan kanalları çıkarır,
spor ve ulusal kanalları başa alır ve turkiye-ucretsiz.m3u dosyasına yazar.
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
SPOR = ["A Spor", "TRT Spor", "HTSpor", "TJK TV", "FB TV"]
ULUSAL = ["TRT 1 ", "ATV (Turkiye)", "TV8 (Turkiye)", "Kanal D (Turkiye)", "Star TV", "NOW ",
          "Show Turk", "Kanal 7 ", "Beyaz TV", "360 ", "A2TV", "TRT Haber", "TRT 3", "TV 4 "]


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


def sira(kanal):
    n = ad(kanal) + " "
    for k, p in enumerate(SPOR):
        if n.startswith(p):
            return (0, k, n)
    for k, p in enumerate(ULUSAL):
        if n.startswith(p):
            return (1, k, n)
    return (2, 0, n)


def main():
    istek = urllib.request.Request(KAYNAK, headers={"User-Agent": "tv-kanal-listesi"})
    with urllib.request.urlopen(istek, timeout=60) as yanit:
        metin = yanit.read().decode("utf-8", errors="replace")
    tum = ayristir(metin)
    ucretsiz = [k for k in tum if not UCRETLI.match(ad(k))]
    resmi = sorted((k for k in ucretsiz if not ARACI_SUNUCU.search(sunucu(k))), key=sira)
    if len(resmi) < EN_AZ_KANAL:
        print(f"Kaynakta yalnızca {len(resmi)} kanal var, liste değiştirilmedi.")
        return 1
    with open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        for inf, ekler, adres in resmi:
            f.write("\n".join([inf, *ekler, adres]) + "\n")
    print(f"kaynak {len(tum)}, ücretli çıkarıldı {len(tum) - len(ucretsiz)}, "
          f"aracı sunucu çıkarıldı {len(ucretsiz) - len(resmi)}, liste {len(resmi)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
