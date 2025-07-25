import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st

st.title("🔎 Test des jointures étape par étape")

# Connexion à MySQL
engine = create_engine(
    "mysql+pymysql://oncf:oncf@localhost:3306/oncf?connect_timeout=60",
    pool_recycle=3600,
    pool_pre_ping=True
)

# Requêtes pour tester chaque jointure séparément
queries = {
    "🟢 Commandes seules": """
        SELECT * FROM commandes LIMIT 10
    """,
    "🟡 Commandes + articles": """
        SELECT c.commande_id, c.article_id, a.designation
        FROM commandes c
        LEFT JOIN articles a ON c.article_id = a.article_id
        LIMIT 10
    """,
    "🟠 Commandes + fournisseurs": """
        SELECT c.commande_id, c.fournisseur_id, f.fournisseur_id AS fournisseur_fk
        FROM commandes c
        LEFT JOIN fournisseurs f ON c.fournisseur_id = f.fournisseur_id
        LIMIT 10
    """,
    "🔴 Commandes + demandes_matiere": """
        SELECT c.commande_id, c.article_id, dm.quantite
        FROM commandes c
        LEFT JOIN demandes_matiere dm ON c.article_id = dm.article_id
        LIMIT 10
    """,
    "✅ FULL JOIN complet": """
      SELECT
    c.commande_id,
    c.date_commande,
    c.quantite,
    c.fournisseur_id,
    c.article_id,
    c.libelle_article,
    c.type_achat,
    c.montant_commande,
    a.designation,
    a.famille_article,
    f.fournisseur_id AS fournisseur_fk,
    dm.quantite AS quantite_dm
FROM commandes c
LEFT JOIN articles a ON c.article_id = a.article_id
LEFT JOIN fournisseurs f ON c.fournisseur_id = f.fournisseur_id
LEFT JOIN demandes_matiere dm ON c.article_id = dm.article_id
LIMIT 1000


    """
}

# Exécution des requêtes et affichage
for label, sql in queries.items():
    st.subheader(label)
    try:
        df = pd.read_sql(text(sql), engine)
        if df.empty:
            st.warning("⚠️ Résultat vide pour cette requête.")
        else:
            st.dataframe(df)
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête: {label}")
        st.exception(e)
