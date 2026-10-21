import io
import re
import zipfile
from datetime import datetime, date

# Türkiye 81 İl ve İlçe Haritası (Bağımsız - app.py bağımlılığı yoktur)
UDF_IL_ILCE = {
    "Adana": ["Merkez", "Aladağ", "Ceyhan", "Çukurova", "Feke", "İmamoğlu", "Karaisalı", "Karataş", "Kozan", "Pozantı", "Saimbeyli", "Sarıçam", "Seyhan", "Tufanbeyli", "Yumurtalık", "Yüreğir"],
    "Adıyaman": ["Merkez", "Besni", "Çelikhan", "Gerger", "Gölbaşı", "Kahta", "Samsat", "Sincik", "Tut"],
    "Afyonkarahisar": ["Merkez", "Başmakçı", "Bayat", "Bolvadin", "Çay", "Çobanlar", "Dazkırı", "Dinar", "Emirdağ", "Evciler", "Hocalar", "İhsaniye", "İscehisar", "Kızılören", "Sandıklı", "Sinanpaşa", "Sultandağı", "Şuhut"],
    "Ağrı": ["Merkez", "Diyadin", "Doğubayazıt", "Eleşkirt", "Hamur", "Patnos", "Taşlıçay", "Tutak"],
    "Amasya": ["Merkez", "Göynücek", "Gümüşhacıköy", "Hamamözü", "Merzifon", "Suluova", "Taşova"],
    "Ankara": ["Merkez", "Akyurt", "Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere", "Çankaya", "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı", "Güdül", "Haymana", "Kalecik", "Kahramankazan", "Keçiören", "Kızılcahamam", "Mamak", "Nallıhan", "Polatlı", "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle"],
    "Antalya": ["Merkez", "Akseki", "Aksu", "Alanya", "Demre", "Döşemealtı", "Elmalı", "Finike", "Gazipaşa", "Gündoğmuş", "İbradı", "Kaş", "Kemer", "Kepez", "Konyaaltı", "Korkuteli", "Kumluca", "Manavgat", "Muratpaşa", "Serik"],
    "Artvin": ["Merkez", "Ardanuç", "Arhavi", "Borçka", "Hopa", "Kemalpaşa", "Murgul", "Şavşat", "Yusufeli"],
    "Aydın": ["Merkez", "Bozdoğan", "Buharkent", "Çine", "Didim", "Efeler", "Germencik", "İncirliova", "Karacasu", "Karpuzlu", "Koçarlı", "Köşk", "Kuşadası", "Kuyucak", "Nazilli", "Söke", "Sultanhisar", "Yenipazar"],
    "Balıkesir": ["Merkez", "Altıeylül", "Karesi", "Ayvalık", "Balya", "Bandırma", "Bigadiç", "Burhaniye", "Dursunbey", "Edremit", "Erdek", "Gömeç", "Gönen", "Havran", "İvrindi", "Kepsut", "Manyas", "Marmara", "Savaştepe", "Sındırgı", "Susurluk"],
    "Bilecik": ["Merkez", "Bozüyük", "Gölpazarı", "İnhisar", "Osmaneli", "Pazaryeri", "Söğüt", "Yenipazar"],
    "Bingöl": ["Merkez", "Adaklı", "Genç", "Karlıova", "Kiğı", "Solhan", "Yayladere", "Yedisu"],
    "Bitlis": ["Merkez", "Adilcevaz", "Ahlat", "Güroymak", "Hizan", "Mutki", "Tatvan"],
    "Bolu": ["Merkez", "Dörtdivan", "Gerede", "Göynük", "Kıbrıscık", "Mengen", "Mudurnu", "Seben", "Yeniçağa"],
    "Burdur": ["Merkez", "Ağlasun", "Altınyayla", "Bucak", "Çavdır", "Çeltikçi", "Gölhisar", "Karamanlı", "Kemer", "Tefenni", "Yeşilova"],
    "Bursa": ["Merkez", "Büyükorhan", "Gemlik", "Gürsu", "Harmancık", "İnegöl", "İznik", "Karacabey", "Keles", "Kestel", "Mudanya", "Mustafakemalpaşa", "Nilüfer", "Orhaneli", "Orhangazi", "Osmangazi", "Yenişehir", "Yıldırım"],
    "Çanakkale": ["Merkez", "Ayvacık", "Bayramiç", "Biga", "Bozcaada", "Çan", "Eceabat", "Ezine", "Gelibolu", "Gökçeada", "Lapseki", "Yenice"],
    "Çankırı": ["Merkez", "Atkaracalar", "Bayramören", "Çerkeş", "Eldivan", "Ilgaz", "Kızılırmak", "Korgun", "Kurşunlu", "Orta", "Şabanözü", "Yapraklı"],
    "Çorum": ["Merkez", "Alaca", "Bayat", "Boğazkale", "Dodurga", "İskilip", "Kargı", "Laçin", "Mecitözü", "Oğuzlar", "Ortaköy", "Osmancık", "Sungurlu", "Uğurludağ"],
    "Denizli": ["Merkez", "Acıpayam", "Babadağ", "Baklan", "Bekilli", "Beyağaç", "Bozkurt", "Buldan", "Çal", "Çameli", "Çardak", "Çivril", "Güney", "Honaz", "Kale", "Merkezefendi", "Pamukkale", "Sarayköy", "Serinhisar", "Tavas"],
    "Diyarbakır": ["Merkez", "Bağlar", "Bismil", "Çermik", "Çınar", "Çüngüş", "Dicle", "Eğil", "Ergani", "Hani", "Hazro", "Kayapınar", "Kocaköy", "Kulp", "Lice", "Silvan", "Sur", "Yenişehir"],
    "Edirne": ["Merkez", "Enez", "Havsa", "İpsala", "Keşan", "Lalapaşa", "Meriç", "Süloğlu", "Uzunköprü"],
    "Elazığ": ["Merkez", "Ağın", "Alacakaya", "Arıcak", "Baskil", "Karakoçan", "Keban", "Kovancılar", "Maden", "Palu", "Sivrice"],
    "Erzincan": ["Merkez", "Çayırlı", "İliç", "Kemah", "Kemaliye", "Otlukbeli", "Refahiye", "Tercan", "Üzümlü"],
    "Erzurum": ["Merkez", "Aşkale", "Aziziye", "Çat", "Hınıs", "Horasan", "İspir", "Karaçoban", "Karayazı", "Köprüköy", "Narman", "Oltu", "Olur", "Palandöken", "Pasinler", "Pazaryolu", "Şenkaya", "Tekman", "Tortum", "Uzundere", "Yakutiye"],
    "Eskişehir": ["Merkez", "Alpu", "Beylikova", "Çifteler", "Günyüzü", "Han", "İnönü", "Mahmudiye", "Mihalgazi", "Mihalıççık", "Odunpazarı", "Sarıcakaya", "Seyitgazi", "Sivrihisar", "Tepebaşı"],
    "Gaziantep": ["Merkez", "Araban", "İslahiye", "Karkamış", "Nizip", "Nurdağı", "Oğuzeli", "Şahinbey", "Şehitkamil", "Yavuzeli"],
    "Giresun": ["Merkez", "Alucra", "Bulancak", "Çamoluk", "Çanakçı", "Dereli", "Doğankent", "Espiye", "Eynesil", "Görele", "Güce", "Keşap", "Piraziz", "Şebinkarahisar", "Tirebolu", "Yağlıdere"],
    "Gümüşhane": ["Merkez", "Kelkit", "Köse", "Kürtün", "Şiran", "Torul"],
    "Hakkâri": ["Merkez", "Çukurca", "Derecik", "Şemdinli", "Yüksekova"],
    "Hatay": ["Merkez", "Altınözü", "Antakya", "Arsuz", "Belen", "Defne", "Dörtyol", "Erzin", "Hassa", "İskenderun", "Kırıkhan", "Kumlu", "Payas", "Reyhanlı", "Samandağ", "Yayladağı"],
    "Isparta": ["Merkez", "Aksu", "Atabey", "Eğirdir", "Gelendost", "Gönen", "Keçiborlu", "Senirkent", "Sütçüler", "Şarkikaraağaç", "Uluborlu", "Yalvaç", "Yenişarbademli"],
    "Mersin": ["Merkez", "Akdeniz", "Anamur", "Aydıncık", "Bozyazı", "Çamlıyayla", "Erdemli", "Gülnar", "Mezitli", "Mut", "Silifke", "Tarsus", "Toroslar"],
    "İstanbul": ["Çağlayan", "Anadolu", "Bakırköy", "Büyükçekmece", "Küçükçekmece", "Gaziosmanpaşa", "Beykoz", "Silivri", "Çatalca", "Şile", "Merkez", "Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beylikdüzü", "Beyoğlu", "Çekmeköy", "Esenler", "Esenyurt", "Eyüpsultan", "Fatih", "Güngören", "Kadıköy", "Kağıthane", "Kartal", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer", "Sultanbeyli", "Sultangazi", "Şişli", "Tuzla", "Ümraniye", "Üsküdar", "Zeytinburnu"],
    "İzmir": ["Merkez", "Aliağa", "Balçova", "Bayındır", "Bayraklı", "Bergama", "Beydağ", "Bornova", "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Güzelbahçe", "Karabağlar", "Karaburun", "Karşıyaka", "Kemalpaşa", "Kınık", "Kiraz", "Konak", "Menderes", "Menemen", "Narlıdere", "Ödemiş", "Seferihisar", "Selçuk", "Tire", "Torbalı", "Urla"],
    "Kars": ["Merkez", "Akyaka", "Arpaçay", "Digor", "Kağızman", "Sarıkamış", "Selim", "Susuz"],
    "Kastamonu": ["Merkez", "Abana", "Ağlı", "Araç", "Bozkurt", "Cide", "Çatalzeytin", "Daday", "Devrekani", "Doğanyurt", "Hanönü", "İhsangazi", "İnebolu", "Küre", "Pınarbaşı", "Seydiler", "Şenpazar", "Taşköprü", "Tosya"],
    "Kayseri": ["Merkez", "Akkışla", "Bünyan", "Develi", "Felahiye", "Hacılar", "İncesu", "Kocasinan", "Melikgazi", "Özvatan", "Pınarbaşı", "Sarıoğlan", "Sarız", "Talas", "Tomarza", "Yahyalı", "Yeşilhisar"],
    "Kırklareli": ["Merkez", "Babaeski", "Demirköy", "Kofçaz", "Lüleburgaz", "Pehlivanköy", "Pınarhisar", "Vize"],
    "Kırşehir": ["Merkez", "Akçakent", "Akpınar", "Boztepe", "Çiçekdağı", "Kaman", "Mucur"],
    "Kocaeli": ["Merkez", "Başiskele", "Çayırova", "Darıca", "Derince", "Dilovası", "Gebze", "Gölcük", "İzmit", "Kandıra", "Karamürsel", "Kartepe", "Körfez"],
    "Konya": ["Merkez", "Ahırlı", "Akören", "Akşehir", "Altınekin", "Beyşehir", "Bozkır", "Cihanbeyli", "Çeltik", "Çumra", "Derbent", "Derebucak", "Doğanhisar", "Emirgazi", "Ereğli", "Güneysınır", "Hadim", "Halkapınar", "Hüyük", "Ilgın", "Kadınhanı", "Karapınar", "Karatay", "Kulu", "Meram", "Sarayönü", "Selçuklu", "Seydişehir", "Taşkent", "Tuzlukçu", "Yalıhüyük", "Yunak"],
    "Kütahya": ["Merkez", "Altıntaş", "Aslanapa", "Çavdarhisar", "Domaniç", "Dumlupınar", "Emet", "Gediz", "Hisarcık", "Pazarlar", "Şaphane", "Simav", "Tavşanlı"],
    "Malatya": ["Merkez", "Akçadağ", "Arapgir", "Arguvan", "Battalgazi", "Darende", "Doğanşehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Pütürge", "Yazıhan", "Yeşilyurt"],
    "Manisa": ["Merkez", "Ahmetli", "Akhisar", "Alaşehir", "Demirci", "Gölmarmara", "Gördes", "Kırkağaç", "Köprübaşı", "Kula", "Salihli", "Sarıgöl", "Saruhanlı", "Selendi", "Soma", "Şehzadeler", "Turgutlu", "Yunusemre"],
    "Kahramanmaraş": ["Merkez", "Afşin", "Andırın", "Çağlayancerit", "Dulkadiroğlu", "Ekinözü", "Elbistan", "Göksun", "Nurhak", "Onikişubat", "Pazarcık", "Türkoğlu"],
    "Mardin": ["Merkez", "Artuklu", "Dargeçit", "Derik", "Kızıltepe", "Mazıdağı", "Midyat", "Nusaybin", "Ömerli", "Savur", "Yeşilli"],
    "Muğla": ["Merkez", "Bodrum", "Dalaman", "Datça", "Fethiye", "Kavaklıdere", "Köyceğiz", "Marmaris", "Menteşe", "Milas", "Ortaca", "Seydikemer", "Ula", "Yatağan"],
    "Muş": ["Merkez", "Bulanık", "Hasköy", "Korkut", "Malazgirt", "Varto"],
    "Nevşehir": ["Merkez", "Acıgöl", "Avanos", "Derinkuyu", "Gülşehir", "Hacıbektaş", "Kozaklı", "Ürgüp"],
    "Niğde": ["Merkez", "Altunhisar", "Bor", "Çamardı", "Çiftlik", "Ulukışla"],
    "Ordu": ["Merkez", "Akkuş", "Altınordu", "Aybastı", "Çamaş", "Çatalpınar", "Çaybaşı", "Fatsa", "Gölköy", "Gülyalı", "Gürgentepe", "İkizce", "Kabadüz", "Kabataş", "Korgan", "Kumru", "Mesudiye", "Perşembe", "Ulubey", "Ünye"],
    "Rize": ["Merkez", "Ardeşen", "Çamlıhemşin", "Çayeli", "Derepazarı", "Fındıklı", "Güneysu", "Hemşin", "İkizdere", "İyidere", "Kalkandere", "Pazar"],
    "Sakarya": ["Merkez", "Adapazarı", "Akyazı", "Arifiye", "Erenler", "Ferizli", "Geyve", "Hendek", "Karapürçek", "Karasu", "Kaynarca", "Kocaali", "Pamukova", "Sapanca", "Serdivan", "Söğütlü", "Taraklı"],
    "Samsun": ["Merkez", "Alaçam", "Asarcık", "Atakum", "Ayvacık", "Bafra", "Canik", "Çarşamba", "Havza", "İlkadım", "Kavak", "Ladik", "Ondokuzmayıs", "Salıpazarı", "Tekkeköy", "Terme", "Vezirköprü", "Yakakent"],
    "Siirt": ["Merkez", "Baykan", "Eruh", "Kurtalan", "Pervari", "Şirvan", "Tillo"],
    "Sinop": ["Merkez", "Ayancık", "Boyabat", "Dikmen", "Durağan", "Erfelek", "Gerze", "Saraydüzü", "Türkeli"],
    "Sivas": ["Merkez", "Akıncılar", "Altınyayla", "Divriği", "Doğanşar", "Gemerek", "Gölova", "Gürün", "Hafik", "İmranlı", "Kangal", "Koyulhisar", "Suşehri", "Şarkışla", "Ulaş", "Yıldızeli", "Zara"],
    "Tekirdağ": ["Merkez", "Çerkezköy", "Çorlu", "Ergene", "Hayrabolu", "Kapaklı", "Malkara", "Marmaraereğlisi", "Muratlı", "Saray", "Süleymanpaşa", "Şarköy"],
    "Tokat": ["Merkez", "Almus", "Artova", "Başçiftlik", "Erbaa", "Niksar", "Pazar", "Reşadiye", "Sulusaray", "Turhal", "Yeşilyurt", "Zile"],
    "Trabzon": ["Merkez", "Akçaabat", "Araklı", "Arsin", "Beşikdüzü", "Çarşıbaşı", "Çaykara", "Dernekpazarı", "Düzköy", "Hayrat", "Köprübaşı", "Maçka", "Of", "Ortahisar", "Sürmene", "Şalpazarı", "Tonya", "Vakfıkebir", "Yomra"],
    "Tunceli": ["Merkez", "Çemişgezek", "Hozat", "Mazgirt", "Nazımiye", "Ovacık", "Pertek", "Pülümür"],
    "Şanlıurfa": ["Merkez", "Akçakale", "Birecik", "Bozova", "Ceylanpınar", "Eyyübiye", "Halfeti", "Haliliye", "Harran", "Hilvan", "Karaköprü", "Siverek", "Suruç", "Viranşehir"],
    "Uşak": ["Merkez", "Banaz", "Eşme", "Karahallı", "Sivaslı", "Ulubey"],
    "Van": ["Merkez", "Bahçesaray", "Başkale", "Çaldıran", "Çatak", "Edremit", "Erciş", "Gevaş", "Gürpınar", "İpekyolu", "Muradiye", "Özalp", "Saray", "Tuşba"],
    "Yozgat": ["Merkez", "Akdağmadeni", "Aydıncık", "Boğazlıyan", "Çandır", "Çayıralan", "Çekerek", "Kadışehri", "Saraykent", "Sarıkaya", "Sorgun", "Şefaatli", "Yenifakılı", "Yerköy"],
    "Zonguldak": ["Merkez", "Alaplı", "Çaycuma", "Devrek", "Gökçebey", "Kilimli", "Kozlu", "Karadeniz Ereğli"],
    "Aksaray": ["Merkez", "Ağaçören", "Eskil", "Gülağaç", "Güzelyurt", "Ortaköy", "Sarıyahşi", "Sultanhanı"],
    "Bayburt": ["Merkez", "Aydıntepe", "Demirözü"],
    "Karaman": ["Merkez", "Ayrancı", "Başyayla", "Ermenek", "Kazımkarabekir", "Sarıveliler"],
    "Kırıkkale": ["Merkez", "Bahşılı", "Balışeyh", "Çelebi", "Delice", "Karakeçili", "Keskin", "Sulakyurt", "Yahşihan"],
    "Batman": ["Merkez", "Beşiri", "Gercüş", "Hasankeyf", "Kozluk", "Sason"],
    "Şırnak": ["Merkez", "Beytüşşebap", "Cizre", "Güçlükonak", "İdil", "Silopi", "Uludere"],
    "Bartın": ["Merkez", "Amasra", "Kurucaşile", "Ulus"],
    "Ardahan": ["Merkez", "Çıldır", "Damal", "Göle", "Hanak", "Posof"],
    "Iğdır": ["Merkez", "Aralık", "Karakoyunlu", "Tuzluca"],
    "Yalova": ["Merkez", "Altınova", "Armutlu", "Çınarcık", "Çiftlikköy", "Termal"],
    "Karabük": ["Merkez", "Eflani", "Eskipazar", "Ovacık", "Safranbolu", "Yenice"],
    "Kilis": ["Merkez", "Elbeyli", "Musabeyli", "Polateli"],
    "Osmaniye": ["Merkez", "Bahçe", "Düziçi", "Hasanbeyli", "Kadirli", "Sumbas", "Toprakkale"],
    "Düzce": ["Merkez", "Akçakoca", "Cumayeri", "Çilimli", "Gölyaka", "Gümüşova", "Kaynaşlı", "Yığılca"]
}

def tr_lower(s):
    if not s:
        return ""
    return str(s).replace("İ", "i").replace("I", "ı").lower()

def parse_turkish_amount(val_str):
    if not val_str:
        return 0.0
    clean = re.sub(r'[^\d,.-]', '', str(val_str)).strip()
    if not clean:
        return 0.0
    clean = clean.replace('.', '').replace(',', '.')
    try:
        return float(clean)
    except Exception:
        return 0.0

def calculate_icra_vekalet(takip_cikisi):
    if takip_cikisi <= 0:
        return 0.0
    basamaklar = [
        (600000.0, 0.16),
        (600000.0, 0.15),
        (1200000.0, 0.14),
        (1200000.0, 0.13),
        (1800000.0, 0.11),
        (2400000.0, 0.08),
        (3000000.0, 0.05),
        (3600000.0, 0.03),
        (4200000.0, 0.02),
    ]
    nisbi = 0.0
    kalan = float(takip_cikisi)
    for dilim, oran in basamaklar:
        if kalan <= 0:
            break
        hesaplanan = min(kalan, dilim)
        nisbi += hesaplanan * oran
        kalan -= hesaplanan
    maktu = 9000.0
    vekalet = max(nisbi, maktu)
    if vekalet > takip_cikisi:
        vekalet = takip_cikisi
    return round(vekalet, 2)

def extract_udf_xml_and_date(file_bytes_or_path, filename=""):
    if hasattr(file_bytes_or_path, 'name') and not filename:
        filename = file_bytes_or_path.name
    if hasattr(file_bytes_or_path, 'read'):
        raw = file_bytes_or_path.read()
    elif isinstance(file_bytes_or_path, bytes):
        raw = file_bytes_or_path
    else:
        filename = filename or str(file_bytes_or_path)
        with open(file_bytes_or_path, 'rb') as f:
            raw = f.read()

    xml_content = ""
    zip_date = None
    try:
        with zipfile.ZipFile(io.BytesIO(raw), 'r') as z:
            for info in z.infolist():
                if info.date_time and info.date_time[0] > 2000:
                    try:
                        zip_date = date(info.date_time[0], info.date_time[1], info.date_time[2])
                        break
                    except Exception:
                        pass
            if 'content.xml' in z.namelist():
                xml_content = z.read('content.xml').decode('utf-8', errors='ignore')
            else:
                for info in z.infolist():
                    if info.filename.endswith('.xml') and info.filename != 'documentproperties.xml':
                        xml_content = z.read(info.filename).decode('utf-8', errors='ignore')
                        break
    except Exception:
        xml_content = raw.decode('utf-8', errors='ignore')

    return xml_content, zip_date, filename

def find_location_match(search_text):
    text_low = tr_lower(search_text)
    # Özel İstanbul İcra Adliyeleri Tespiti (Anadolu vs Çağlayan)
    if "anadolu" in text_low:
        return "İstanbul", "Anadolu"
    if "çağlayan" in text_low or "caglayan" in text_low:
        return "İstanbul", "Çağlayan"

    # 1. Önce ilçeleri tara (Merkez, Çağlayan, Anadolu hariç)
    for il_ad, ilceler in UDF_IL_ILCE.items():
        for ilce_ad in ilceler:
            if ilce_ad.lower() not in ["merkez", "çağlayan", "anadolu"]:
                if re.search(r'\b' + re.escape(tr_lower(ilce_ad)) + r'\b', text_low):
                    return il_ad, ilce_ad
    # 2. İlleri tara
    for il_ad in UDF_IL_ILCE.keys():
        if re.search(r'\b' + re.escape(tr_lower(il_ad)) + r'\b', text_low):
            if il_ad == "İstanbul":
                return "İstanbul", "Çağlayan"
            return il_ad, "Merkez"
    return "İzmir", "Merkez"

def parse_single_udf(file_bytes_or_path, filename=""):
    xml_content, zip_date, filename = extract_udf_xml_and_date(file_bytes_or_path, filename)
    if not xml_content:
        return None, "UDF dosyası okunamadı veya içeriği boş."

    cdata = ""
    c_m = re.search(r'<content><!\[CDATA\[(.*?)\]\]></content>', xml_content, re.DOTALL)
    if c_m:
        cdata = c_m.group(1)
    else:
        cdata = re.sub(r'<[^>]+>', ' ', xml_content)

    data_tag = ""
    d_m = re.search(r'<data>(.*?)</data>', xml_content, re.DOTALL)
    if d_m:
        data_tag = d_m.group(1)

    low_comb = tr_lower(xml_content + " " + filename + " " + cdata)

    # Belge Türü Tespiti
    doc_type = "DIGER"
    if "ödeme emri" in low_comb or "odeme_icra_emri" in low_comb or "örnek no : 10" in low_comb or "kambiyo senetlerine" in low_comb:
        if "takip talebi" not in tr_lower(filename) and "haciz talebi" not in tr_lower(filename):
            doc_type = "ODEME_EMRI"
    elif "takip talebi" in low_comb or "takip_talebi" in low_comb or "örnek no: 1" in low_comb or "<alacagintlolarakkarsiligifaizmiktari>" in low_comb:
        doc_type = "TAKIP_TALEBI"
    elif "haciz talebi" in low_comb:
        doc_type = "HACIZ_TALEBI"
    elif "dosya hesabı" in low_comb or "kapak hesabı" in low_comb:
        doc_type = "DOSYA_HESABI"

    res = {
        "doc_type": doc_type,
        "filename": filename,
        "il": "",
        "ilce": "",
        "icra_dairesi": "",
        "dosya_no": "",
        "yil": "",
        "sira_no": "",
        "takip_turu": "",
        "takip_tarihi": None,
        "alacakli": "",
        "alacakli_vkn": "",
        "borclular": [],
        "ana_para": 0.0,
        "t_oncesi_faiz": 0.0,
        "takip_cikisi": 0.0,
        "faiz_turu": "Ticari Avans Faizi (%48.00)",
        "faiz_orani": 48.0
    }

    # 1. ESAS / DOSYA NUMARASI
    esas_m = re.search(r'(\d{4})\s*[/_]\s*(\d+)\s*(?:ESAS|E\.)?', cdata, re.IGNORECASE)
    if esas_m:
        res["yil"] = esas_m.group(1)
        res["sira_no"] = esas_m.group(2)
        res["dosya_no"] = f"{esas_m.group(1)}/{esas_m.group(2)} E."
    else:
        fn_m = re.search(r'(\d{4})_(\d+)', filename)
        if fn_m:
            res["yil"] = fn_m.group(1)
            res["sira_no"] = fn_m.group(2)
            res["dosya_no"] = f"{fn_m.group(1)}/{fn_m.group(2)} E."

    # 2. İCRA DAİRESİ & İL/İLÇE TESPİTİ
    if data_tag:
        il_ilce_m = re.search(r'<il_Ilce>(.*?)</il_Ilce>', data_tag)
        if il_ilce_m and il_ilce_m.group(1).strip():
            matched_il, matched_ilce = find_location_match(il_ilce_m.group(1))
            res["il"] = matched_il
            res["ilce"] = matched_ilce

    daire_block_m = re.search(r'(?:T\.C\.\s*)?([^\n\r]+?)\s*(İCRA DAİRESİ|İCRA MÜDÜRLÜĞÜ|GENEL İCRA DAİRESİ|ESAS İCRA DAİRESİ)(?:[\'’]NE|[\'’]ne|[\'’]NA|[\'’]na)?', cdata, re.IGNORECASE)
    if daire_block_m:
        raw_loc = daire_block_m.group(1).replace("T.C.", "").strip()
        matched_il, matched_ilce = find_location_match(raw_loc)
        res["il"] = matched_il
        res["ilce"] = matched_ilce

        num_m = re.search(r'(\d+)\.\s*İcra', daire_block_m.group(0), re.IGNORECASE)
        if num_m:
            res["icra_dairesi"] = f"{num_m.group(1)}. İcra Dairesi"
        elif "Genel İcra" in daire_block_m.group(0):
            res["icra_dairesi"] = "Genel İcra Dairesi"
        else:
            res["icra_dairesi"] = "İcra Dairesi"
    elif not res["icra_dairesi"]:
        res["icra_dairesi"] = "İcra Dairesi"

    # 3. TAKİP TARİHİ TESPİTİ
    date_fn_m = re.search(r'(\d{2})_(\d{2})_(\d{4})', filename)
    if date_fn_m:
        try:
            d, m, y = int(date_fn_m.group(1)), int(date_fn_m.group(2)), int(date_fn_m.group(3))
            res["takip_tarihi"] = date(y, m, d)
        except Exception:
            pass

    if not res["takip_tarihi"]:
        tarih_cdata = re.search(r'(?:Talep Tarihi|Takip Tarihi|Tarih)\s*[:\t ]+(\d{2}[./]\d{2}[./]\d{4})', cdata, re.IGNORECASE)
        if tarih_cdata:
            try:
                res["takip_tarihi"] = datetime.strptime(tarih_cdata.group(1).replace("/", "."), "%d.%m.%Y").date()
            except Exception:
                pass
        elif zip_date:
            res["takip_tarihi"] = zip_date

    # 4. TAKİP TÜRÜ (ÖRNEK NO)
    if "kambiyo" in low_comb or "örnek no : 10" in low_comb or "örnek no: 10" in low_comb or "örnek no:10" in low_comb:
        res["takip_turu"] = "Örnek No: 10 (Kambiyo Senetleri - Çek/Bono/Poliçe)"
    elif "ilamlı" in low_comb or "örnek no: 4" in low_comb or "örnek no : 4" in low_comb:
        res["takip_turu"] = "Örnek No: 4-5 (İlamlı Takip - Para/Teminat)"
    elif "örnek no: 13" in low_comb or "örnek no : 13" in low_comb:
        res["takip_turu"] = "Örnek No: 13 (Kira Borcu ve Tahliye Talepli)"
    elif "örnek no: 14" in low_comb or "örnek no : 14" in low_comb:
        res["takip_turu"] = "Örnek No: 14 (Tahliye Taahhüdüne Dayalı)"
    else:
        res["takip_turu"] = "Örnek No: 7 (İlamsız Takip - Para/Teminat)"

    # 5. TARAFLAR (ALACAKLI & BORÇLULAR)
    # A) <data> etiketinden ayıkla (Takip Talebinde en temiz yapılandırılmış kaynak)
    if data_tag:
        alc_m = re.search(r'<alacakliAdiSoyadi>(.*?)</alacakliAdiSoyadi>', data_tag)
        alc_v = re.search(r'<alacakliAdiSoyadiGrp>.*?<vergiNo>(.*?)</vergiNo>', data_tag, re.DOTALL)
        if alc_m:
            alc_clean = re.sub(r'<[^>]+>', '', alc_m.group(1)).strip(' ,;-:\t\n\r')
            alc_vkn = re.search(r'\d{10,11}', alc_v.group(1)).group(0) if (alc_v and re.search(r'\d{10,11}', alc_v.group(1))) else ""
            res["alacakli"] = alc_clean
            res["alacakli_vkn"] = alc_vkn

        b_grps = re.findall(r'<borcluAdiSoyadiGrp>(.*?)</borcluAdiSoyadiGrp>', data_tag, re.DOTALL)
        for bg in b_grps:
            bm = re.search(r'<borcluAdiSoyadi>(.*?)</borcluAdiSoyadi>', bg)
            vm = re.search(r'<vergiNo>(.*?)</vergiNo>', bg)
            if bm:
                b_name = re.sub(r'<[^>]+>', '', bm.group(1)).strip(' ,;-:\t\n\r')
                b_vkn = re.search(r'\d{10,11}', vm.group(1)).group(0) if (vm and re.search(r'\d{10,11}', vm.group(1))) else ""
                if b_name and len(b_name) > 2 and b_name not in [x['ad_unvan'] for x in res['borclular']]:
                    res["borclular"].append({"ad_unvan": b_name, "tc_vkn": b_vkn})

    # B) Metin (CDATA) içinden ayıkla (Ödeme Emri vb.)
    if not res["alacakli"]:
        m_a = re.search(r'1\s*-\s*Alacaklı.*?:(.*?)(?=2\s*-\s*Borçlunun)', cdata, re.DOTALL | re.IGNORECASE)
        if m_a:
            a_block = m_a.group(1).strip()
            a_clean = re.split(r'vekili\s+Av\.', a_block, flags=re.IGNORECASE)[0]
            v_m = re.search(r'(\d{10,11})\s*(?:Vergi|TC|T\.C\.)', a_clean, re.IGNORECASE)
            alc_vkn = v_m.group(1) if v_m else ""
            alc_name = re.split(r'[,;]\s*\d{10,11}', a_clean)[0].strip(' ,;-:\t\n\r')
            res["alacakli"] = alc_name
            res["alacakli_vkn"] = alc_vkn

    if not res["borclular"]:
        m_b = re.search(r'2\s*-\s*Borçlunun.*?:(.*?)(?=3\s*-\s*Alacağın)', cdata, re.DOTALL | re.IGNORECASE)
        if m_b:
            b_block = m_b.group(1).strip()
            items = re.split(r'\n\s*\d+\s*-\s*', '\n1- ' + b_block)
            for it in items:
                it = it.strip()
                if not it or "alacaklı tarafından" in it.lower() or "borçlunun ve varsa" in it.lower():
                    continue
                v_m = re.search(r'(\d{10,11})\s*(?:Vergi|TC|T\.C\.)', it, re.IGNORECASE)
                vkn = v_m.group(1) if v_m else ""
                name = re.split(r'[,;]\s*\d{10,11}', it)[0].strip()
                name = re.sub(r'^\d+\s*-\s*', '', name).strip(' ,;-:\t\n\r')
                if name and len(name) > 2 and name not in [x['ad_unvan'] for x in res['borclular']]:
                    res["borclular"].append({"ad_unvan": name, "tc_vkn": vkn})
        else:
            hcz_b = re.search(r'(?:İşlem Yapılacak Taraf Adı|Borçlu)\s*[:\t ]+([^\n\r,;]+)', cdata, re.IGNORECASE)
            if hcz_b:
                name = hcz_b.group(1).strip(' ,;-:\t')
                v_m = re.search(r'\d{11}', cdata)
                vkn = v_m.group(0) if v_m else ""
                if name and "borçlunun ve varsa" not in name.lower():
                    res["borclular"].append({"ad_unvan": name, "tc_vkn": vkn})

    # 6. TUTARLAR VE FAİZ BİLGİSİ
    amounts_found = []
    if data_tag:
        d_amts = re.findall(r'<takipTalebiDortMaddeAlacaginTlOlarakKarsiligiFaizMiktari>([0-9.,]+)</takipTalebiDortMaddeAlacaginTlOlarakKarsiligiFaizMiktari>\s*</takipTalebiDortMaddeAlacaginTlOlarakKarsiligiFaizMiktarGrp>\s*<takipTalebiDortMaddFaizinIslemeyeBasladigiGunGrp>\s*<faizinIslemeyeBasladigiGun>(.*?)</faizinIslemeyeBasladigiGun>', data_tag, re.DOTALL)
        for a_str, desc in d_amts:
            amt = parse_turkish_amount(a_str)
            amounts_found.append((amt, desc))

    if not amounts_found:
        m_c = re.search(r'3\s*-\s*Alacağın.*?:(.*?)(?=4\s*-\s*Senet|4\s*-\s*Alacağın)', cdata, re.DOTALL | re.IGNORECASE)
        if m_c:
            lines = m_c.group(1).split('\n')
            curr_amt = 0.0
            for line in lines:
                line_str = line.strip()
                amt_match = re.match(r'^([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})$', line_str)
                if amt_match:
                    curr_amt = parse_turkish_amount(amt_match.group(1))
                elif curr_amt > 0 and ('TL' in line_str or 'bedeli' in line_str or 'faiz' in line_str.lower() or 'alacak' in line_str.lower() or 'tazminat' in line_str.lower()):
                    amounts_found.append((curr_amt, line_str))
                    curr_amt = 0.0

    anapara_kalemleri = 0.0
    faiz_kalemi = 0.0
    toplam_alacak = 0.0

    for amt, desc in amounts_found:
        desc_low = tr_lower(desc)
        if "toplam alacak" in desc_low:
            toplam_alacak = amt
        elif "işlemiş faiz" in desc_low or "islemiş faiz" in desc_low:
            faiz_kalemi += amt
        else:
            anapara_kalemleri += amt

    if toplam_alacak > 0:
        res["takip_cikisi"] = toplam_alacak
        if faiz_kalemi > 0:
            res["t_oncesi_faiz"] = faiz_kalemi
            res["ana_para"] = round(toplam_alacak - faiz_kalemi, 2)
        else:
            res["ana_para"] = toplam_alacak
    elif anapara_kalemleri > 0:
        res["ana_para"] = anapara_kalemleri
        res["t_oncesi_faiz"] = faiz_kalemi
        res["takip_cikisi"] = round(anapara_kalemleri + faiz_kalemi, 2)

    # Faiz Türü & Oranı (Öncelik: Reeskont içeren tüm ifadeler TCMB Reeskont Faizidir)
    if "reeskont" in low_comb:
        res["faiz_turu"] = "TCMB Reeskont Faizi (%39.75)"
        res["faiz_orani"] = 39.75
    elif "ticari avans" in low_comb or "avans" in low_comb:
        res["faiz_turu"] = "Ticari Avans Faizi (%48.00)"
        res["faiz_orani"] = 48.0
    elif "yasal faiz" in low_comb or "kanuni faiz" in low_comb:
        res["faiz_turu"] = "Yasal Faiz (%31.00)"
        res["faiz_orani"] = 31.0

    # 7. AYRINTILI ALACAK KALEMLERİ LİSTESİ OLUŞTURMA
    res["alacak_kalemleri"] = []
    for amt, desc in amounts_found:
        desc_clean = re.sub(r'^[0-9.,\sTL-]+', '', desc).strip()
        desc_low = tr_lower(desc)
        if "toplam alacak" in desc_low:
            continue
        
        if "işlemiş faiz" in desc_low or "islemiş faiz" in desc_low:
            k_tur = "Takip Öncesi Faiz"
            k_ad = "Takip Öncesi İşlemiş Faiz"
            k_faiz_turu = "Faizsiz"
            k_faiz_orani = 0.0
            k_sorumlu = "Tüm Borçlular"
            tutar_val = 0.0
            faiz_val = amt
        elif "tazminat" in desc_low:
            k_tur = "Tazminat"
            k_ad = "Çek Tazminatı"
            k_faiz_turu = res["faiz_turu"]
            k_faiz_orani = res["faiz_orani"]
            k_sorumlu = "Keşideci (Yalnızca Keşideci Sorumlu)" if ("keşideci" in desc_low or "kesideci" in desc_low) else "Tüm Borçlular"
            tutar_val = amt
            faiz_val = 0.0
        elif "çek bedeli" in desc_low or "cek bedeli" in desc_low:
            k_tur = "Asıl Alacak"
            k_ad = "Karşılıksız Çek Bedeli"
            k_faiz_turu = res["faiz_turu"]
            k_faiz_orani = res["faiz_orani"]
            k_sorumlu = "Tüm Borçlular"
            tutar_val = amt
            faiz_val = 0.0
        else:
            k_tur = "Asıl Alacak"
            k_ad = desc_clean if len(desc_clean) > 2 else "Asıl Alacak"
            k_faiz_turu = res["faiz_turu"]
            k_faiz_orani = res["faiz_orani"]
            k_sorumlu = "Tüm Borçlular"
            tutar_val = amt
            faiz_val = 0.0

        res["alacak_kalemleri"].append({
            "kalem_adi": k_ad,
            "kalem_turu": k_tur,
            "tutar": tutar_val,
            "t_oncesi_faiz": faiz_val,
            "faiz_turu": k_faiz_turu,
            "faiz_orani": k_faiz_orani,
            "sorumlu_borclular": k_sorumlu
        })

    # Eğer tek parça tutar varsa ama kalem ayrışmamışsa
    if not res["alacak_kalemleri"] and res["ana_para"] > 0:
        res["alacak_kalemleri"].append({
            "kalem_adi": "Asıl Alacak",
            "kalem_turu": "Asıl Alacak",
            "tutar": res["ana_para"],
            "t_oncesi_faiz": 0.0,
            "faiz_turu": res["faiz_turu"],
            "faiz_orani": res["faiz_orani"],
            "sorumlu_borclular": "Tüm Borçlular"
        })
        if res["t_oncesi_faiz"] > 0:
            res["alacak_kalemleri"].append({
                "kalem_adi": "Takip Öncesi İşlemiş Faiz",
                "kalem_turu": "Takip Öncesi Faiz",
                "tutar": 0.0,
                "t_oncesi_faiz": res["t_oncesi_faiz"],
                "faiz_turu": "Faizsiz",
                "faiz_orani": 0.0,
                "sorumlu_borclular": "Tüm Borçlular"
            })

    return res, None

def merge_udf_list(file_results):
    if not file_results:
        return None, "Ayrıştırılacak dosya bulunamadı."

    odeme_doc = next((d for d in file_results if d.get('doc_type') == 'ODEME_EMRI'), None)
    talep_doc = next((d for d in file_results if d.get('doc_type') == 'TAKIP_TALEBI'), None)

    # Birincil temel şablon: Ödeme Emri varsa ondan başla, yoksa Takip Talebi
    primary = odeme_doc or talep_doc or file_results[0]
    merged = dict(primary)

    # 1. Dosya No, Daire & Takip Türü: Ödeme Emri öncelikli
    if odeme_doc:
        if odeme_doc.get("dosya_no"):
            merged["dosya_no"] = odeme_doc["dosya_no"]
            merged["yil"] = odeme_doc["yil"]
            merged["sira_no"] = odeme_doc["sira_no"]
        if odeme_doc.get("il") and odeme_doc["il"] != "İzmir":
            merged["il"] = odeme_doc["il"]
            merged["ilce"] = odeme_doc["ilce"]
        if odeme_doc.get("icra_dairesi"):
            merged["icra_dairesi"] = odeme_doc["icra_dairesi"]
        if odeme_doc.get("takip_turu"):
            merged["takip_turu"] = odeme_doc["takip_turu"]

    # 2. Takip Açılış Tarihi: Kesinlikle Takip Talebi öncelikli!
    if talep_doc and talep_doc.get("takip_tarihi"):
        merged["takip_tarihi"] = talep_doc["takip_tarihi"]
    elif not merged.get("takip_tarihi"):
        for d in file_results:
            if d.get("takip_tarihi"):
                merged["takip_tarihi"] = d["takip_tarihi"]
                break
    if not merged.get("takip_tarihi"):
        merged["takip_tarihi"] = date.today()

    # 3. Alacaklı Bilgisi: VKN içeren en detaylı alacaklıyı seç
    all_alacakli = [d for d in file_results if d.get("alacakli")]
    if all_alacakli:
        best_alc = max(all_alacakli, key=lambda x: len(x.get("alacakli_vkn", "")))
        merged["alacakli"] = best_alc["alacakli"]
        merged["alacakli_vkn"] = best_alc.get("alacakli_vkn", "")

    # 4. Borçlular Listesi: Tüm belgelerdeki borçluları birleştir (Tekilleştir & VKN güncelle)
    merged_borclular = []
    seen_names = set()
    for d in file_results:
        for b in d.get("borclular", []):
            name = b.get("ad_unvan", "").strip()
            vkn = b.get("tc_vkn", "").strip()
            if not name or "borçlunun ve varsa" in name.lower():
                continue
            if name not in seen_names:
                seen_names.add(name)
                merged_borclular.append({"ad_unvan": name, "tc_vkn": vkn})
            elif vkn:
                for existing in merged_borclular:
                    if existing["ad_unvan"] == name and not existing.get("tc_vkn"):
                        existing["tc_vkn"] = vkn

    merged["borclular"] = merged_borclular
    merged["borclu_adlari"] = [b["ad_unvan"] for b in merged_borclular]
    merged["borclu"] = ", ".join(merged["borclu_adlari"])

    # 5. Tutarlar: En detaylı hesaplamayı seç
    docs_with_amt = [d for d in file_results if d.get("ana_para", 0) > 0]
    if docs_with_amt:
        best_amt_doc = max(docs_with_amt, key=lambda x: (x.get("takip_cikisi", 0), x.get("t_oncesi_faiz", 0)))
        merged["ana_para"] = best_amt_doc["ana_para"]
        merged["t_oncesi_faiz"] = best_amt_doc["t_oncesi_faiz"]
        merged["takip_cikisi"] = best_amt_doc["takip_cikisi"]
        merged["faiz_turu"] = best_amt_doc["faiz_turu"]
        merged["faiz_orani"] = best_amt_doc["faiz_orani"]

    # 6. Alacak Kalemleri: En zengin kalem listesini al
    kalem_docs = [d for d in file_results if len(d.get("alacak_kalemleri", [])) > 0]
    if kalem_docs:
        best_k_doc = max(kalem_docs, key=lambda x: len(x.get("alacak_kalemleri", [])))
        merged["alacak_kalemleri"] = best_k_doc.get("alacak_kalemleri", [])
    elif not merged.get("alacak_kalemleri"):
        merged["alacak_kalemleri"] = []

    # Vekalet Ücreti
    cikis = merged.get("ana_para", 0.0) + merged.get("t_oncesi_faiz", 0.0)
    merged["vekalet_ucreti"] = calculate_icra_vekalet(cikis)
    merged["yuklenen_dosyalar"] = [d.get("filename", "") for d in file_results]

    return merged, None

def parse_udf_files(files_or_paths):
    """
    Birden fazla veya tekil UDF dosyasını ayrıştırıp akıllı öncelik kurallarıyla birleştirir.
    """
    if not isinstance(files_or_paths, (list, tuple)):
        files_or_paths = [files_or_paths]

    parsed_list = []
    errors = []
    for item in files_or_paths:
        fname = getattr(item, 'name', str(item))
        res, err = parse_single_udf(item, fname)
        if err:
            errors.append(f"{fname}: {err}")
        elif res:
            parsed_list.append(res)

    if not parsed_list:
        return None, " | ".join(errors) if errors else "Hiçbir UDF dosyası okunamadı."

    return merge_udf_list(parsed_list)

def parse_udf_file(file_bytes_or_path):
    """Geriye dönük uyumluluk için tekil çağrı fonksiyonu"""
    return parse_udf_files([file_bytes_or_path])
