import pandas as pd
import mysql.connector

# 📌 Connexion à MySQL (à adapter si besoin)
conn = mysql.connector.connect(
    host="localhost",
    user="oncf",
    password="oncf",
    database="oncf",
    port=3306
)
cursor = conn.cursor()

# 🔁 Nettoyage commun
def clean_df(df):
    df.replace("null", pd.NA, inplace=True)
    df.fillna(value=pd.NA, inplace=True)
    return df

# ✅ ARTICLES
df_articles = pd.read_csv("data/Article.csv")
df_articles = clean_df(df_articles)

cursor.execute("DROP TABLE IF EXISTS articles")
cursor.execute("""
CREATE TABLE articles (
    article_id VARCHAR(20),
    chapitre INT,
    lettre_cle VARCHAR(5),
    unite_distribution INT,
    direction VARCHAR(50),
    classe_article VARCHAR(50),
    designation VARCHAR(100),
    methode_reaprrovisionnement VARCHAR(50),
    article_organisation INT,
    famille_article INT,
    type_achat INT,
    pu_annee_prec FLOAT,
    pu_annee_cours FLOAT,
    pu_dernier_cout_achat FLOAT,
    valeur_stock FLOAT,
    quantite_stock FLOAT
)
""")

insert_article = "INSERT INTO articles VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
for _, row in df_articles.iterrows():
    cursor.execute(insert_article, tuple(row))
# ✅ COMMANDES
df_cmd = pd.read_csv("data/Commande.csv")
df_cmd = clean_df(df_cmd)

# 🕒 Conversion intelligente des dates (si invalide → None)
df_cmd["date_commande"] = pd.to_datetime(df_cmd["date_commande"], errors="coerce")
df_cmd["date"] = pd.to_datetime(df_cmd["date"], errors="coerce")

# ⛑ Remplace les dates invalides (NaT) par None
df_cmd["date_commande"] = df_cmd["date_commande"].where(df_cmd["date_commande"].notna(), None)
df_cmd["date"] = df_cmd["date"].where(df_cmd["date"].notna(), None)

cursor.execute("DROP TABLE IF EXISTS commandes")
cursor.execute("""
CREATE TABLE commandes (
    commande_id INT,
    date_commande DATETIME,
    quantite FLOAT,
    fournisseur_id VARCHAR(20),
    article_id VARCHAR(20),
    libelle_article VARCHAR(100),
    type_achat VARCHAR(20),
    montant_commande FLOAT,
    `Montant Offre` FLOAT,
    date DATETIME,
    mode_paiement VARCHAR(50)
)
""")

insert_cmd = """
INSERT INTO commandes VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
for _, row in df_cmd.iterrows():
    cursor.execute(insert_cmd, tuple(row))


# ✅ FOURNISSEURS
df_fourn = pd.read_csv("data/Fournisseur.csv")
df_fourn = clean_df(df_fourn)

cursor.execute("DROP TABLE IF EXISTS fournisseurs")
cursor.execute("""
CREATE TABLE fournisseurs (
    famille_article INT,
    fournisseur_id VARCHAR(20),
    article_id VARCHAR(20)
)
""")

insert_fourn = "INSERT INTO fournisseurs VALUES (%s, %s, %s)"
for _, row in df_fourn.iterrows():
    cursor.execute(insert_fourn, tuple(row))

# ✅ DEMANDES MATIERE
df_dm = pd.read_csv("data/DM.csv")
df_dm = clean_df(df_dm)

cursor.execute("DROP TABLE IF EXISTS demandes_matiere")
cursor.execute("""
CREATE TABLE demandes_matiere (
    dm_id INT,
    article_id VARCHAR(20),
    quantite FLOAT,
    direction VARCHAR(50)
)
""")

insert_dm = "INSERT INTO demandes_matiere VALUES (%s, %s, %s, %s)"
for _, row in df_dm.iterrows():
    cursor.execute(insert_dm, tuple(row))

# ✅ Commit final
conn.commit()
cursor.close()
conn.close()

print("✅ Toutes les tables ont été insérées avec succès dans MySQL.")
