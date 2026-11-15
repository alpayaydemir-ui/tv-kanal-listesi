#!/usr/bin/env python3
"""Ücretsiz Türk TV kanal listesini üretir.

Kaynaklar, öncelik sırasıyla:
  1. ek-kanallar.m3u: elle doğrulanmış yayıncı adresleri
  2. iptv-org'un Türkiye listesi
  3. Keşif: bilinen ve GitHub aramasıyla bulunan Türkçe listeler. Bunlardan yalnızca
     yayıncıların kendi sunucularındaki adresler alınır, sadece eksik kanalları tamamlar.

Normalde ücretli olan kanallar, aracı/yeniden yayın sunucuları, dini yayın yapan kanallar
ve TRT'nin yabancı dil kanalları listeye alınmaz. Kanallar türe ve reytinge göre sıralanır.
Yayınlar burada test edilmez: GitHub sunucuları yurt dışında olduğu için Türkiye'ye
kısıtlı birçok kanal oradan ölü görünür.
"""
import datetime
import json
import os
import pathlib
import re
import sys
import urllib.parse
import urllib.request

KAYNAK = "https://iptv-org.github.io/iptv/countries/tr.m3u"
KLASOR = pathlib.Path(__file__).resolve().parent
CIKTI = KLASOR / "turkiye-ucretsiz.m3u"
EK = KLASOR / "ek-kanallar.m3u"
EN_AZ_KANAL = 50  # kaynak bozuk gelirse mevcut liste korunur

KESIF_DOSYALARI = [
    "https://raw.githubusercontent.com/hayatiptv/iptv/master/index.m3u",
    "https://raw.githubusercontent.com/raalbatros/iptv/main/yeni.m3u",
]
KESIF_ARAMALARI = ["turkiye m3u", "türk tv m3u", "turkish iptv m3u", "turk kanallari m3u8"]
KESIF_GUN = 90  # aramada yalnızca son bu kadar günde güncellenmiş depolar
EN_BUYUK_DOSYA = 3_000_000

# Keşifte kabul edilen sunucular: yayıncıların kendi altyapısı
RESMI_SUNUCU = re.compile(
    r"(^|\.)(daioncdn\.net|medya\.trt\.com\.tr|live\.trt\.com\.tr|turknet\.ercdn\.net|tjk\.org|"
    r"dygdigital\.com|powerapp\.com\.tr|blutv\.com)$|^[a-z0-9]+-live\.ercdn\.net$|"
    r"^[a-z0-9]+-live\.lg\.mncdn\.com$",
    re.I,
)
RESMI_DISI = re.compile(r"^saran-", re.I)  # ücretli kanal paketi sunucusu

UCRETLI = re.compile(
    r"^(S Sport|beIN|Eurosport|BBC (First|Earth)|National Geographic|Viasat|FX\b|Cartoon Network|"
    r"Disney|BabyTV|MovieSmart|CNBC-e|Tabii Spor|Exxen|TOD\b|Smart Spor|Tivibu Spor|D-?Smart)",
    re.I,
)
# Yayıncıya ait olmayan yeniden yayın / aktarma sunucuları
ARACI_SUNUCU = re.compile(
    r"(siteyaptim\.live|onrender\.com|raw\.githubusercontent\.com|smartplaytv\.in|"
    r"digitalbox\.xyz|radyotvonline\.net|ensonhaber\.com|"
    r"85\.117\.61\.84)(:\d+)?$",  # son ikisi: haber sitesi aktarması, Gürcistan'dan CNN Türk aktarması
    re.I,
)
# Dini yayın yapan kanallar (Religious etiketi olmayanlar) ve TRT'nin yabancı dil kanalları
LISTE_DISI = ["Ilke TV", "Kanal Hayat", "Luys TV", "Sat 7 Turk", "Semerkand TV", "Sercem TV",
              "TRT Arabi", "TRT Avaz", "TRT Diyanet Cocuk", "TRT Kurdi", "Vav TV", "Diyanet TV",
              "Lalegul TV", "Kanal 7 Avrupa"]
# Reyting sırası: canlitv.com aylık tablosu (tarihi doğrulanamadı). Listede olmayanlar alfabetik gelir.
HABER_REYTING = ["TRT Haber", "Halk TV", "A Haber", "Haberturk TV", "NTV", "Haber Global",
                 "TGRT Haber"]
HABER_EK = ["Tele 1", "TVNET", "Ulke TV", "Akit TV", "KRT"]  # News etiketi olmayan haber kanalları
GENEL_REYTING = ["TRT 1", "Kanal D", "TV8", "Show TV"]
GENEL_ALFABETIK = ["ATV", "Beyaz TV", "Kanal 7", "NOW", "Star TV"]
SPOR_EK = ["A Spor", "HT Spor", "TJK TV", "FB TV", "TRT Spor", "TRT Spor Yildiz"]
MUZIK_EK = ["Power TV", "PowerTurk TV", "Kral Pop", "Dream Turk", "Number 1"]
YABANCI = ["Almahriah TV", "Elsharq TV", "Mekameleen TV", "Persiana Turkiye", "Qaf TV",
           "RTG int.", "TRT World", "Zarok TV"]
KISALTMA = {"TV", "TRT", "HT", "NTV", "ATV", "CNN", "FB", "TJK", "DHA", "TBMM", "TGRT", "HD", "EBA", "KRT"}
TR = str.maketrans("çğıöşüîâûÇĞİÖŞÜÎÂÛ", "cgiosuiauCGIOSUIAU")
# Aynı kanalın listelerde geçen farklı adları
ESLER = {"a2tv": "a2", "tv8bucuk": "tv85", "trtebaortakul": "trtebaortaokul", "trt3spor": "trt3",
         "powertvakustik": "powerturkakustik", "trtcocukdiyanet": "trtdiyanetcocuk"}


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


def temiz_ad(kanal):
    return re.sub(r"\s*(\(\d+p\)|\[[^\]]*\])", "", ad(kanal)).strip()


def anahtar(isim):
    """Aynı kanalın farklı yazımlarını eşler: 'SHOW TV HD', 'Show TV' -> 'show'."""
    s = isim.translate(TR).casefold().split("/")[0]
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    s = re.sub(r"\b(f?hd|sd|uhd|4k|canli|yayin)\b", " ", s)
    s = re.sub(r"\btv\s*$", "", s.strip())
    s = re.sub(r"[^a-z0-9]", "", s)
    return ESLER.get(s, s)


def anahtarlar(liste):
    return [anahtar(x) for x in liste]


HABER_REYTING_K, HABER_EK_K = anahtarlar(HABER_REYTING), set(anahtarlar(HABER_EK))
GENEL_REYTING_K, GENEL_ALFABETIK_K = anahtarlar(GENEL_REYTING), set(anahtarlar(GENEL_ALFABETIK))
SPOR_EK_K, MUZIK_EK_K = set(anahtarlar(SPOR_EK)), anahtarlar(MUZIK_EK)
YABANCI_K, LISTE_DISI_K = set(anahtarlar(YABANCI)), set(anahtarlar(LISTE_DISI))


def sunucu(kanal):
    return kanal[2].split("/")[2] if kanal[2].count("/") >= 2 else ""


def etiketler(kanal):
    m = re.search(r'group-title="([^"]*)"', kanal[0])
    return set(m.group(1).split(";")) if m else set()


def istenmeyen(kanal):
    k = anahtar(temiz_ad(kanal))
    return "Religious" in etiketler(kanal) or k in LISTE_DISI_K or "diyanet" in k


def sira(kanal):
    """Haber, reyting listesi, spor, diğer, müzik, yabancı; grup içinde reyting ya da alfabe."""
    n, tur = temiz_ad(kanal), etiketler(kanal)
    k, alfabe = anahtar(n), n.translate(TR).casefold()
    if k in YABANCI_K:
        return (5, 0, alfabe)
    if k in HABER_REYTING_K:
        return (0, HABER_REYTING_K.index(k), alfabe)
    if "News" in tur or k in HABER_EK_K:
        return (0, len(HABER_REYTING_K), alfabe)
    if k in GENEL_REYTING_K:
        return (1, GENEL_REYTING_K.index(k), alfabe)
    if k in GENEL_ALFABETIK_K:
        return (1, len(GENEL_REYTING_K), alfabe)
    if "Sports" in tur or k in SPOR_EK_K or "spor" in k:
        return (2, 0, alfabe)
    if "Music" in tur or any(k.startswith(m) for m in MUZIK_EK_K):
        return (4, 0, alfabe)
    return (3, 0, alfabe)


def indir(adres, limit=EN_BUYUK_DOSYA, json_mu=False):
    basliklar = {"User-Agent": "tv-kanal-listesi"}
    if json_mu and os.environ.get("GITHUB_TOKEN"):
        basliklar["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    with urllib.request.urlopen(urllib.request.Request(adres, headers=basliklar), timeout=30) as y:
        veri = y.read(limit + 1)
    if len(veri) > limit:
        raise ValueError("dosya çok büyük")
    return json.loads(veri) if json_mu else veri.decode("utf-8", errors="replace")


def kesif_dosyalari():
    """Bilinen listeler + GitHub'da son günlerde güncellenmiş Türkçe m3u depoları."""
    dosyalar = list(KESIF_DOSYALARI)
    sinir = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=KESIF_GUN)
    for sorgu in KESIF_ARAMALARI:
        try:
            q = urllib.parse.quote(sorgu)
            depolar = indir(f"https://api.github.com/search/repositories?q={q}&sort=updated&per_page=10",
                            json_mu=True)["items"]
        except Exception as e:
            print(f"  arama atlandı ({sorgu}): {e}")
            continue
        for d in depolar:
            if datetime.datetime.fromisoformat(d["pushed_at"].replace("Z", "+00:00")) < sinir:
                continue
            try:
                icerik = indir(f"https://api.github.com/repos/{d['full_name']}/contents", json_mu=True)
            except Exception:
                continue
            m3u = [f["download_url"] for f in icerik
                   if f.get("type") == "file" and re.search(r"\.m3u8?$", f["name"], re.I)]
            dosyalar.extend(m3u[:3])
    return list(dict.fromkeys(dosyalar))


def guzel_ad(isim):
    isim = re.sub(r"\s+\b(F?HD|SD|UHD|4K)\b\s*$", "", isim.strip(), flags=re.I).strip()
    if sum(c.isupper() for c in isim) > sum(c.islower() for c in isim):
        isim = " ".join(w.upper() if w.upper() in KISALTMA or re.search(r"\d", w) else w.capitalize()
                        for w in isim.split())
    return isim


def kesif():
    bulunan = {}
    for adres in kesif_dosyalari():
        try:
            kanallar = ayristir(indir(adres))
        except Exception as e:
            print(f"  kaynak atlandı ({adres}): {e}")
            continue
        for kanal in kanallar:
            h = sunucu(kanal)
            isim = guzel_ad(temiz_ad(kanal))
            k = anahtar(isim)
            if (not k or k in bulunan or not RESMI_SUNUCU.search(h) or RESMI_DISI.search(h)
                    or UCRETLI.match(isim)):
                continue
            bulunan[k] = (f'#EXTINF:-1 group-title="Kesif",{isim}', [], kanal[2])
    return list(bulunan.values())


def main():
    metin = indir(KAYNAK)
    ek = ayristir(EK.read_text(encoding="utf-8")) if EK.exists() else []
    ek_k = {anahtar(temiz_ad(k)) for k in ek}
    tum = [k for k in ayristir(metin) if anahtar(temiz_ad(k)) not in ek_k] + ek
    ucretsiz = [k for k in tum if not UCRETLI.match(ad(k))]
    resmi = [k for k in ucretsiz if not ARACI_SUNUCU.search(sunucu(k))]
    secili = [k for k in resmi if not istenmeyen(k)]

    var = {anahtar(temiz_ad(k)) for k in secili} | {anahtar(temiz_ad(k)) for k in resmi if istenmeyen(k)}
    eklenen = [k for k in kesif() if anahtar(temiz_ad(k)) not in var and not istenmeyen(k)]
    secili = sorted(secili + eklenen, key=sira)

    if len(secili) < EN_AZ_KANAL:
        print(f"Kaynakta yalnızca {len(secili)} kanal var, liste değiştirilmedi.")
        return 1
    with open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write("#EXTM3U\n")
        for inf, ekler, adres in secili:
            f.write("\n".join([inf, *ekler, adres]) + "\n")
    print(f"kaynak {len(tum)}, ücretli çıkarıldı {len(tum) - len(ucretsiz)}, "
          f"aracı sunucu çıkarıldı {len(ucretsiz) - len(resmi)}, "
          f"dini/TRT yabancı dil çıkarıldı {len(resmi) - len([k for k in resmi if not istenmeyen(k)])}, "
          f"keşiften eklenen {len(eklenen)}, liste {len(secili)}")
    if eklenen:
        print("  keşif:", ", ".join(temiz_ad(k) for k in eklenen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
