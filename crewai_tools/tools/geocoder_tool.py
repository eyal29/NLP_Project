from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import json
import re
from litellm import completion
import streamlit as st

import time
from litellm import completion
# ... autres imports

def call_llm_with_retry(prompt, model="groq/llama-3.1-8b-instant", retries=3):
    """Tente l'appel API plusieurs fois en cas d'erreur 429"""
    for i in range(retries):
        try:
            return completion(
                model=model, 
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
        except Exception as e:
            if "429" in str(e) and i < retries - 1:
                wait_time = (2 ** i) * 5  # Attente exponentielle : 5s, 10s...
                print(f"Rate limit atteint. Attente de {wait_time}s...")
                time.sleep(wait_time)
                continue
            raise e


def extraire_points_gps(texte_itineraire, ville_destination):
    """
    1. Utilise le LLM pour extraire uniquement les NOMS des lieux.
    2. Utilise Geopy (OpenStreetMap) pour trouver les vraies coordonnées.
    """
    # Étape 1 : Demander au LLM une liste de noms simples
    time.sleep(3)
    prompt_noms = f"""Analyse cet itinéraire pour la ville de {ville_destination}.
                    Liste les noms officiels des monuments, parcs ou quartiers mentionnés (maximum 15).
                    Réponds uniquement avec une liste JSON de chaînes de caractères.
                    Format : ["Nom du lieu 1, {ville_destination}", "Nom du lieu 2, {ville_destination}"]
                    Itinéraire : {texte_itineraire}"""
    
    codes_pays = {"Japon": "jp", "Rome": "it", "New_York": "us"}
    code_iso = codes_pays.get(ville_destination)
    try:
        response = call_llm_with_retry(prompt_noms)
        res_content = response.choices[0].message.content
        # Nettoyage pour extraire le JSON
        match = re.search(r'\[.*\]', res_content, re.DOTALL)
        if not match:
            return []
        noms_lieux = json.loads(re.search(r'\[.*\]', response.choices[0].message.content, re.DOTALL).group())
        print(f"🔍 DEBUG LLM : Lieux extraits par l'IA ({len(noms_lieux)}) : {noms_lieux}")

        # Étape 2 : Géocodage via Nominatim (API Gratuite)
        geolocator = Nominatim(user_agent="my_travel_planner_app_v1")
        points_gps = []
        
        # On limite à 5 lieux pour ne pas être trop lent (Nominatim = 1 req/sec)
        for nom in noms_lieux[:10]:
            try:
                nom = nom[0] if isinstance(nom, list) else nom
                # Nettoyage rapide pour Nominatim (retrait des parenthèses)
                query = re.sub(r'\(.*?\)', '', nom).strip()
                # On force la recherche dans le pays spécifique si on le connaît
                location = geolocator.geocode(
                    query, 
                    timeout=10, 
                    country_codes=code_iso if code_iso else None
                )
                
                if location:
                    points_gps.append({
                        "name": nom,
                        "lat": location.latitude,
                        "lon": location.longitude
                    })
                    print(f"✅Trouvé -> {nom}")
                else:
                    print(f"❌Non trouvé -> {nom}")
                time.sleep(1) 
            except Exception:
                continue
        print(f"Points GPS extraits : {points_gps}")   
        return points_gps
    except Exception as e:
        st.error(f"Erreur extraction : {e}")
        return []