from crewai import Crew
import streamlit as st
from agents_hierarchical import create_hierarchical_crew
from crewai_tools.tools.geocoder_tool import extraire_points_gps
from agents_sequential import create_travel_crew
from crewai_tools.tools.database import get_vectorstore
from utils import afficher_resultat_mode
import time
from evaluation import afficher_dashboard_evaluation

st.set_page_config(page_title="Travel Planner Pro - Comparatif", page_icon="🌍", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "generation"

st.title("Générateur d'Itinéraires de Voyage")
st.markdown("Comparez l'impact du RAG et du Multi-Agent sur votre itinéraire.")

if "comparatif" not in st.session_state:
    st.session_state.comparatif = {}

# if 'WORKFLOW_STEPS' not in st.session_state:
#     st.session_state.WORKFLOW_STEPS = []

with st.sidebar:
    st.header("⚙️ Configuration")
    ville = st.selectbox("Destination", ["New_York", "Rome", "Japon"])
    profil = st.selectbox("Votre profil", ["Luxe", "Etudiant", "Aventure", "Famille"])
    
    col_a, col_e = st.columns(2)
    with col_a:
        adultes = st.number_input("Adultes", min_value=1, max_value=10, value=2)
    with col_e:
        enfants = st.number_input("Enfants", min_value=0, max_value=10, value=0)
        
    budget = st.select_slider("Budget total estimé (€)", options=["Économique", "Modéré", "Élevé"], value="Modéré")
    rythme = st.radio("Rythme du séjour", ["Détendu (1-2 lieux/jour)", "Équilibré (3 lieux/jour)", "Intense (Marathon)"], index=1)
    interets = st.multiselect( "Centres d'intérêt", ["Gastronomie", "Culture & Histoire", "Shopping", "Nature", "Vie nocturne"], default=["Gastronomie"])
    duree = st.slider("Nombre de jours", 1, 7, 3)

    st.write("---")
    btn_lancer = st.button("🚀 Lancer le comparatif complet", use_container_width=True, type="primary")

    st.write("---")
    if st.button("📊 Voir l'analyse détaillée", use_container_width=True):
        st.session_state.page = "evaluation"

    if st.session_state.page == "evaluation":
        if st.button("⬅️ Retour au générateur", use_container_width=True):
            st.session_state.page = "generation"
# --- LOGIQUE DE GÉNÉRATION ---
if st.session_state.page == "generation":
    if btn_lancer:
        configs = [
            {"id": "mode_1", "name": "👥​ Multi-Agents + 📚 RAG", "rag": True, "agents": True},
            {"id": "mode_2", "name": "👤 LLM Single + 📚 RAG", "rag": True, "agents": False},
            {"id": "mode_3", "name": "👥​ Multi-Agents Only", "rag": False, "agents": True},
            {"id": "mode_4", "name": "👤 LLM Single Only", "rag": False, "agents": False},
        ]
        
        st.session_state.comparatif = {}

        with st.status("🛠️ Génération des scénarios...", expanded=True) as status:
            for conf in configs:
                try:
                    mode_label = conf["name"]
                    st.write(f"⏳ Traitement de : **{mode_label}**...")
                    
                    start_time = time.time()
                    
                    # 1. Gestion du RAG
                    infos_contextuelles = ""
                    if conf["rag"]:
                        vectorstore = get_vectorstore(ville)
                        docs = vectorstore.similarity_search(f"activités et bonnes pratiques à {ville}", k=2)
                        infos_contextuelles = "\n\n".join([d.page_content for d in docs])

                    # 2. Exécution
                    instance = create_travel_crew(ville, profil, duree, budget, rythme, interets, adultes, enfants, infos_contextuelles, conf["agents"])
                    if isinstance(instance, Crew):
                        resultat_brut = instance.kickoff()
                    else:
                        resultat_brut = instance
                    # 3. Extraction GPS
                    points = extraire_points_gps(resultat_brut.raw, ville)
                    
                    st.session_state.comparatif[conf["id"]] = {
                        "label": mode_label,
                        "texte": resultat_brut.raw,
                        "points": points,
                        "sources": infos_contextuelles,
                        "temps": round(time.time() - start_time, 2)
                    }
                    
                    if conf != configs[-1]:
                        st.write("Wait for API cooldown...")
                        time.sleep(25) 

                except Exception as e:
                    st.error(f"Erreur sur {conf['name']} : {e}")
                    time.sleep(15)
                    continue
                    
            status.update(label="✅ Traitement terminé !", state="complete", expanded=False)
            
    
    if st.session_state.comparatif:
        st.write("---")
        
        labels = [v["label"] for v in st.session_state.comparatif.values()]
        tabs = st.tabs(labels)
        
        for i, (mode_id, data) in enumerate(st.session_state.comparatif.items()):
            with tabs[i]:
                afficher_resultat_mode(mode_id, data)
    else:
        st.info("Prêt à comparer ! Configurez vos préférences à gauche et lancez la simulation.")


    st.write("---")
    st.header("👑 Test Méthode Avancée")

    if st.button("🧪 Tester le mode Hiérarchique"):
        st.session_state.WORKFLOW_STEPS = []
        with st.spinner("Lancement de l'orchestration hiérarchique..."):
            try:
            # On réduit le RAG pour ce test
                vectorstore = get_vectorstore(ville)
                # k=1 est suffisant pour prouver le fonctionnement
                docs = vectorstore.similarity_search(f"noms de lieux à {ville}", k=1)
                
                # Limite EXTRÊME à 300 caractères (environ 50 mots)
                info_test = f"New York est divisée en 5 boroughs : Manhattan, Brooklyn, Queens, Bronx, Staten Island."
                
                # Ajoutez une pause forcée AVANT de lancer pour vider le quota Groq
                st.warning("Vidage du quota API (15s)...")
                time.sleep(10) 
                
                start_h = time.time()
                crew_h = create_hierarchical_crew(ville, profil, duree, budget, rythme, interets, adultes, enfants, info_test, True)
                result_h = crew_h.kickoff()
                st.success(f"✅ Terminé en {round(time.time() - start_h, 2)}s !")
                st.markdown(result_h.raw)

            except Exception as e:
                st.error(f"Erreur: {e}")


if st.session_state.page == "evaluation":
    config_voyage = {
        "ville": ville,
        "profil": profil,
        "duree": duree,
        "rythme": rythme,
        "adultes": adultes,
        "enfants": enfants,
        "interets": ", ".join(interets)
    }
    afficher_dashboard_evaluation(st, st.session_state.comparatif, config_voyage)