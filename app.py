import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from groq import Groq
import os

# ─── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tableau de Bord Éducation",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #f8fafc; }

    .dashboard-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 60%, #4a9eca 100%);
        border-radius: 16px; padding: 28px 36px; margin-bottom: 24px;
        color: white; box-shadow: 0 8px 32px rgba(30,58,95,0.25);
    }
    .dashboard-header h1 { font-size: 1.9rem; font-weight: 700; margin: 0 0 4px 0; }
    .dashboard-header p  { font-size: 0.9rem; margin: 0; opacity: 0.85; }

    .section-title {
        font-size: 1rem; font-weight: 600; color: #1e3a5f;
        margin: 8px 0 14px 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;
    }
    .insight-box {
        background: #eff6ff; border-left: 4px solid #2d6a9f;
        border-radius: 8px; padding: 12px 16px; margin: 6px 0;
        font-size: 0.88rem; color: #1e3a5f;
    }
    .msg-user {
        background: #1e3a5f; color: white;
        border-radius: 12px 12px 2px 12px;
        padding: 10px 15px; margin: 8px 0 8px 60px; font-size: 0.88rem; line-height: 1.5;
    }
    .msg-ai {
        background: #f1f5f9; color: #1e293b;
        border-radius: 12px 12px 12px 2px;
        padding: 10px 15px; margin: 8px 60px 8px 0; font-size: 0.88rem; line-height: 1.5;
    }
    .msg-label { font-size: 0.72rem; font-weight: 600; color: #94a3b8; margin-bottom: 2px; }
    .chat-container {
        background: white; border-radius: 14px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        padding: 20px; min-height: 280px; max-height: 400px; overflow-y: auto;
    }
    .stPlotlyChart { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ─── Data ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    return pd.read_csv("dataset_education.csv")

df = load_data()

COLOR_NIVEAU = {"primaire": "#1e3a5f", "secondaire": "#2d6a9f", "universitaire": "#4a9eca"}
COLOR_TYPE   = {"public": "#1e3a5f", "privé": "#e07b39"}

# ─── Session state init ───────────────────────────────────────────────────────
if "messages"    not in st.session_state: st.session_state.messages    = []
if "toast_shown" not in st.session_state: st.session_state.toast_shown = False

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=60)
    st.markdown("## 🎛️ Panneau de contrôle")
    st.markdown("---")

    st.markdown("### 🔍 Filtres")
    niveaux = st.multiselect(
        "Niveau d'établissement",
        options=df["niveau_etablissement"].unique().tolist(),
        default=df["niveau_etablissement"].unique().tolist(),
    )
    types = st.multiselect(
        "Type d'établissement",
        options=df["type_etablissement"].unique().tolist(),
        default=df["type_etablissement"].unique().tolist(),
    )
    budget_range = st.slider(
        "💰 Plage de budget",
        int(df["budget_education"].min()),
        int(df["budget_education"].max()),
        (int(df["budget_education"].min()), int(df["budget_education"].max())),
        step=10,
    )
    enseignants_range = st.slider(
        "👩‍🏫 Nombre d'enseignants",
        int(df["nombre_enseignants"].min()),
        int(df["nombre_enseignants"].max()),
        (int(df["nombre_enseignants"].min()), int(df["nombre_enseignants"].max())),
    )

    st.markdown("---")
    st.markdown("### ⚙️ Options d'affichage")
    show_trendline   = st.toggle("📈 Afficher les tendances", value=True)
    show_annotations = st.toggle("🏷️ Afficher les annotations", value=True)
    dark_mode_corr   = st.toggle("🎨 Heatmap inversée", value=False)
    nb_bins          = st.slider("📊 Bins histogramme", 10, 50, 20)
    graph_type       = st.radio(
        "📦 Type de graphique budget",
        ["Box plot", "Violin", "Strip"],
        horizontal=True,
    )

    st.markdown("---")
    st.markdown("### 📁 Dataset")
    st.info(f"**{len(df)}** établissements · **5** variables\n\n Aucune valeur manquante\n Sans doublons")

    if st.button("🔄 Réinitialiser les filtres", use_container_width=True):
        st.rerun()

# ─── Filtrage ─────────────────────────────────────────────────────────────────
dff = df[
    df["niveau_etablissement"].isin(niveaux) &
    df["type_etablissement"].isin(types) &
    df["budget_education"].between(*budget_range) &
    df["nombre_enseignants"].between(*enseignants_range)
]

# ─── Toasts ───────────────────────────────────────────────────────────────────
if not st.session_state.toast_shown:
    st.toast("🎓 Tableau de bord chargé avec succès !", icon="✅")
    st.session_state.toast_shown = True

if len(dff) < 10:
    st.toast(f"⚠️ Seulement {len(dff)} établissements sélectionnés !", icon="⚠️")

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="dashboard-header">
    <h1>🎓 Tableau de Bord Éducation</h1>
    <p>Analyse des établissements · Budget · Enseignants · Taux de réussite · Propulsé par Groq IA</p>
</div>
""", unsafe_allow_html=True)

# Info filtre actif
pct_affiche = len(dff) / len(df) * 100
if pct_affiche < 100:
    st.info(f"🔎 **{len(dff)} établissements** affichés ({pct_affiche:.0f}% du dataset) selon vos filtres.")

# ─── KPIs avec st.metric + delta ──────────────────────────────────────────────
st.markdown('<div class="section-title">📌 Indicateurs Clés</div>', unsafe_allow_html=True)

delta_budget   = dff["budget_education"].mean()   - df["budget_education"].mean()
delta_ens      = dff["nombre_enseignants"].mean()  - df["nombre_enseignants"].mean()
delta_reussite = dff["taux_reussite"].mean()       - df["taux_reussite"].mean()
delta_total    = dff["budget_education"].sum()     - df["budget_education"].sum()

k1, k2, k3, k4, k5 = st.columns(5)
with k1: st.metric("🏫 Établissements",   f"{len(dff)}",                             delta=f"{len(dff)-len(df)} vs total")
with k2: st.metric("💰 Budget moyen",     f"{dff['budget_education'].mean():,.0f}",   delta=f"{delta_budget:+.0f}")
with k3: st.metric("👩‍🏫 Enseignants moy.", f"{dff['nombre_enseignants'].mean():.1f}", delta=f"{delta_ens:+.1f}")
with k4: st.metric("🏆 Taux de réussite", f"{dff['taux_reussite'].mean():.1f}%",      delta=f"{delta_reussite:+.1f}%")
with k5: st.metric("💵 Budget total",     f"{dff['budget_education'].sum():,}",        delta=f"{delta_total:+,.0f}")

st.markdown("<br>", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Distributions",
    "💰 Budget & RH",
    "🏆 Réussite",
    "🔍 Corrélations",
    "📋 Données",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Distributions
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    c1, c2, c3 = st.columns(3)
    with c1:
        fig = px.pie(dff, names="niveau_etablissement", hole=0.55,
                     color="niveau_etablissement", color_discrete_map=COLOR_NIVEAU,
                     title="Répartition par niveau")
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=40,b=10,l=10,r=10), height=280,
                          plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.pie(dff, names="type_etablissement", hole=0.55,
                     color="type_etablissement", color_discrete_map=COLOR_TYPE,
                     title="Public vs Privé")
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=40,b=10,l=10,r=10), height=280,
                          plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        agg = dff.groupby(["niveau_etablissement","type_etablissement"]).size().reset_index(name="count")
        fig = px.bar(agg, x="niveau_etablissement", y="count", color="type_etablissement",
                     barmode="group", color_discrete_map=COLOR_TYPE, title="Niveau × Type", text="count")
        fig.update_traces(textposition="outside")
        fig.update_layout(legend_title_text="", margin=dict(t=40,b=10,l=10,r=10), height=280,
                          plot_bgcolor="white", paper_bgcolor="white",
                          xaxis_title="", yaxis_title="Nb établissements")
        st.plotly_chart(fig, use_container_width=True)

    if show_annotations and len(dff) > 0:
        st.markdown('<div class="section-title">💡 Insights automatiques</div>', unsafe_allow_html=True)
        top_niveau = dff["niveau_etablissement"].value_counts().idxmax()
        top_type   = dff["type_etablissement"].value_counts().idxmax()
        pct_prive  = (dff["type_etablissement"] == "privé").mean() * 100
        st.markdown(f'<div class="insight-box">🏫 Le niveau <b>{top_niveau}</b> est le plus représenté dans la sélection actuelle.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box">🏛️ Les établissements <b>{top_type}</b> dominent avec <b>{pct_prive if top_type=="privé" else 100-pct_prive:.0f}%</b> de la sélection.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Budget & RH
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    c4, c5 = st.columns(2)
    with c4:
        if graph_type == "Box plot":
            fig = px.box(dff, x="niveau_etablissement", y="budget_education",
                         color="niveau_etablissement", color_discrete_map=COLOR_NIVEAU,
                         title="Distribution du budget par niveau", points="outliers")
        elif graph_type == "Violin":
            fig = px.violin(dff, x="niveau_etablissement", y="budget_education",
                            color="niveau_etablissement", color_discrete_map=COLOR_NIVEAU,
                            title="Distribution du budget (Violin)", box=True)
        else:
            fig = px.strip(dff, x="niveau_etablissement", y="budget_education",
                           color="niveau_etablissement", color_discrete_map=COLOR_NIVEAU,
                           title="Distribution du budget (Strip)")
        fig.update_layout(showlegend=False, margin=dict(t=40,b=10,l=10,r=10), height=320,
                          plot_bgcolor="#f8fafc", paper_bgcolor="white",
                          xaxis_title="", yaxis_title="Budget")
        st.plotly_chart(fig, use_container_width=True)

    with c5:
        fig = px.histogram(dff, x="nombre_enseignants", color="type_etablissement",
                           color_discrete_map=COLOR_TYPE, barmode="overlay", opacity=0.75,
                           title="Distribution du nombre d'enseignants", nbins=nb_bins)
        fig.update_layout(legend_title_text="Type", margin=dict(t=40,b=10,l=10,r=10), height=320,
                          plot_bgcolor="#f8fafc", paper_bgcolor="white",
                          xaxis_title="Nombre d'enseignants", yaxis_title="Fréquence")
        st.plotly_chart(fig, use_container_width=True)

    avg_budget = dff.groupby(["niveau_etablissement","type_etablissement"])["budget_education"].mean().reset_index()
    fig = px.bar(avg_budget, x="niveau_etablissement", y="budget_education",
                 color="type_etablissement", barmode="group", color_discrete_map=COLOR_TYPE,
                 title="Budget moyen par niveau et type",
                 text=avg_budget["budget_education"].apply(lambda x: f"{x:.0f}"))
    fig.update_traces(textposition="outside")
    fig.update_layout(legend_title_text="", margin=dict(t=40,b=10,l=10,r=10), height=300,
                      plot_bgcolor="#f8fafc", paper_bgcolor="white",
                      xaxis_title="", yaxis_title="Budget moyen")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">📐 Statistiques avancées</div>', unsafe_allow_html=True)
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a: st.metric("Budget médian",  f"{dff['budget_education'].median():,.0f}")
    with col_b: st.metric("Budget max",     f"{dff['budget_education'].max():,}")
    with col_c: st.metric("Budget min",     f"{dff['budget_education'].min():,}")
    with col_d: st.metric("Écart-type",     f"{dff['budget_education'].std():,.0f}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Réussite
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    c6, c7 = st.columns(2)
    with c6:
        avg_tr = dff.groupby("niveau_etablissement")["taux_reussite"].mean().reset_index()
        avg_tr.columns = ["niveau","taux_moyen"]
        avg_tr = avg_tr.sort_values("taux_moyen", ascending=True)
        fig = px.bar(avg_tr, x="taux_moyen", y="niveau", orientation="h",
                     color="taux_moyen", color_continuous_scale=["#b8dff0","#1e3a5f"],
                     title="Taux de réussite moyen par niveau",
                     text=avg_tr["taux_moyen"].apply(lambda x: f"{x:.1f}%"))
        fig.update_traces(textposition="outside")
        fig.update_layout(coloraxis_showscale=False, margin=dict(t=40,b=10,l=10,r=10), height=280,
                          plot_bgcolor="#f8fafc", paper_bgcolor="white",
                          xaxis_title="Taux moyen (%)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with c7:
        avg_type = dff.groupby(["niveau_etablissement","type_etablissement"])["taux_reussite"].mean().reset_index()
        fig = px.bar(avg_type, x="niveau_etablissement", y="taux_reussite",
                     color="type_etablissement", barmode="group", color_discrete_map=COLOR_TYPE,
                     title="Taux de réussite : Public vs Privé",
                     text=avg_type["taux_reussite"].apply(lambda x: f"{x:.0f}%"))
        fig.update_traces(textposition="outside")
        fig.update_layout(legend_title_text="", margin=dict(t=40,b=10,l=10,r=10), height=280,
                          plot_bgcolor="#f8fafc", paper_bgcolor="white",
                          xaxis_title="", yaxis_title="Taux moyen (%)")
        st.plotly_chart(fig, use_container_width=True)

    scale = ["#1e3a5f","#b8dff0"] if dark_mode_corr else ["#b8dff0","#1e3a5f"]
    pivot = dff.groupby(["niveau_etablissement","type_etablissement"])["taux_reussite"].mean().unstack()
    fig = px.imshow(pivot, text_auto=".1f", color_continuous_scale=scale,
                    title="Heatmap : Taux de réussite moyen (Niveau × Type)")
    fig.update_layout(margin=dict(t=40,b=10,l=10,r=10), height=280,
                      paper_bgcolor="white", xaxis_title="Type", yaxis_title="Niveau")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">📊 Performance relative par niveau</div>', unsafe_allow_html=True)
    max_tr = dff["taux_reussite"].max() if len(dff) > 0 else 1
    moy_globale = dff["taux_reussite"].mean()
    for niveau, grp in dff.groupby("niveau_etablissement"):
        moy = grp["taux_reussite"].mean()
        col_l, col_r = st.columns([4, 1])
        with col_l:
            st.progress(min(moy / max_tr, 1.0), text=f"**{niveau.capitalize()}** — {moy:.1f}%")
        with col_r:
            st.metric("", f"{moy:.1f}%", delta=f"{moy - moy_globale:+.1f}%")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Corrélations
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    trendline_opt = "ols" if show_trendline else None
    c8, c9 = st.columns(2)

    with c8:
        fig = px.scatter(dff, x="budget_education", y="taux_reussite",
                         color="niveau_etablissement", symbol="type_etablissement",
                         color_discrete_map=COLOR_NIVEAU, trendline=trendline_opt,
                         title="Budget vs Taux de réussite", hover_data=["nombre_enseignants"])
        fig.update_layout(legend_title_text="Niveau", margin=dict(t=40,b=10,l=10,r=10), height=340,
                          plot_bgcolor="#f8fafc", paper_bgcolor="white",
                          xaxis_title="Budget", yaxis_title="Taux de réussite (%)")
        st.plotly_chart(fig, use_container_width=True)

    with c9:
        fig = px.scatter(dff, x="nombre_enseignants", y="taux_reussite",
                         color="type_etablissement", color_discrete_map=COLOR_TYPE,
                         trendline=trendline_opt, size="budget_education",
                         title="Enseignants vs Taux de réussite (taille = budget)",
                         hover_data=["niveau_etablissement"])
        fig.update_layout(legend_title_text="Type", margin=dict(t=40,b=10,l=10,r=10), height=340,
                          plot_bgcolor="#f8fafc", paper_bgcolor="white",
                          xaxis_title="Nombre d'enseignants", yaxis_title="Taux de réussite (%)")
        st.plotly_chart(fig, use_container_width=True)

    corr_matrix = dff[["budget_education","nombre_enseignants","taux_reussite"]].corr()
    scale2 = ["#1e3a5f","white","#e07b39"] if dark_mode_corr else ["#b8dff0","white","#1e3a5f"]
    fig = px.imshow(corr_matrix, text_auto=".3f", color_continuous_scale=scale2,
                    zmin=-1, zmax=1, title="Matrice de corrélation entre variables numériques")
    fig.update_layout(margin=dict(t=40,b=10,l=10,r=10), height=300, paper_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

    if show_annotations and len(dff) > 1:
        def interpret(r):
            a = abs(r)
            sens = "positive" if r > 0 else "négative"
            if a > 0.7:   return f"forte ({sens})"
            elif a > 0.4: return f"modérée ({sens})"
            elif a > 0.2: return f"faible ({sens})"
            else:         return "très faible / nulle"

        corr_br = corr_matrix.loc["budget_education","taux_reussite"]
        corr_er = corr_matrix.loc["nombre_enseignants","taux_reussite"]
        corr_be = corr_matrix.loc["budget_education","nombre_enseignants"]
        st.markdown('<div class="section-title">📝 Interprétations</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box">📌 Budget ↔ Réussite : corrélation <b>{interpret(corr_br)}</b> (r = {corr_br:.3f})</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box">📌 Enseignants ↔ Réussite : corrélation <b>{interpret(corr_er)}</b> (r = {corr_er:.3f})</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="insight-box">📌 Budget ↔ Enseignants : corrélation <b>{interpret(corr_be)}</b> (r = {corr_be:.3f})</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Données
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    col_search, col_sort = st.columns([3, 1])
    with col_search:
        search = st.text_input("🔍 Rechercher dans les données…", placeholder="Ex: primaire, public…")
    with col_sort:
        sort_col = st.selectbox("Trier par", dff.columns.tolist(), index=4)

    df_display = dff.copy()
    if search:
        mask = df_display.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        df_display = df_display[mask]
        st.toast(f"🔎 {len(df_display)} résultat(s) pour « {search} »", icon="🔍")

    df_display = df_display.sort_values(sort_col, ascending=False).reset_index(drop=True)

    st.dataframe(
        df_display.style
            .background_gradient(subset=["budget_education","taux_reussite"], cmap="Blues")
            .format({"budget_education": "{:,.0f}", "taux_reussite": "{:.2f}", "nombre_enseignants": "{:.0f}"}),
        use_container_width=True, height=380
    )

    col_dl, col_info = st.columns([2, 3])
    with col_dl:
        csv = df_display.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Télécharger la sélection (CSV)", csv,
                           file_name="education_filtre.csv", mime="text/csv",
                           use_container_width=True)
    with col_info:
        st.caption(f"**{len(df_display)}** lignes · triées par **{sort_col}** (décroissant)")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION IA
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="dashboard-header" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%); margin-top:10px;">
    <h1>🤖 Assistant IA — Analyste Éducation</h1>
    <p>Posez vos questions · Groq (LLaMA 3.3 70B) analyse le jeu de données filtré en temps réel</p>
</div>
""", unsafe_allow_html=True)

def build_data_context(dataframe):
    stats         = dataframe.describe().to_string()
    dist_niveau   = dataframe["niveau_etablissement"].value_counts().to_string()
    dist_type     = dataframe["type_etablissement"].value_counts().to_string()
    corr          = dataframe[["budget_education","nombre_enseignants","taux_reussite"]].corr().to_string()
    avg_by_niveau = dataframe.groupby("niveau_etablissement")[["budget_education","nombre_enseignants","taux_reussite"]].mean().to_string()
    avg_by_type   = dataframe.groupby("type_etablissement")[["budget_education","nombre_enseignants","taux_reussite"]].mean().to_string()
    return f"""
Tu es un expert en analyse de données éducatives. Réponds toujours en français.
Voici les données actuellement filtrées ({len(dataframe)} établissements) :

STATISTIQUES DESCRIPTIVES:
{stats}

DISTRIBUTION PAR NIVEAU:
{dist_niveau}

DISTRIBUTION PAR TYPE:
{dist_type}

MOYENNES PAR NIVEAU:
{avg_by_niveau}

MOYENNES PAR TYPE:
{avg_by_type}

MATRICE DE CORRÉLATION:
{corr}

Réponds de manière claire, précise et structurée. Utilise des chiffres issus des données.
Sois concis mais complet. Propose des insights actionnables quand c'est pertinent.
"""

def call_groq(messages, data_context):
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return "⚠️ Clé API Groq manquante. Définis la variable d'environnement `GROQ_API_KEY`."
    if not messages:
        return "⚠️ Aucun message à envoyer."
    try:
        client = Groq(api_key=api_key)
        history = [{"role": "system", "content": data_context}]
        for m in messages:
            role = "user" if m["role"] == "user" else "assistant"
            history.append({"role": role, "content": m["content"]})
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=history,
            max_tokens=1024,
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Erreur Groq : {e}"

# Suggestions rapides
st.markdown("**💡 Questions suggérées :**")
sugg_cols = st.columns(4)
suggestions = [
    "Quels insights clés retenir ?",
    "Quel niveau a le meilleur taux de réussite ?",
    "Y a-t-il une corrélation budget/réussite ?",
    "Comparez public et privé",
]
for i, (col, sug) in enumerate(zip(sugg_cols, suggestions)):
    with col:
        if st.button(sug, key=f"sug_{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": sug})
            st.toast("💬 Question envoyée à l'IA…", icon="🤖")
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Affichage du chat
chat_html = '<div class="chat-container">'
if not st.session_state.messages:
    chat_html += '<p style="color:#94a3b8;text-align:center;margin-top:80px;">👋 Posez une question ou choisissez une suggestion ci-dessus</p>'
else:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            chat_html += f'<div class="msg-label" style="text-align:right;margin-right:8px">Vous</div><div class="msg-user">{msg["content"]}</div>'
        else:
            chat_html += f'<div class="msg-label" style="margin-left:8px">🤖 Groq LLaMA 3.3</div><div class="msg-ai">{msg["content"]}</div>'
chat_html += '</div>'
st.markdown(chat_html, unsafe_allow_html=True)

# Input
col_input, col_btn, col_clear, col_export = st.columns([5, 1, 1, 1])
with col_input:
    user_input = st.text_input("Votre question…", label_visibility="collapsed",
                               key="chat_input",
                               placeholder="Ex: Quel est l'impact du budget sur la réussite ?")
with col_btn:
    send = st.button("Envoyer", use_container_width=True, type="primary")
with col_clear:
    if st.button("🗑️ Effacer", use_container_width=True):
        st.session_state.messages = []
        st.toast("Conversation réinitialisée", icon="🗑️")
        st.rerun()
with col_export:
    if st.session_state.messages:
        conv_txt = "\n\n".join([
            f"{'Vous' if m['role']=='user' else 'IA'} : {m['content']}"
            for m in st.session_state.messages
        ])
        st.download_button("💾", conv_txt, file_name="conversation_ia.txt",
                           mime="text/plain", use_container_width=True,
                           help="Exporter la conversation")

# Appel IA
if (send and user_input.strip()) or (st.session_state.messages and st.session_state.messages[-1]["role"] == "user"):
    last = st.session_state.messages[-1] if st.session_state.messages else None

    if last and last["role"] == "user":
        with st.spinner("Groq analyse les données…"):
            answer = call_groq(st.session_state.messages, build_data_context(dff))
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.toast("✅ Réponse reçue !", icon="🤖")
            st.rerun()
    elif send and user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})
        st.rerun()

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center; color:#94a3b8; font-size:0.78rem; padding:20px 0 10px 0;">
    🎓 Tableau de Bord Éducation · {len(df)} établissements · Propulsé par Groq AI (LLaMA 3.3 70B)
</div>
""", unsafe_allow_html=True)