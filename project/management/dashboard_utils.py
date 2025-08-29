import math
import streamlit as st

def render(df, avoid_neutral=False):
    tag_columns = df.columns[3:]
    def has_tag(row):
        return any(int(row[col]) in [-1, 1] for col in tag_columns)
    
    if avoid_neutral:
        df = df[df.apply(has_tag, axis=1)].reset_index(drop=True)

    def render_tag(name, value):
        color = {
            1: "#b6e3a2",     # light green
            -1: "#f4aaaa"     # light red
        }[value]

        return f'<span style="background-color: {color}; padding: 4px 8px; border-radius: 12px; margin-right: 6px;">{name}</span>'
    
    players_per_page = 5
    num_pages = math.ceil(len(df) / players_per_page)
    page = st.number_input("Page", min_value=1, max_value=num_pages, value=1)

    start = (page - 1) * players_per_page
    end = start + players_per_page
    
    for _, row in df.iloc[start:end].iterrows():
        tags_html = ""
        for col in df.columns[3:]:
            if row[col] != 0:
                tags_html += render_tag(col, row[col])
        
        player_block = f"""
        <div style="border: 1px solid #ccc; border-radius: 12px; padding: 12px; margin-bottom: 10px;">
            <strong>{row['Player']}, {row['Team']}, {row['Position']}</strong><br>
            {tags_html}
        </div>
        """
        st.markdown(player_block, unsafe_allow_html=True)