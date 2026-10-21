"""
knowledge_base.py
=================
Basis pengetahuan (knowledge base): teks label & rekomendasi perawatan.

Dipisah dari rule_engine.py agar:
  - Aturan (kapan sesuatu berlaku)  -> rule_engine.py
  - Isi saran (apa yang disarankan) -> file ini
Anggota kelompok yang tidak ngoding bisa merapikan isi saran di sini
(sebaiknya dikonsultasikan dengan sumber dermatologi yang tepercaya).
"""

DISCLAIMER = (
    "Hasil ini adalah skrining visual otomatis dari satu foto, bukan diagnosis medis. "
    "Pencahayaan, kamera, dan warna kulit dapat memengaruhi hasil. "
    "Jika kulit terasa sakit, meradang, atau tidak membaik, konsultasikan ke dokter kulit."
)

# ---------------------------------------------------------------------- #
#  Jenis kulit
# ---------------------------------------------------------------------- #
SKIN_TYPES = {
    "oily": {
        "label": "Berminyak",
        "summary": "Permukaan kulit tampak mengilap karena produksi sebum yang tinggi, "
                   "terutama di area dahi, hidung, dan pipi.",
        "recommendations": {
            "morning": [
                "Cuci muka dengan pembersih gel atau foaming yang lembut.",
                "Serum niacinamide untuk membantu mengontrol minyak dan memperkecil tampilan pori.",
                "Pelembap bertekstur gel, non-comedogenic (tidak menyumbat pori).",
                "Tabir surya SPF 30+ bertekstur ringan atau matte.",
            ],
            "night": [
                "Bersihkan sisa tabir surya dan debu dengan micellar water atau cleansing oil, lalu cuci muka.",
                "BHA (salicylic acid) 2-3 kali seminggu untuk membersihkan pori.",
                "Pelembap gel yang ringan; kulit berminyak tetap perlu pelembap.",
            ],
            "ingredients": ["Niacinamide", "Salicylic acid (BHA)", "Zinc PCA", "Clay mask (1x seminggu)"],
            "avoid": [
                "Mencuci muka lebih dari 3 kali sehari; kulit bisa memproduksi minyak lebih banyak.",
                "Scrub butiran kasar yang menggores kulit.",
                "Krim kental atau produk berbasis minyak berat.",
            ],
            "lifestyle": [
                "Ganti sarung bantal 1-2 kali seminggu.",
                "Bawa kertas penyerap minyak, jangan menggosok wajah dengan tisu kasar.",
            ],
        },
    },
    "dull": {
        "label": "Kusam",
        "summary": "Kulit tampak kurang cerah dan kurang bercahaya, biasanya karena sel kulit mati "
                   "menumpuk, kurang hidrasi, atau paparan matahari tanpa perlindungan.",
        "recommendations": {
            "morning": [
                "Cuci muka dengan pembersih lembut.",
                "Serum vitamin C untuk membantu mencerahkan dan melindungi dari radikal bebas.",
                "Pelembap yang menghidrasi.",
                "Tabir surya SPF 30+ setiap hari; ini langkah terpenting agar kulit tidak makin kusam.",
            ],
            "night": [
                "Eksfoliasi lembut dengan AHA (glycolic atau lactic acid) 1-2 kali seminggu.",
                "Serum niacinamide atau alpha arbutin untuk meratakan warna kulit.",
                "Pelembap malam untuk membantu pemulihan kulit.",
            ],
            "ingredients": ["Vitamin C", "AHA (glycolic/lactic acid)", "Niacinamide", "Alpha arbutin"],
            "avoid": [
                "Keluar rumah tanpa tabir surya.",
                "Scrub kasar dan eksfoliasi setiap hari; justru merusak lapisan pelindung kulit.",
            ],
            "lifestyle": [
                "Tidur 7-8 jam dan minum air putih cukup.",
                "Perbanyak buah dan sayur; kurangi rokok dan begadang.",
                "Foto ulang di tempat terang agar hasil tidak dipengaruhi cahaya redup.",
            ],
        },
    },
    "dry": {
        "label": "Kering",
        "summary": "Permukaan kulit tampak kasar dan kurang lembap, tanda lapisan pelindung kulit "
                   "kekurangan air dan minyak alami.",
        "recommendations": {
            "morning": [
                "Bilas dengan air biasa atau pembersih cream/milk yang tidak berbusa.",
                "Serum hyaluronic acid, oleskan saat wajah masih sedikit lembap.",
                "Pelembap kaya dengan ceramide atau squalane.",
                "Tabir surya SPF 30+ dengan formula melembapkan.",
            ],
            "night": [
                "Pembersih lembut tanpa sabun keras.",
                "Pelembap yang lebih kental, atau tambahkan lapisan tipis balm di area yang sangat kering.",
                "Sheet mask hidrasi 1-2 kali seminggu.",
            ],
            "ingredients": ["Hyaluronic acid", "Ceramide", "Glycerin", "Squalane", "Shea butter"],
            "avoid": [
                "Air panas saat mencuci muka.",
                "Produk beralkohol (alcohol denat) dan sabun yang membuat kulit terasa 'kesat'.",
                "Eksfoliasi berlebihan.",
            ],
            "lifestyle": [
                "Minum air putih yang cukup.",
                "Gunakan humidifier bila berada di ruangan ber-AC sepanjang hari.",
            ],
        },
    },
    "normal": {
        "label": "Normal",
        "summary": "Kecerahan, kilap, dan tekstur kulit berada dalam batas seimbang. "
                   "Fokus perawatan adalah menjaga kondisi ini.",
        "recommendations": {
            "morning": [
                "Cuci muka dengan pembersih lembut.",
                "Pelembap ringan.",
                "Tabir surya SPF 30+ setiap hari.",
            ],
            "night": [
                "Bersihkan wajah, terutama setelah memakai tabir surya atau makeup.",
                "Pelembap malam.",
                "Eksfoliasi lembut 1 kali seminggu bila diperlukan.",
            ],
            "ingredients": ["Antioksidan ringan (vitamin C/E)", "Hyaluronic acid", "Niacinamide"],
            "avoid": [
                "Terlalu sering berganti-ganti produk; kulit butuh waktu beradaptasi.",
                "Tidur dengan makeup yang belum dibersihkan.",
            ],
            "lifestyle": [
                "Pertahankan pola tidur, makan, dan minum yang baik.",
                "Scan ulang secara berkala untuk memantau perubahan kulit.",
            ],
        },
    },
}

# ---------------------------------------------------------------------- #
#  Tingkat noda / jerawat (aturan terpisah dari jenis kulit)
# ---------------------------------------------------------------------- #
BLEMISH_LEVELS = {
    "clear": {
        "label": "Bersih",
        "summary": "Hampir tidak terdeteksi bintik kemerahan atau noda gelap.",
        "tips": [],
    },
    "few": {
        "label": "Sedikit noda",
        "summary": "Terdeteksi beberapa bintik kemerahan atau noda gelap.",
        "tips": [
            "Jangan memencet jerawat; bisa memperparah peradangan dan meninggalkan bekas.",
            "Totol spot treatment dengan benzoyl peroxide 2,5% atau salicylic acid pada bintik yang meradang.",
            "Gunakan tabir surya agar bekas noda tidak menggelap.",
        ],
    },
    "many": {
        "label": "Banyak noda",
        "summary": "Terdeteksi cukup banyak bintik kemerahan atau noda gelap.",
        "tips": [
            "Hindari memencet atau menggaruk bintik.",
            "Jaga rutinitas sederhana dan lembut; hindari mencoba banyak produk aktif sekaligus.",
            "Pertimbangkan konsultasi ke dokter kulit, terutama bila jerawat nyeri, bernanah, atau terus bertambah.",
        ],
    },
}
