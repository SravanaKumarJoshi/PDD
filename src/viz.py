"""
Visualization utilities using Plotly.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Any


def create_comparison_radar_chart(
    top_polymers: pd.DataFrame,
    user_requirements: dict[str, Any],
) -> go.Figure:
    """
    Create a radar chart comparing top polymers with user targets.
    
    Args:
        top_polymers: Top N ranked polymers
        user_requirements: User requirements dictionary
        
    Returns:
        Plotly figure
    """
    features = [
        ("tensile_strength", "Tensile Strength"),
        ("flexibility", "Flexibility"),
        ("wvtr", "WVTR"),
        ("oxygen_permeability", "O₂ Permeability"),
        ("biocompatibility", "Biocompatibility"),
    ]
    
    fig = go.Figure()
    
    # Add user target as a trace
    target_values = []
    feature_names = []
    
    for feature_key, feature_name in features:
        target_val = user_requirements.get(f"target_{feature_key}")
        if target_val is not None:
            target_values.append(target_val)
            feature_names.append(feature_name)
    
    if target_values:
        fig.add_trace(go.Scatterpolar(
            r=target_values,
            theta=feature_names,
            fill='toself',
            name='Your Target',
            line=dict(color='gold', width=2, dash='dash'),
        ))
    
    # Add top polymers (limit to top 3 for clarity)
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    
    for idx, (_, polymer) in enumerate(top_polymers.head(3).iterrows()):
        polymer_values = []
        
        for feature_key, _ in features:
            if feature_key in polymer:
                polymer_values.append(polymer[feature_key])
        
        fig.add_trace(go.Scatterpolar(
            r=polymer_values,
            theta=feature_names,
            fill='toself',
            name=f"{polymer['polymer']} ({polymer['final_score']:.1f}%)",
            line=dict(color=colors[idx % len(colors)], width=2),
            opacity=0.6,
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                showticklabels=True,
            )
        ),
        showlegend=True,
        title="Property Comparison: Top Polymers vs Your Target",
        height=500,
    )
    
    return fig


def create_grouped_bar_chart(
    top_polymers: pd.DataFrame,
    user_requirements: dict[str, Any],
) -> go.Figure:
    """
    Create grouped bar chart comparing polymer properties.
    
    Args:
        top_polymers: Top N ranked polymers
        user_requirements: User requirements dictionary
        
    Returns:
        Plotly figure
    """
    features = [
        ("tensile_strength", "Tensile Strength (MPa)"),
        ("flexibility", "Flexibility"),
        ("wvtr", "WVTR (g/m²/day)"),
        ("oxygen_permeability", "O₂ Permeability"),
        ("biocompatibility", "Biocompatibility (1-10)"),
    ]
    
    fig = go.Figure()
    
    # Add bars for each polymer
    for _, polymer in top_polymers.head(5).iterrows():
        values = [polymer[feat[0]] for feat in features]
        labels = [feat[1] for feat in features]
        
        fig.add_trace(go.Bar(
            name=f"{polymer['polymer']} ({polymer['final_score']:.1f}%)",
            x=labels,
            y=values,
        ))
    
    fig.update_layout(
        barmode='group',
        title="Property Comparison: Top 5 Polymers",
        xaxis_title="Properties",
        yaxis_title="Values",
        height=500,
        showlegend=True,
    )
    
    return fig


def create_score_breakdown_chart(
    top_polymers: pd.DataFrame,
) -> go.Figure:
    """
    Create a horizontal bar chart showing score breakdown.
    
    Args:
        top_polymers: Top N ranked polymers
        
    Returns:
        Plotly figure
    """
    top_5 = top_polymers.head(5).copy()
    
    # Calculate score components
    top_5["similarity_component"] = top_5["similarity_score"] * 0.6
    top_5["ml_component"] = top_5["suitability_probability"] * 100 * 0.4
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Similarity (60%)',
        y=top_5['polymer'],
        x=top_5['similarity_component'],
        orientation='h',
        marker=dict(color='#1f77b4'),
    ))
    
    fig.add_trace(go.Bar(
        name='ML Suitability (40%)',
        y=top_5['polymer'],
        x=top_5['ml_component'],
        orientation='h',
        marker=dict(color='#ff7f0e'),
    ))
    
    fig.update_layout(
        barmode='stack',
        title="Match Score Breakdown (Top 5)",
        xaxis_title="Score Components",
        yaxis_title="Polymer",
        height=400,
        showlegend=True,
        yaxis={'categoryorder': 'total ascending'},
    )
    
    return fig


def create_confusion_matrix_heatmap(
    confusion_mat: list[list[int]],
) -> go.Figure:
    """
    Create a heatmap for confusion matrix.
    
    Args:
        confusion_mat: 2x2 confusion matrix [[TN, FP], [FN, TP]]
        
    Returns:
        Plotly figure
    """
    labels = ['Not Suitable (0)', 'Suitable (1)']
    
    # Create annotations for cell values
    annotations = []
    for i in range(2):
        for j in range(2):
            annotations.append(
                dict(
                    x=j,
                    y=i,
                    text=str(confusion_mat[i][j]),
                    showarrow=False,
                    font=dict(size=20, color='white'),
                )
            )
    
    fig = go.Figure(data=go.Heatmap(
        z=confusion_mat,
        x=['Predicted 0', 'Predicted 1'],
        y=['Actual 0', 'Actual 1'],
        colorscale='Blues',
        showscale=True,
    ))
    
    fig.update_layout(
        title="Confusion Matrix",
        annotations=annotations,
        height=400,
        xaxis_title="Predicted Label",
        yaxis_title="Actual Label",
    )
    
    return fig
