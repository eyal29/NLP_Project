import folium
from streamlit_folium import st_folium
import streamlit as st

def afficher_resultat_mode(mode_id, data):
    """Affiche le contenu avec un sélecteur pour alterner entre texte et carte"""
    
    vue = st.radio(
        "Choisir l'affichage :",
        ["📄 Itinéraire détaillé", "📍 Carte interactive"],
        horizontal=True,
        key=f"selector_{mode_id}",
        label_visibility="collapsed" 
    )

    st.write("---")

    if vue == "📄 Itinéraire détaillé":
        st.subheader(f"Détails du séjour ({data['temps']}s)")
        st.markdown(data["texte"])

    else:
        st.subheader("Visualisation géographique")
        if data["points"]:
            m = folium.Map(
                location=[data["points"][0]['lat'], data["points"][0]['lon']], 
                zoom_start=12
            )
            
            coords = [[p['lat'], p['lon']] for p in data["points"]]
            
            for i, p in enumerate(data["points"], start=1):
                folium.Marker(
                    [p['lat'], p['lon']], 
                    popup=f"Étape {i}: {p['name']}", 
                    tooltip=p['name'],
                    icon=folium.DivIcon(
                        icon_size=(30,30),
                        icon_anchor=(15,15),
                        html=f"""<div style="font-size: 12pt; color: white; background-color: #E74C3C; 
                                border-radius: 50%; width: 30px; height: 30px; display: flex; 
                                justify-content: center; align-items: center; border: 2px solid white; 
                                font-weight: bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">{i}</div>"""
                    )
                ).add_to(m)
            
            folium.PolyLine(coords, color="blue", weight=3, opacity=0.7).add_to(m)
            
            # Affichage de la carte
            st_folium(m, key=f"map_{mode_id}", use_container_width=True, height=600)
        else:
            st.info("Aucun lieu n'a pu être géolocalisé pour ce mode.")