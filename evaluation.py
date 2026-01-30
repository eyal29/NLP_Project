import pandas as pd
import re
import os
import streamlit as st
import plotly.express as px
from geopy.distance import geodesic
from litellm import completion

def calculer_distance_totale(points):
    """Calcule la distance cumulée entre les points GPS en kilomètres."""
    if len(points) < 2:
        return 0
    
    dist_totale = 0
    for i in range(len(points) - 1):
        coord1 = (points[i]['lat'], points[i]['lon'])
        coord2 = (points[i+1]['lat'], points[i+1]['lon'])
        dist_totale += geodesic(coord1, coord2).km
    return round(dist_totale, 2)

    
def llm_judge_score(texte_itineraire, config):
    """
    Evalue la cohérence de l'itinéraire par rapport aux paramètres saisis.
    config: dict contenant ville, profil, budget, rythme, adultes, enfants, etc.
    """
    prompt = f"""
    Tu es un auditeur qualité pour une agence de voyage. 
    Ton rôle est de vérifier si l'itinéraire généré respecte STRICTEMENT la situation du client.

    --- SITUATION DU CLIENT ---
    - Destination : {config['ville']}
    - Durée : {config['duree']} jours
    - Profil : {config['profil']}
    - Groupe : {config['adultes']} adultes et {config['enfants']} enfants
    - Rythme : {config['rythme']}
    - Intérêts : {config['interets']}

    --- ITINÉRAIRE GÉNÉRÉ ---
    {texte_itineraire[:2500]}

    --- TA MISSION ---
    Note chaque critère sur 10 :
    1. PERSONNALISATION (10pts) : L'itinéraire cite-t-il des lieux précis et pertinents pour {config['profil']} ? (Pénalise fortement si les conseils sont génériques/bateaux).
    2. LOGISTIQUE GROUPE (10pts) : Est-ce adapté pour {config['enfants']} enfants ? Les temps de pause et le transport sont-ils réalistes ? S'il y a 0 enfant, ignore ce critère.
    3. COHÉRENCE GÉOGRAPHIQUE (10pts) : Les lieux d'une même demi-journée sont-ils proches ? (Pénalise les "allers-retours" inutiles dans la ville).
    4. RICHESSE DOCUMENTAIRE (10pts) : Y a-t-il des détails pratiques (prix, astuces, horaires) ou est-ce juste une liste ?

    --- INSTRUCTIONS DE CALCUL ---
    - Un itinéraire "moyen" ou "standard" doit obtenir 5/10.
    - Pour obtenir plus de 8/10, il faut une optimisation géographique parfaite et une personnalisation poussée.
    - Si l'itinéraire ignore la présence des enfants ou le budget, la note globale ne peut excéder 4/10.
    
    Réponds EXCLUSIVEMENT sous ce format :
    Note: [Moyenne des 4 critères]/10
    Justification: [Une analyse critique de 2 phrases maximum sur le respect des contraintes]
    """
    try:
        response = completion(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )
        content = response.choices[0].message.content
        note_match = re.search(r"Note:\s*([\d.]+)", content)
        justif_match = re.search(r"Justification:\s*(.*)", content)
        
        score = float(note_match.group(1)) if note_match else 5.0
        justif = justif_match.group(1) if justif_match else "Pas de justification fournie."
        print (f"🔍 DEBUG LLM JUDGE : Note = {score}, Justification = {justif}")
        return score, justif
    except Exception as e:
        return 0.0, f"Erreur d'analyse : {str(e)}"

def calculer_metriques(comparatif_dict, config_voyage):
    """
    Transforme les données du session_state en DataFrame enrichi.
    """
    metrics_list = []
    
    for mode_id, data in comparatif_dict.items():
        texte = data["texte"]
        
        # 1. Richesse (existante)
        nb_lieux = len(re.findall(r"[*•-]\s|\d\.", texte))
        
        # 2. Fidélité RAG (existante)
        score_rag = None
        if data["sources"]:
            mots_sources = set(data["sources"].lower().split())
            mots_reponse = set(texte.lower().split())
            if mots_sources:
                intersection = mots_sources.intersection(mots_reponse)
                score_rag = round(len(intersection) / len(mots_sources) * 100, 2)

        # 3. NOUVEAU : Distance Totale (Optimisation logistique)
        distance = calculer_distance_totale(data["points"])
        efficience = round(distance / max(nb_lieux, 1), 2)

        # 4. NOUVEAU : LLM Judge (Qualité sémantique)
        with st.spinner(f"Audit qualité pour : {data['label']}..."):
            score, raison = llm_judge_score(data["texte"], config_voyage)
        print(data['texte'])
        metrics_list.append({
            "Mode": data["label"],
            "Temps (s)": data["temps"],
            "Lieux identifiés": nb_lieux,
            "Fidélité RAG (%)": score_rag if data["sources"] else "N/A",
            "Distance Totale (km)": distance,
            "Efficience (km/lieu)": efficience,
            "Note Qualité (/10)": score,
            "Justification": raison,
            "Points GPS": len(data["points"])
        })
    
    return pd.DataFrame(metrics_list)

def afficher_dashboard_evaluation(st, comparatif_dict, config_voyage):
    """
    Rendu visuel complet dans l'onglet Analyse
    """
    st.header("📊 Analyse des résultats")
    st.markdown("Cette page compare l'efficacité brute (temps) à l'intelligence logistique et rédactionnelle.")
    
    if not comparatif_dict:
        st.warning("Aucune donnée disponible. Lancez la simulation d'abord.")
        return

    # Calcul des données
    df = calculer_metriques(comparatif_dict, config_voyage)

    # Affichage du tableau récapitulatif
    st.subheader("Synthèse des métriques")
    df_display = df.drop(columns=["Justification"]).copy()
    df_display["Fidélité RAG (%)"] = pd.to_numeric(df_display["Fidélité RAG (%)"], errors='coerce')
    st.dataframe(df_display.style.format({"Fidélité RAG (%)": "{:.2f}"}, na_rep="-"), width='stretch')

    # Rangée 1 : Performance vs Qualité
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Rapidité d'exécution**")
        fig_temps = px.bar(df, x="Mode", y="Temps (s)", color="Mode", text_auto=True)
        st.plotly_chart(fig_temps, width='stretch')
    
    with col2:
        st.write("**Score de Qualité (LLM Judge)**")
        fig_qual = px.line(df, x="Mode", y="Note Qualité (/10)", markers=True, range_y=[0,10])
        st.plotly_chart(fig_qual, width='stretch')

    # Rangée 2 : Logistique
    st.write("---")
    col3, col4 = st.columns(2)
    
    with col3:
        st.write("**Optimisation du trajet (Distance)**")
        fig_dist = px.bar(df, x="Mode", y="Distance Totale (km)", 
                          color_discrete_sequence=['#2ECC71'], text_auto=True)
        st.plotly_chart(fig_dist, width='stretch')
        st.caption("Une distance plus courte pour un même nombre de lieux indique une meilleure organisation géographique.")
    
    with col4:
        st.write("**Efficience Géographique (km par lieu)**")
        # On utilise une couleur différente pour bien distinguer
        fig_eff = px.bar(df, x="Mode", y="Efficience (km/lieu)", 
                          color_discrete_sequence=['#9B59B6'], text_auto=True)
        st.plotly_chart(fig_eff, width='stretch')
        st.caption("💡 **Plus le score est bas**, plus l'IA a regroupé les lieux intelligemment pour limiter les déplacements.")
    # with col4:
    #     df_rag = df[df["Fidélité RAG (%)"] != "N/A"]
    #     if not df_rag.empty:
    #         st.write("**Exploitation des sources (RAG)**")
    #         fig_rag = px.pie(df_rag, names="Mode", values="Fidélité RAG (%)", hole=0.4)
    #         st.plotly_chart(fig_rag, width='stretch')

    st.subheader("🧐 Verdict du LLM Judge")
    st.info("Le juge évalue si l'IA a respecté vos contraintes (enfants, rythme, centres d'intérêt).")
    
    # Affichage sous forme de "Cards" ou Expandeurs
    for _, row in df.iterrows():
        with st.expander(f"Détails du score pour : **{row['Mode']}** — {row['Note Qualité (/10)']}/10"):
            st.write(f"**Analyse critique :** {row['Justification']}")
            st.progress(row['Note Qualité (/10)'] / 10)