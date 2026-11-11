import pandas as pd

data = pd.read_excel("data.xlsx")
logikai_hibak = pd.DataFrame(columns=["Sorindex", "Megjegyzés"])

print("Adatméret:", data.shape)

data_betoltott = data.copy()

data.iloc[:, 2] = pd.to_numeric(
    (
    data.iloc[:, 2].copy()
    .astype("string")
    .str.replace(
        r"\belso\b|\belső\b", "1", case=False, regex=True
        )
    .str.extract(r"(\d+)")[0]
    ),
    errors="coerce"
).astype("Int64")

eredeti_ktsg = data_betoltott.iloc[:, 12].copy()

data.iloc[:, 12] = pd.to_numeric(
    (
    eredeti_ktsg
    .astype("string")
    .str.strip()
    .replace({
        "20eu": "8000", #pontosítás kell beadáskor átváltási rátára
        "0, család fizeti": "0",
        "Diák ingyenesel vagyok": "0",
        "7000 ft (csak a claude-ért fizetek)":"7000"
    })
    .str.replace(
        r"(?i)^(\d+(?:[.,]\d+)?)\s*k$",
        lambda m: str(
            int(float(m.group(1).replace(",", ".")) * 1000)
        ),
        regex=True
    )
    .str.replace(
        r"(?i)\s*(HUF|Ft)\s*$",
        "",
        regex=True
    )
    .str.replace(".", "", regex=False)
    .str.strip()
    ),
    errors="coerce"
).astype("Int64")

#print("\nSzemeszter:")
#print(data.iloc[:, 2].value_counts(dropna=False))
#print("\nHavi kiadás:")
#print(data.iloc[:, 12].value_counts(dropna=False))

#print("\nNem feldolgozható költségválaszok:")
#print(
 #   pd.DataFrame({
  #      "eredeti": eredeti_ktsg,
   #     "tisztitott": data.iloc[:, 12]
    #}).loc[
     #   eredeti_ktsg.notna() &
      #  data.iloc[:, 12].isna()
  #  ]
#)

#korlátozás gyakorisága
gyak_oszlopok = data.columns[43:50]
gyak_dummy = (
    data.loc[:, gyak_oszlopok]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
)
jelolesek_szama = gyak_dummy.eq(1).sum(axis=1) #válaszok per fő

kivalasztott = gyak_dummy.iloc[:, ::-1].eq(1).idxmax(axis=1)
kivalasztott = kivalasztott.where(jelolesek_szama > 0)
data["korlatozas_gyakorisaga"] = (
    kivalasztott
    .str.rsplit(" | ", n=1)
    .str[-1]
)
#print("\nKorlátokba ütközés gyakorisági eloszlása:")
#print(
 #   data["korlatozas_gyakorisaga"]
  #  .value_counts(dropna=False)
   # .to_string()
#)
tobb_jeloles = jelolesek_szama > 1
#print("\nTöbb választ adók száma:")
#print(tobb_jeloles.sum())
#print("\nTöbb válasz rekordok (indexszám):")
#print(
 #   data.loc[tobb_jeloles, [
  #      data.columns[0],
   #     *gyak_oszlopok,
    #    "korlatozas_gyakorisaga"
    #]].to_string(index=True)
#)
#print("\nJelölt válaszopciók szerint:")
#print(jelolesek_szama.value_counts().sort_index())

uj_hibak = pd.DataFrame({
    "Sorindex": data.index[tobb_jeloles],
    "Megjegyzés": "Többet jelölt korlátozás gyakoriságnak"
})

logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

ai_hasznalt = (
    data.iloc[:, 4]
    .astype("string")
    .str.strip()
    .str.casefold()
    .eq("igen")
)

nem_regisztralt = (
    data.iloc[:, 5:12]
    .astype("string")
    .apply(
        lambda col: col.str.strip().str.startswith(
            "Nem vagyok regisztrálva ennél az AI-szolgáltatónál", na=False
        )
    )
    .all(axis=1)
)

ellentmondas = ai_hasznalt & nem_regisztralt
uj_hibak = pd.DataFrame({
    "Sorindex": data.index[ellentmondas],
    "Megjegyzés": "AI-t használt, de sehol nincs regisztrálva"
})
logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

#print("\nAI-használat regisztráció nélkül:")
#print(ellentmondas.sum())
#print("\nÉrintett rekordok:")
#print(
 #   data.loc[ellentmondas, [
  #      data.columns[4],
   #     *data.columns[5:12]
    #]].to_string()
#)

csomagok = data.iloc[:, 5:12].astype("string").apply(
    lambda col: (
        col.str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.casefold()
    )
)

fizetos_csomag = csomagok.apply(
    lambda col: (
        col.str.startswith("fizetős csomag", na=False)
        | col.str.contains("költségmegosztás", na=False)
    )
).any(axis=1)

ingyenes_premium = csomagok.apply(
    lambda col: col.str.startswith(
        "ingyenes hozzáférés fizetős csomaghoz",
        na=False
    )
).any(axis=1)

ingyenes_alap = csomagok.eq("ingyenes csomag").any(axis=1)
ai_hasznalt = (
    data.iloc[:, 4]
    .astype("string")
    .str.strip()
    .str.casefold()
    .eq("igen")
    .fillna(False)
)

data["elofizetesi_csoport"] = pd.NA

data.loc[ai_hasznalt, "elofizetesi_csoport"] = "Ingyenes"

data.loc[
    ai_hasznalt & fizetos_csomag,
    "elofizetesi_csoport"
] = "Előfizető"

print(data["elofizetesi_csoport"].value_counts())
print("Összes kitöltő:", len(data))

data["ingyenes_csomag"] = (
    ai_hasznalt
    & ~fizetos_csomag
    & ~ingyenes_premium
    & ingyenes_alap
).astype(int)

data["ingyenes_premium"] = (
    ai_hasznalt
    & ~fizetos_csomag
    & ingyenes_premium
).astype(int)

print("\nElőfizetési főcsoportok:")
print(data["elofizetesi_csoport"].value_counts())

print("\nIngyenes alcsoportok:")
print("Csak ingyenes csomag:", data["ingyenes_csomag"].sum())
print("Ingyenes prémium:", data["ingyenes_premium"].sum())

print("Sehol nem regisztrált:", nem_regisztralt.sum())

elofizetes_okai = (
    data.iloc[:, 13:24]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
)

ingyenes = data["elofizetesi_csoport"].eq("Ingyenes")
van_elofizetesi_indok = elofizetes_okai.eq(1).any(axis=1)

ellentmondas_3 = (
    ai_hasznalt
    & ~fizetos_csomag
    & ~ingyenes_premium
    & van_elofizetesi_indok
)
uj_hibak = pd.DataFrame({
    "Sorindex": data.index[ellentmondas_3],
    "Megjegyzés": "Ingyenes felhasználó előfizetési indokot jelölt"
})
logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

print("\nInkonzisztens rekordok száma:", ellentmondas_3.sum())
print("\nÉrintett rekordok:")
print(
    data.loc[
        ellentmondas_3,
        [data.columns[0], "elofizetesi_csoport", *data.columns[13:24]]
    ].to_string()
)

reakcio_oszlopok = data.columns[50:59]

nincs_korlat_oszlop = next(
    (col for col in reakcio_oszlopok
    if "Nem ütköztem még AI-használat korlátozásába" in col),
    None
)

egyeb_reakciok = reakcio_oszlopok.drop(nincs_korlat_oszlop)

reakciok = (
    data.loc[:, egyeb_reakciok]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
)

soha = data["korlatozas_gyakorisaga"].astype("string").str.strip().eq("Soha")

van_konkret_reakcio = reakciok.eq(1).any(axis=1)
gyanus = soha & van_konkret_reakcio
uj_hibak = pd.DataFrame({
    "Sorindex": data.index[gyanus],
    "Megjegyzés": 'A korlátozás gyakorisága "Soha", mégis konkrét reakciót jelölt'
})

logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

#print("Gyanús rekordok száma:", gyanus.sum())
#print(
 #   data.loc[
  #      gyanus,
   #     [data.columns[0], "korlatozas_gyakorisaga", *reakcio_oszlopok]
   # ].to_string()
#)

volt_korlat_30nap = (
    data.iloc[:, 68]
    .astype("string")
    .str.strip()
    .str.casefold()
    .eq("igen")
)
ellentmondas_5 = soha & volt_korlat_30nap

uj_hibak = pd.DataFrame({
    "Sorindex": data.index[ellentmondas_5],
    "Megjegyzés": 'Korlátozás gyakorisága "Soha", de az elmúlt 30 napban volt korlátozása'
})

logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

#print("Ellentmondásos rekordok száma:", ellentmondas_5.sum())
#print(
 #   data.loc[
  #      ellentmondas_5,
   #     [data.columns[0], "korlatozas_gyakorisaga", data.columns[68]]
    #].to_string()
#)

koltseg = pd.to_numeric(data.iloc[:, 12], errors="coerce")

koltseg_kategoria = pd.Series("Hiányzó", index=data.index)
koltseg_kategoria.loc[koltseg.eq(0)] = "0 Ft"
koltseg_kategoria.loc[koltseg.gt(0)] = "Pozitív összeg"

#print("\nFizetős státusz és megadott havi kiadás:")
#print(pd.crosstab(
 #   fizetos_csomag.map({True: "Fizetős státusz", False: "Nincs fizetős státusz"}),
  #  koltseg_kategoria
#).to_string())

ellentmondas_6 = fizetos_csomag & (koltseg.eq(0) | koltseg.isna())

uj_hibak = pd.DataFrame({
    "Sorindex": data.index[ellentmondas_6],
    "Megjegyzés": "Fizetős csomag vagy költségmegosztás, de 0 Ft vagy hiányzó havi kiadás"
})
logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

#print("\nFizetős státuszú kitöltők:", fizetos_csomag.sum())
#print("Közülük pozitív összeget megadók:", (fizetos_csomag & koltseg.gt(0)).sum())
#print("Ellentmondásos rekordok:", ellentmondas_6.sum())

#print("\nÉrintett rekordok:")
#print(
 #   data.loc[
  #      ellentmondas_6,
   #     [data.columns[0], *data.columns[5:12], data.columns[12]]
   # ].to_string()
#)

ellentmondas_7 = (
    ai_hasznalt
    & ~fizetos_csomag
    & koltseg.gt(0)
)
uj_hibak = pd.DataFrame({
    "Sorindex": data.index[ellentmondas_7],
    "Megjegyzés": "Ingyenes státusz, de 0 Ft-nál nagyobb havi AI-kiadás"
})
logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

#print("Ingyenes státuszú kitöltők:", ingyenes.sum())
#print("Ellentmondásos rekordok:", ellentmondas_7.sum())

#print("\nÉrintett rekordok:")
#print(
   # data.loc[
    #    ellentmondas_7,
     #   [data.columns[0], *data.columns[5:12], data.columns[12]]
    #].to_string()
#)

reakcio_oszlopok = data.columns[50:59]

reakciok = (
    data.loc[:, reakcio_oszlopok]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
)

ellentmondas_8 = (
    reakciok[nincs_korlat_oszlop].eq(1)
    & reakciok.drop(columns=nincs_korlat_oszlop).eq(1).any(axis=1)
)
uj_hibak = pd.DataFrame({
    "Sorindex": data.index[ellentmondas_8],
    "Megjegyzés": '"Nem ütköztem még korlátozásba" mellett konkrét reakciót is jelölt'
})
logikai_hibak = pd.concat(
    [logikai_hibak, uj_hibak],
    ignore_index=True
)

print("Ellentmondásos rekordok száma:", ellentmondas_8.sum())
print(
    data.loc[
        ellentmondas_8,
        [data.columns[0], *reakcio_oszlopok]
    ].to_string()
)

logikai_hibak.to_excel("logikai_hibak.xlsx", index=False)

print(f"Exportálva: {len(logikai_hibak)} hibabejegyzés")
print(f"Érintett kitöltők száma: {logikai_hibak['Sorindex'].nunique()}")

hibak_osszesitve = (
    logikai_hibak
    .groupby("Sorindex")["Megjegyzés"]
    .agg(lambda x: ", ".join(x.dropna().drop_duplicates()))
)

data["Logikai_hibak"] = (
    data.index.to_series()
    .map(hibak_osszesitve)
    .fillna("")
)

data["Csomaghozzaferes"] = pd.NA

data.loc[
    ai_hasznalt & fizetos_csomag,
    "Csomaghozzaferes"
] = "Fizetős"

data.loc[
    ai_hasznalt & ~fizetos_csomag & ingyenes_premium,
    "Csomaghozzaferes"
] = "Ingyenes prémium"

data.loc[
    ai_hasznalt & ~fizetos_csomag & ~ingyenes_premium & ingyenes_alap,
    "Csomaghozzaferes"
] = "Csak ingyenes"

data.to_excel("tisztitott_adatok.xlsx", index=False)

print("Tisztított adatok exportálva.")
print(data["Csomaghozzaferes"].value_counts(dropna=False))
print("Logikai hibás válaszadók:",
      data["Logikai_hibak"].ne("").sum())
