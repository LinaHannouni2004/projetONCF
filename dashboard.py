import streamlit as st
import pandas as pd
import mysql.connector

# 🔹 Connexion MySQL (Docker)
conn = mysql.connector.connect(
    host="localhost",
    user="oncf",
    password="article",
    database="articles_db",
    port=3306
)

# 🔹 Récupération des données
df = pd.read_sql("SELECT * FROM articles", conn)

# 🔹 Titre principal
st.title("📊 Tableau de bord Achats")

# 🔹 Affichage des données
st.subheader("Aperçu des articles")
st.dataframe(df, use_container_width=True)

# 🔹 KPI simple
st.subheader("📦 Total des articles en stock")
st.metric("Quantité totale", f"{df['quantite_stock'].sum():,.2f}")
