import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
import streamlit as st

# ⚙️ Configuration de la page Streamlit
st.set_page_config(page_title="Dashboard Achats ONCF", layout="wide")

# 🔌 Connexion à la base MySQL
engine = create_engine(
    "mysql+pymysql://oncf:oncf@localhost:3306/oncf?connect_timeout=60",
    pool_recycle=3600,
    pool_pre_ping=True
)

# 📥 Requête SQL avec jointures
query = """
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

# 🚀 Chargement des données
try:
    st.info("⏳ Chargement des données...")
    df = pd.read_sql(query, engine)
    st.success("✅ Données chargées avec succès.")
except Exception as e:
    st.error("❌ Erreur lors de l'exécution de la requête SQL.")
    st.exception(e)
    st.stop()

# 🔁 Suppression des doublons exacts sauf si la date_commande diffère
df = df.drop_duplicates(
    subset=[
        'commande_id',
        'date_commande',
        'quantite',
        'fournisseur_id',
        'article_id',
        'libelle_article',
        'type_achat',
        'montant_commande',
        'designation',
        'famille_article',
        'fournisseur_fk',
        'quantite_dm'
    ],
    keep='first'
)

# 🧹 Nettoyage et préparation
for col in ['montant_commande', 'quantite', 'quantite_dm']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

if 'date_commande' in df.columns:
    df['date_commande'] = pd.to_datetime(df['date_commande'], errors='coerce')

df = df.dropna(subset=['montant_commande', 'quantite', 'date_commande'])
if df.empty:
    st.warning("⚠️ Aucune donnée disponible après nettoyage.")
    st.stop()

# 📊 KPI principaux
total_montant = df['montant_commande'].sum()
total_quantite = df['quantite'].sum()

# 🔝 Top 10 articles
top_articles = (
    df.groupby('designation')['montant_commande']
    .sum()
    .nlargest(10)
    .reset_index()
)

# 📆 Évolution par mois
df['mois'] = df['date_commande'].dt.to_period('M')
montant_par_mois = (
    df.groupby('mois')['montant_commande']
    .sum()
    .reset_index()
)
montant_par_mois['mois'] = montant_par_mois['mois'].dt.to_timestamp()

# 🍰 Répartition par type d’achat
repartition_type_achat = (
    df.groupby('type_achat')['montant_commande']
    .sum()
    .reset_index()
)

# 🖥️ Interface graphique
st.title("📊 Dashboard Achats - ONCF")

col1, col2 = st.columns(2)
col1.metric("💰 Total Montant Commandé", f"{total_montant:,.2f} MAD")
col2.metric("📦 Quantité Totale Commandée", f"{total_quantite:,.0f}")

# 🔝 Top 10 des articles
st.subheader("🏆 Top 10 des Articles par Montant Commandé")

# Graphique barre
fig_top_articles = px.bar(top_articles, x='designation', y='montant_commande',
                          labels={'designation': "Article", 'montant_commande': "Montant Commandé (MAD)"},
                          color='montant_commande', height=400)
st.plotly_chart(fig_top_articles, use_container_width=True)

# Liste simple des noms + montants
st.markdown("### 🗂️ Noms et Montants des Top 10 Articles")
for i, row in top_articles.iterrows():
    st.markdown(f"{i+1}. {row['designation']} — {row['montant_commande']:,.2f} MAD")

# 📈 Évolution mensuelle
st.subheader("📈 Evolution Mensuelle du Montant des Commandes")
fig_montant_mois = px.line(montant_par_mois, x='mois', y='montant_commande',
                           labels={'mois': "Mois", 'montant_commande': "Montant Commandé (MAD)"},
                           markers=True)
st.plotly_chart(fig_montant_mois, use_container_width=True)

# 🧾 Répartition par type d'achat
st.subheader("📂 Répartition du Montant Commandé par Type d'Achat")
fig_type_achat = px.pie(repartition_type_achat, names='type_achat', values='montant_commande',
                        title="Montant Commandé par Type d'Achat", hole=0.3)
st.plotly_chart(fig_type_achat, use_container_width=True)
