import pandas as pd
from sqlalchemy import create_engine
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Configuration page
st.set_page_config(page_title="Analyse Articles Commandés ONCF", layout="wide")
st.title("📦 Analyse Des Données fournisseurs et articles dont le cadre de la refonte SI de gestion - ONCF")

# Connexion MySQL
engine = create_engine(
    "mysql+pymysql://oncf:oncf@localhost:3306/oncf?connect_timeout=60"
)

@st.cache_data(ttl=3600)
def load_data():
    articles = pd.read_sql("SELECT article_id, designation FROM articles", engine)
    commandes = pd.read_sql("""
        SELECT article_id, quantite, montant_commande, date_commande, fournisseur_id
        FROM commandes
    """, engine)
    demandes = pd.read_sql("""
        SELECT article_id, quantite AS quantite_dm
        FROM demandes_matiere
    """, engine)
    return articles, commandes, demandes

articles, commandes, demandes = load_data()

# Nettoyage
articles['article_id'] = articles['article_id'].str.strip()
commandes['article_id'] = commandes['article_id'].str.strip()
demandes['article_id'] = demandes['article_id'].str.strip()
commandes['fournisseur_id'] = commandes['fournisseur_id'].str.strip()

commandes['date_commande'] = pd.to_datetime(commandes['date_commande'], errors='coerce')
commandes['annee'] = commandes['date_commande'].dt.year

# Filtre par année en sidebar
st.sidebar.subheader("📅 Filtrer par année")
annees_dispo = sorted(commandes['annee'].dropna().unique())
annee_selectionnee = st.sidebar.selectbox("Année :", options=[None] + list(annees_dispo))

if annee_selectionnee:
    commandes = commandes[commandes['annee'] == annee_selectionnee]

# Merge commandes + articles pour désignation
commandes_avec_articles = pd.merge(
    commandes,
    articles[['article_id', 'designation']],
    how='left',
    on='article_id'
)

# Filtre fournisseur dans sidebar
st.sidebar.subheader("🔍 Filtrer par fournisseur")
fournisseurs_dispo = commandes_avec_articles['fournisseur_id'].dropna().unique()
fournisseur_selectionne = st.sidebar.selectbox("Fournisseur :", options=[None] + sorted(fournisseurs_dispo))

if fournisseur_selectionne:
    commandes_avec_articles = commandes_avec_articles[commandes_avec_articles['fournisseur_id'] == fournisseur_selectionne]

# Recalcul après filtres
agg_global = commandes_avec_articles.groupby('article_id').agg(
    quantite_commandee_total=('quantite', 'sum'),
    montant_total_payé=('montant_commande', 'sum')
).reset_index()

articles_commandes = pd.merge(
    articles, agg_global, how='inner', on='article_id'
).sort_values(by='montant_total_payé', ascending=False)

articles_commandes = pd.merge(
    articles_commandes, demandes.groupby('article_id').agg(quantite_dm=('quantite_dm', 'sum')).reset_index(),
    how='left', on='article_id'
)

articles_commandes['ecart_dm_stock'] = articles_commandes['quantite_commandee_total'] - articles_commandes['quantite_dm']

agg_par_annee = commandes_avec_articles.groupby(['article_id', 'annee']).agg(
    quantite_commandee_annuelle=('quantite', 'sum'),
    montant_annuel_payé=('montant_commande', 'sum')
).reset_index()

agg_par_annee = pd.merge(
    agg_par_annee, articles[['article_id', 'designation']], how='left', on='article_id'
)

articles_non_commandes = pd.merge(
    articles, agg_global[['article_id']], how='left', indicator=True, on='article_id'
)
articles_non_commandes = articles_non_commandes[articles_non_commandes['_merge'] == 'left_only']
articles_non_commandes = articles_non_commandes.drop(columns=['_merge'])

# -- KPIs principaux
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🗂️ Total Articles", len(articles))
col2.metric("📦 Articles Commandés", len(articles_commandes))
col3.metric("🚫 Articles Non Commandés", len(articles_non_commandes))
col4.metric("💰 Montant Total Commandé", f"{commandes_avec_articles['montant_commande'].sum()/1_000_000:.2f} M MAD")
col5.metric("📊 Quantité Totale Commandée", f"{commandes_avec_articles['quantite'].sum():,.0f}")

# -- KPIs avancés
col6, col7, col8, col9 = st.columns(4)
if not articles_commandes.empty:
    top_qte = articles_commandes.sort_values(by='quantite_commandee_total', ascending=False).iloc[0]
    col6.metric("📌 Article le plus commandé", top_qte['designation'], f"{top_qte['quantite_commandee_total']:,.0f}")
    top_cost = articles_commandes.iloc[0]
    col7.metric("💿 Article le plus coûteux", top_cost['designation'], f"{top_cost['montant_total_payé'] / 1_000_000:.2f} M MAD")
else:
    col6.metric("📌 Article le plus commandé", "N/A", "0")
    col7.metric("💿 Article le plus coûteux", "N/A", "0")

annee_max = commandes_avec_articles.groupby('annee')['montant_commande'].sum().idxmax() if not commandes_avec_articles.empty else None
col8.metric("📈 Année la plus chargée", int(annee_max) if annee_max else "N/A")
prix_moyen = commandes_avec_articles['montant_commande'].sum() / commandes_avec_articles['quantite'].sum() if commandes_avec_articles['quantite'].sum() > 0 else 0
col9.metric("💵 Prix Unitaire Moyen", f"{prix_moyen:.2f} MAD")

# -- NOUVEAUX KPIs analytiques
col10, col11, col12 = st.columns(3)
articles_avec_demande = articles_commandes[articles_commandes['quantite_dm'].notnull()]
taux_utilisation_articles = len(articles_avec_demande) / len(articles_commandes) * 100 if len(articles_commandes) > 0 else 0
col10.metric("📊 Taux d'articles utilisés (avec DM)", f"{taux_utilisation_articles:.1f}%")
total_commande = articles_avec_demande['quantite_commandee_total'].sum()
total_dm = articles_avec_demande['quantite_dm'].sum()
ratio_global = total_commande / total_dm if total_dm else 0
col11.metric("📏 Ratio global Commande / Demande", f"{ratio_global:.2f}")
articles_surstock = articles_avec_demande[articles_avec_demande['ecart_dm_stock'] > 0]
col12.metric("📦 Articles surstockés", len(articles_surstock))

# --- Début des nouveaux KPIs ---

st.markdown("---")

# KPI 1 : Nombre moyen de fournisseurs par article commandé
fournisseurs_par_article = commandes_avec_articles.groupby('article_id')['fournisseur_id'].nunique().reset_index(name='nb_fournisseurs')
moy_fournisseurs = fournisseurs_par_article['nb_fournisseurs'].mean()
st.metric("🛒 Nombre moyen de fournisseurs par article commandé", f"{moy_fournisseurs:.2f}")

# KPI 2 : % Articles commandés auprès de plusieurs fournisseurs
pct_multi_fournisseurs = (fournisseurs_par_article['nb_fournisseurs'] > 1).mean() * 100
st.metric("🔀 % Articles commandés auprès de plusieurs fournisseurs", f"{pct_multi_fournisseurs:.1f}%")

# KPI 3 : Top 5 fournisseurs par montant commandé
top5_fournisseurs = commandes_avec_articles.groupby('fournisseur_id')['montant_commande'].sum().sort_values(ascending=False).head(5)
st.subheader("💼 Top 5 Fournisseurs par montant commandé")
fig_fournisseurs = px.bar(
    top5_fournisseurs.reset_index(),
    x='fournisseur_id',
    y='montant_commande',
    labels={'fournisseur_id': 'Fournisseur', 'montant_commande': 'Montant commandé (MAD)'},
    color='montant_commande',
    color_continuous_scale='Viridis'
)
st.plotly_chart(fig_fournisseurs, use_container_width=True)

# KPI 4 : Évolution mensuelle des quantités commandées pour l'année sélectionnée
if annee_selectionnee:
    commandes_mensuelles = commandes_avec_articles[commandes_avec_articles['annee'] == annee_selectionnee].copy()
    commandes_mensuelles['mois'] = commandes_mensuelles['date_commande'].dt.to_period('M').astype(str)
    agg_mensuel = commandes_mensuelles.groupby('mois')['quantite'].sum().reset_index()
    st.subheader(f"📈 Évolution mensuelle des quantités commandées en {annee_selectionnee}")
    fig_mensuel = px.line(
        agg_mensuel,
        x='mois',
        y='quantite',
        markers=True,
        labels={'mois': 'Mois', 'quantite': 'Quantité commandée'}
    )
    st.plotly_chart(fig_mensuel, use_container_width=True)

# KPI 5 : Top 5 Articles à forte volatilité mensuelle des quantités commandées
commandes_avec_articles['mois'] = commandes_avec_articles['date_commande'].dt.to_period('M')
volatilite = commandes_avec_articles.groupby(['article_id', 'mois'])['quantite'].sum().reset_index()
volatilite_par_article = volatilite.groupby('article_id')['quantite'].std().reset_index(name='volatilite_quantite')
volatilite_par_article = pd.merge(volatilite_par_article, articles[['article_id', 'designation']], on='article_id')
top_volatilite = volatilite_par_article.sort_values(by='volatilite_quantite', ascending=False).head(5)
st.subheader("⚡ Top 5 Articles à forte volatilité mensuelle des quantités commandées")
st.dataframe(top_volatilite[['designation', 'volatilite_quantite']])

# --- Fin des nouveaux KPIs ---

st.markdown("---")

# Articles commandés (table)
st.subheader("✅ Articles Commandés (totaux par article avec demande de matière)")
st.dataframe(articles_commandes[['article_id', 'designation', 'quantite_commandee_total', 'quantite_dm', 'ecart_dm_stock', 'montant_total_payé']])

# Articles non commandés (table)
st.subheader("⚠️ Articles Non Commandés")
st.dataframe(articles_non_commandes[['article_id', 'designation']])

# -- Tableau commandes avec article et fournisseur filtré
st.subheader("📋 Détail des commandes par fournisseur avec article désigné")
st.dataframe(
    commandes_avec_articles[
        ['fournisseur_id', 'article_id', 'designation', 'quantite', 'date_commande']
    ].sort_values(['fournisseur_id', 'date_commande'])
)

# -- Graphique évolution annuelle par article sélectionné
st.subheader("📅 Détail Annuel des Commandes par Article")
selected_article = st.selectbox(
    "Choisissez un article pour voir l'évolution annuelle",
    options=articles_commandes['designation'].tolist()
)

if selected_article:
    data_annee = agg_par_annee[agg_par_annee['designation'] == selected_article]
    if not data_annee.empty:
        st.dataframe(data_annee[['annee', 'quantite_commandee_annuelle', 'montant_annuel_payé']].sort_values('annee'))
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=data_annee['annee'],
            y=data_annee['montant_annuel_payé'] / 1_000,
            name="Montant payé (K MAD)",
            marker_color='indianred'
        ))
        fig.add_trace(go.Scatter(
            x=data_annee['annee'],
            y=data_annee['quantite_commandee_annuelle'],
            name="Quantité commandée",
            mode='lines+markers',
            yaxis="y2"
        ))
        fig.update_layout(
            title=f"📈 Évolution annuelle pour l'article : {selected_article}",
            yaxis=dict(title="Montant (K MAD)"),
            yaxis2=dict(title="Quantité", overlaying="y", side="right"),
            xaxis=dict(title="Année")
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Pas de données disponibles pour cet article.")

# -- Top 5 articles par montant total payé
st.subheader("🏆 Top 5 Articles par Montant Total Payé")
top5 = articles_commandes.head(5).copy()
top5['montant_kMAD'] = top5['montant_total_payé'] / 1_000
fig_top = px.bar(
    top5,
    x='designation',
    y='montant_kMAD',
    text='montant_kMAD',
    labels={'designation': 'Article', 'montant_kMAD': 'Montant (K MAD)'},
    color='montant_kMAD',
)
fig_top.update_traces(texttemplate='%{text:.1f}K', textposition='outside')
fig_top.update_layout(
    uniformtext_minsize=8,
    uniformtext_mode='hide',
    yaxis=dict(
        title="Montant (K MAD)",
        type='log',
        autorange=True
    )
)
st.plotly_chart(fig_top, use_container_width=True)

# -- Top 10 articles surstockés
top_surstock = articles_surstock.sort_values(by='ecart_dm_stock', ascending=False).head(10)
st.subheader("📈 Top 10 Articles Surcommandés (Surstock)")
fig_surstock = px.bar(
    top_surstock,
    x='designation',
    y='ecart_dm_stock',
    labels={'designation': 'Article', 'ecart_dm_stock': 'Surstock'},
    color_discrete_sequence=['#1f77b4']
)
st.plotly_chart(fig_surstock, use_container_width=True)

# -- Top 10 articles sous-stockés
articles_sousstock = articles_avec_demande[articles_avec_demande['ecart_dm_stock'] < 0]
top_sousstock = articles_sousstock.sort_values(by='ecart_dm_stock').head(10)
st.subheader("📉 Top 10 Articles Sous-commandés (Sous-stock)")
fig_sousstock = px.bar(
    top_sousstock,
    x='designation',
    y='ecart_dm_stock',
    labels={'designation': 'Article', 'ecart_dm_stock': 'Sous-stock'},
    color_discrete_sequence=['#d62728']
)
st.plotly_chart(fig_sousstock, use_container_width=True)

# -- Montant total par année (global)
st.subheader("📆 Montant Total des Commandes par Année")
montant_par_annee = commandes_avec_articles.groupby('annee')['montant_commande'].sum().reset_index()
fig_montant_annee = px.line(
    montant_par_annee,
    x='annee',
    y=montant_par_annee['montant_commande'] / 1_000_000,
    markers=True,
    labels={'annee': 'Année', 'y': 'Montant (M MAD)'}
)
fig_montant_annee.update_traces(texttemplate='%{y:.1f}M')
st.plotly_chart(fig_montant_annee, use_container_width=True)
