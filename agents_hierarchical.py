# agents_hierarchical.py
import os
from crewai import Agent, Task, Crew, LLM, Process
from dotenv import load_dotenv
import time
import streamlit as st

from agents_sequential import notify_streamlit_agent

load_dotenv()
api_key = os.getenv("GROQ_API_KEY_CY")

# Configuration LLM identique mais avec des limites strictes
llm_boss = LLM(
    model="groq/llama-3.3-70b-versatile", 
    temperature=0, 
    api_key=api_key,
    max_tokens=1000 # Plus petit pour éviter le Rate Limit
)

def task_completion_callback(task_output):
    """
    Cette fonction est appelée dès qu'une tâche est finie.
    Elle capture l'agent même si celui-ci n'a pas fait de 'Thought' (réflexion).
    """
    # Récupération de l'agent via task_output
    agent_role = getattr(task_output, 'agent', None)
    if agent_role:
        if agent_role not in st.session_state.WORKFLOW_STEPS:
            st.session_state.WORKFLOW_STEPS.append(agent_role)
            # On force un petit print console pour debug
            print(f"DEBUG: Tâche terminée par {agent_role}")


def create_hierarchical_crew(ville, profil, duree, budget, rythme, interets, adultes, enfants, informations_rag, agents_active):
    total_personnes = adultes + enfants
    groupe_str = f"{adultes} adulte(s) et {enfants} enfant(s)"
    
    if budget == "Élevé":
        style_voyage = "luxueux, avec des restaurants étoilés, des guides privés et des hôtels 5 étoiles. Les prix doivent refléter le haut de gamme."
    elif budget == "Économique":
        style_voyage = "très abordable, type 'backpacking', avec des repas bon marché et des activités gratuites."
    else:
        style_voyage = "confortable mais raisonnable, mélangeant activités payantes et moments de détente."

    if agents_active:
        expert_local = Agent(
                role="Spécialiste de Destination",
                goal=(
                    f"Identifier et sélectionner les meilleurs lieux à {ville} "
                    f"pour un profil {profil} s'intéressant à {interets} "
                    f"et correspondant à un style de voyage {style_voyage}, "
                    f"en tenant compte de la composition du groupe : {groupe_str}."
                ),
                backstory=(
                    f"Tu vis à {ville}. Tu connais très bien la ville et ses quartiers. "
                    f"Tu analyses les données RAG fournies : {informations_rag}. "
                    f"Tu identifies uniquement les lieux qui correspondent réellement aux intérêts ({interets}) "
                    f"et qui sont adaptés à un groupe de {groupe_str}. "
                    "Tu es exigeant : tu privilégies les lieux authentiques, pertinents et réalistes."
                ),
                llm=llm_boss,
                max_iter=2,
                allow_delegation=False,
                step_callback=lambda step: notify_streamlit_agent(step, "Spécialiste de Destination"),
            )

        # Agent 2: Le Travel Designer (Logique & Rythme)
        designer = Agent(
            role="Concepteur d'Itinéraire personnalisé",
            goal=(
                f"Transformer la liste de lieux en un itinéraire jour par jour sur {duree} jours, "
                f"en respectant un rythme {rythme} et la présence de {enfants} enfant(s)."
            ),
            backstory=(
                "Tu es expert en logistique de voyage. "
                "Tu regroupes les lieux par proximité géographique pour éviter les trajets inutiles "
                "et tu construis le trajet le plus logique et le plus court possible entre ces lieux. "
                "Tu adaptes systématiquement les horaires et les temps de pause pour que le planning soit réaliste, "
                "agréable et adapté aux enfants."
            ),
            llm=llm_boss,
            max_iter=2,
            allow_delegation=False,
            step_callback=lambda step: notify_streamlit_agent(step, "Concepteur d'Itinéraire personnalisé"),
        )

        # Agent 3: Le Contrôleur Financier (Gestion du Budget)
        comptable = Agent(
            role="Auditeur Budgétaire",
            goal=(
                f"Calculer et valider le coût total du séjour pour {total_personnes} personnes "
                f"en fonction du budget {budget} et du style de voyage {style_voyage}."
            ),
            backstory=(
                "Tu es obsédé par la précision financière. "
                "Tu vérifies que chaque activité, chaque repas et chaque transport a un coût réaliste "
                f"pour un style de voyage {style_voyage}, et tu multiplies toujours les montants par {total_personnes}. "
                "Tu fais très attention à ce que le total final reste cohérent avec le budget annoncé."
            ),
            llm=llm_boss,
            max_iter=2,
            allow_delegation=False,
            step_callback=lambda step: notify_streamlit_agent(step, "Auditeur Budgétaire"),
        )

        # Agent 4: Le Rédacteur Voyage (Synthèse & Style)
        redacteur = Agent(
            role="Rédacteur de Guide de Voyage",
            goal=(
                "Compiler les analyses techniques (itinéraire et budget) "
                "en un guide de voyage clair, fluide, structuré et agréable à lire."
            ),
            backstory=(
                "Tu es un éditeur professionnel pour un grand magazine de voyage. "
                "Tu prends des informations brutes (lieux, horaires, calculs financiers) "
                "et tu les transformes en un récit structuré et engageant. "
                "Tu adaptes le ton au profil du voyageur, en restant concret, rassurant et inspirant."
                "Tu ne dois jamais afficher ton raisonnement interne. "
                "Si tu as besoin de réfléchir étape par étape, fais-le mentalement, mais ne sors que la réponse finale demandée au format attendu."
            ),
            llm=llm_boss,
            max_iter=2,
            allow_delegation=False,
            step_callback=lambda step: notify_streamlit_agent(step, "Rédateur de Guide de Voyage"),
        )

        # --- TÂCHES PRÉCISES ET STRUCTURÉES ---

        t1 = Task(
            description=(
                f"Analyse les sources (PDF, données RAG, etc.) concernant {ville} : {informations_rag}. "
                f"Sélectionne exactement 3 lieux par jour à {ville} pour {duree} jours. "
                f"Sélectionne uniquement des lieux adéquats pour le profil {profil} et les intérêts {interets}, "
                f"et adaptés à la composition du groupe : {groupe_str}. "
                "INTERDICTION de faire une introduction ou une conclusion. "
                "Réponds UNIQUEMENT par une liste de noms de lieux, chacun suivi d'une phrase courte de description "
                "et d'une justification rapide par rapport au profil."
            ),
            expected_output=(
                "Une liste de lieux, sous forme de puces ou de lignes, avec pour chacun : "
                "Nom du lieu + phrase courte de description + justification par rapport au profil."
            ),
            agent=expert_local,
            callback=task_completion_callback,
        )

        t2 = Task(
            description=(
                f"À partir de la liste de lieux fournie par le Spécialiste de Destination, "
                f"crée un planning jour par jour sur {duree} jours. "
                f"Respecte strictement le rythme {rythme}. "
                f"Inclus des temps de pause adaptés pour les {enfants} enfant(s). "
                "Regroupe les lieux par proximité géographique : l'itinéraire doit être logique et ne doit surtout pas contenir d' aller-retours inutiles. "
                "INTERDICTION de faire une introduction ou une conclusion. "
                "Réponds UNIQUEMENT par un itinéraire structuré par jour."
            ),
            expected_output=(
                "Un itinéraire structuré par jour, avec pour chaque jour les sections : "
                "Matin, Midi, Après-midi, Soir, chacune contenant les lieux/activités prévus."
            ),
            agent=designer,
            callback=task_completion_callback,
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
                "Un tableau Markdown des coûts, avec au minimum les colonnes : "
                "Poste | Prix unitaire | Total pour le groupe, plus une ligne récapitulative du total "
                "avec conversion en EUR."
            ),
            agent=comptable,
            callback=task_completion_callback,
        )

        t4 = Task(
            description=(
                f"Tu reçois l'itinéraire structuré et l'analyse budgétaire détaillée. "
                f"Ta mission est de produire le document final en respectant cet ordre :\n"
                f"1) Une phrase d'introduction chaleureuse personnalisée pour le profil {profil}.\n"
                f"2) Le programme jour par jour (matin, midi, après-midi, soir) sur {duree} jours, "
                "présenté de façon claire, avec éventuellement des justifications brèves.\n"
                f"3) Une section 'Conseils de l'expert' basée sur le rythme {rythme} et inspirée, si utile, "
                f"par les bonnes pratiques présentes dans le guide / les données : {informations_rag}."
                f"Cette section ne doit pas dépasser 5 phrases.\n"
                "4) Le tableau budgétaire complet fourni par l'Auditeur Budgétaire.\n\n"
                "Interdictions :\n"
                "- Ne pas inventer de nouveaux lieux : utilise uniquement les lieux fournis par les agents précédents.\n"
                "- Ne pas ajouter d'autres introductions ou conclusions inutiles.\n"
                "Réponds UNIQUEMENT par le programme final complet, bien mis en forme en Markdown."
            ),
            expected_output=(
                "Un guide de voyage final en Markdown, avec : "
                "une courte phrase d'introduction personnalisée, le programme jour par jour, "
                "une section 'Conseils de l'expert', puis le tableau budgétaire."
            ),
            agent=redacteur,
            callback=task_completion_callback,
        )
    

    # 3. La Crew Hiérarchique
    return Crew(
        agents=[expert_local, designer, comptable, redacteur],
        tasks=[t1, t2, t3, t4],
        process=Process.hierarchical,
        manager_llm=llm_boss,
        max_rpm=1,            # Sécurité pour Groq
        verbose=True,
        cache=False,
        )



