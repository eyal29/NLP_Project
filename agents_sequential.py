import os
from crewai import Agent, Task, Crew, LLM, Process
from dotenv import load_dotenv
import streamlit as st
import time
import litellm

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
print(f"DEBUG: API Key loaded: {api_key[:10]}...")  # Affiche les 10 premiers caractères
if not api_key:
    print("ERROR: GROQ_API_KEY_CY not found in .env!")
# --- CONFIGURATION DES LLM ---

llm_synthese = LLM(
    model="groq/llama-3.1-8b-instant", 
    temperature=0, 
    api_key=api_key,
    max_tokens=2000, # Limite pour forcer la synthèse
    max_retries=3,          
    timeout=60,
)

llm_planification = LLM(
    model="groq/llama-3.1-8b-instant", 
    temperature=0, 
    api_key=api_key,
    max_retries=3,          
    timeout=60
)

def notify_streamlit_agent(step, agent_role):
    try:            
        st.toast(f"🤖 **{agent_role}** a terminé une étape", icon="✅")
        # time.sleep(5)
    except:
        pass

def create_travel_crew(ville, profil, duree, budget, rythme, interets, adultes, enfants, informations_rag, agents_active):
    
    #interpretation des paramètres
    total_personnes = adultes + enfants
    groupe_str = f"{adultes} adulte(s) et {enfants} enfant(s)"
    
    if budget == "Élevé":
        style_voyage = "luxueux, avec des restaurants étoilés, des guides privés et des hôtels 5 étoiles. Les prix doivent refléter le haut de gamme."
    elif budget == "Économique":
        style_voyage = "très abordable, type 'backpacking', avec des repas bon marché et des activités gratuites."
    else:
        style_voyage = "confortable mais raisonnable, mélangeant activités payantes et moments de détente."

    if agents_active:
    # Agent 1: L'Analyste Local (Expert RAG & Intérêts)
        expert_local = Agent(
            role="Spécialiste de Destination",
            goal=(
                f"Sélectionner 5-6 lieux à {ville} pour profil {profil}, intérêts: {interets}, groupe: {groupe_str}, style de voyage: {style_voyage}"
            ),
            backstory=(
                f"Expert local à {ville}. Sélectionne des lieux authentiques adaptés au profil et aux intérêts demandés."
            ),
            llm=llm_synthese,
            step_callback=lambda step: notify_streamlit_agent(step, "Spécialiste de Destination")
        )

        # Agent 2: Le Travel Designer (Logique & Rythme)
        designer = Agent(
            role="Concepteur d'Itinéraire personnalisé",
            goal=(
                f"Créer itinéraire {duree}j, rythme {rythme}, {enfants} enfant(s)"
            ),
            backstory=(
                "Tu es expert en logistique de voyage dans la ville {ville}. "
                "Ta priorité absolue est de minimiser la distance totale parcourue."
                "Tu regroupes les lieux par proximité géographique pour éviter les trajets inutiles"
                "et tu construis le trajet le plus logique et le plus court possible entre ces lieux. "
                "Organise le tout par quartier pour limiter le transport. (ex: un quartier différent par jour)"
                "Tu adaptes systématiquement les horaires et les temps de pause pour que le planning soit réaliste, "
                "agréable et adapté aux nombre d'enfants."
            ),
            llm=llm_planification,
            step_callback=lambda step: notify_streamlit_agent(step, "Concepteur d'Itinéraire personnalisé")
        )

        # Agent 3: Le Contrôleur Financier (Gestion du Budget)
        comptable = Agent(
            role="Auditeur Budgétaire",
            goal=(
                f"Calculer coût total pour {total_personnes} personnes, budget {budget}, style {style_voyage}"
            ),
            backstory=(
                f"Expert financier. Vérifie coûts réalistes style {style_voyage}, multiplie par {total_personnes}."
            ),
            llm=llm_synthese,
            step_callback=lambda step: notify_streamlit_agent(step, "Auditeur Budgétaire")
        )

        # Agent 4: Le Rédacteur Voyage (Synthèse & Style)
        redacteur = Agent(
            role="Rédacteur de Guide de Voyage",
            goal=(
                "Compiler itinéraire et budget en guide structuré"
            ),
            backstory=(
                "Éditeur voyage. Transforme données brutes en guide engageant adapté au profil."
            ),
            llm=llm_synthese,
            step_callback=lambda step: notify_streamlit_agent(step, "Rédacteur Final")
        )

        # --- TÂCHES PRÉCISES ET STRUCTURÉES ---

        t1 = Task(
            description=(
                f"Contexte: {informations_rag}\n"
                f"Sélectionne 5-6 lieux à {ville} pour {duree}j. Profil: {profil}, intérêts: {interets}, groupe: {groupe_str}.\n"
                "Liste: Nom + description courte."
            ),
            expected_output=(
                "Liste puces: Nom lieu + description courte."
            ),
            agent=expert_local
        )

        t2 = Task(
            description=(
                f"À partir de la liste de lieux fournie par le Spécialiste de Destination, sélectionne les 3 meilleurs par jour, "
                f"crée un planning jour par jour sur {duree} jours. "
                f"Respecte strictement le rythme {rythme}. "
                f"Inclus des temps de pause adaptés pour les {enfants} enfant(s). "
                "CONSIGNE STRICTE : Pour chaque journée, les lieux choisis DOIVENT se situer dans un rayon "
                "géographique restreint. Tu dois minimiser le kilométrage entre le lieu du matin et celui du soir. "
                "Élimine les lieux qui créent des 'pics' de distance inutiles. "
                "L'itinéraire doit être une boucle logique ou une ligne droite continue, jamais un va-et-vient."
                "INTERDICTION de faire une introduction ou une conclusion. "
                "Réponds UNIQUEMENT par un itinéraire structuré par jour."
            ),
            expected_output=(
                "Itinéraire jour par jour: Jour X : Matin: [Nom] | Midi: [Nom] | Après-midi: [Nom] | Soir: [Nom]"
            ),
            agent=designer,
            context=[t1]
        )

        t3 = Task(
            description=(
                f"À partir du planning détaillé, rédige une section BUDGET détaillée. "
                f"1) Crée un tableau Markdown avec les colonnes : Poste (Repas/Activités/Transport) | Prix unitaire | Total pour {total_personnes}. "
                f"2) Assure-toi que le niveau de prix correspond bien à un style de voyage {style_voyage}. "
                "3) Calcule le total final et ajoute une conversion en EUR (donne le total en devise locale puis en EUR). "
                "4) INTERDICTION de faire des introductions ou des explications en dehors du tableau. "
                "Donne UNIQUEMENT le tableau du budget."
            ),
            expected_output=(
                "Tableau: Poste | Prix unitaire | Total groupe + ligne total EUR."
            ),
            agent=comptable,
            context=[t2]
        )

        t4 = Task(
            description=(
                f"IMPORTANT: Ne montre JAMAIS ton raisonnement interne (Thought:, Action:, etc.). Donne DIRECTEMENT le guide final.\n\n"
                f"Tu reçois l'itinéraire structuré et l'analyse budgétaire détaillée. "
                f"Ta mission est de produire le document final en respectant cet ordre :\n"
                f"1) Une phrase d'introduction chaleureuse personnalisée pour le profil {profil}.\n"
                f"2) Le programme jour par jour (matin, midi, après-midi, soir) sur {duree} jours, "
                "présenté de façon claire, avec éventuellement des justifications brèves.\n"
                f"3) Une section 'Conseils de l'expert' basée sur le rythme {rythme} et si utile, les informations présente dans le guide: {informations_rag}\n"
                "Pour CHAQUE lieu mentionné, inclure :\n"
                    "- Une astuce pratique (ex: 'Réserver 2 jours avant')\n"
                    "- Une mention sur l'accessibilité avec des enfants\n"
                    "- L'horaire idéal de visite.\n"
                "Si ces infos manquent, utilise tes connaissances pour les ajouter de manière réaliste."
                "4) Le tableau budgétaire complet fourni par l'Auditeur Budgétaire.\n\n"
                "INTERDICTIONS STRICTES :\n"
                "- NE JAMAIS afficher 'Thought:', 'Action:', ou tout raisonnement interne\n"
                "- Ne pas inventer de nouveaux lieux : utilise uniquement les lieux fournis\n"
                "- Ne pas ajouter d'autres introductions ou conclusions inutiles\n"
                "Réponds UNIQUEMENT par le guide final Markdown, sans aucun commentaire de raisonnement."
            ),
            expected_output=(
                "Guide Markdown complet (intro + programme jour/jour + conseils de l'expert + tableau budgétaire) SANS aucun raisonnement interne visible."
            ),
            agent=redacteur,
            context=[t3]
        )

        return Crew(
            agents=[expert_local, designer, comptable, redacteur],
            tasks=[t1, t2, t3, t4],
            process=Process.sequential,
            verbose=False,
            cache=False
        )

    else:
        super_prompt = f"""
        Tu es un expert en planification de voyage. Ta mission est de créer un guide complet pour {ville} sur {duree} jours.
        
        CONTEXTE :
        - Profil : {profil}
        - Budget : {budget} (Style : {style_voyage})
        - Groupe : {groupe_str}
        - Intérêts : {interets}
        - Rythme : {rythme}
        - Données de référence (RAG) : {informations_rag}
        
        TU DOIS SUIVRE CES ÉTAPES STRICTEMENT :
        1. Sélectionner 3 lieux pertinents par jour basés sur les intérêts et le profil.
        2. Organiser ces lieux logiquement (proximité géographique) pour éviter les allers-retours.
        3. Créer un tableau budgétaire détaillé (Poste | Prix unitaire | Total pour {total_personnes}) incluant repas, activités et transports.
        4. Rédiger le guide final au format Markdown.
        
        STRUCTURE ATTENDUE DU DOCUMENT FINAL :
        - Une phrase d'introduction chaleureuse pour un profil {profil}.
        - Le programme jour par jour (Matin, Midi, Après-midi, Soir).
        - Une section 'Conseils de l'expert' basée sur le rythme {rythme}.
        - Le tableau budgétaire complet avec conversion en EUR.
        
        RÉPONDS UNIQUEMENT AVEC LE GUIDE FINAL EN MARKDOWN.
        """

        # Appel direct via LiteLLM
        response = litellm.completion(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": super_prompt}],
            temperature=0,
            api_key=api_key
        )
        
        # On extrait le texte
        resultat_texte = response.choices[0].message.content
        
        # Pour que app.py ne plante pas, on simule l'objet retourné par crew.kickoff()
        class SimpleResult:
            def __init__(self, raw, usage):
                self.raw = raw
                self.token_usage = usage
        
        # On crée une structure d'usage compatible
        usage_simule = response.usage 
        
        return SimpleResult(resultat_texte, usage_simule)