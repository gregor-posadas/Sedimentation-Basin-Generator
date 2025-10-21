import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import plotly.graph_objects as go

st.set_page_config(
    page_title="Sedimentation Basin Designer",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏗️ Sedimentation Basin Design Tool")

st.markdown("""
Use this tool to design a rectangular sedimentation basin based on settling column test results.
Enter your design parameters from the isoremoval curves analysis to calculate tank dimensions and verify design criteria.
""")

with st.expander("📚 How to Use This Tool", expanded=False):
    st.markdown("""
    ### Step 1: Get Design Parameters from Settling Column Analysis
    Run your settling column data through the Isoremoval Curves Generator to get:
    - **Detention Time** (hours) - from the "Detention Time vs. Removal" plot
    - **Overflow Rate** (m/d) - from the "Overflow Rate vs. Removal" plot
    - Select values that give you your desired removal percentage
    
    ### Step 2: Enter Flow Rate
    - Determine the flow rate your treatment plant needs to handle
    - This could be based on population, industrial needs, or design requirements
    
    ### Step 3: Choose Basin Configuration
    - Decide if you want one large basin or multiple smaller ones
    - Multiple basins provide redundancy and flexibility
    
    ### Step 4: Adjust Dimensions
    - The tool will calculate initial dimensions
    - Adjust length, width, and depth to meet practical constraints
    - Check that all design criteria are satisfied
    
    ### Step 5: Review Design
    - Verify all design checks pass (green checkmarks)
    - Review the 3D visualization
    - Export results for your design report
    """)

st.markdown("---")

# ==================== SIDEBAR INPUTS ====================
st.sidebar.header("Design Parameters")

st.sidebar.subheader("1. From Settling Column Test")

detention_time = st.sidebar.number_input(
    "Detention Time (hours)",
    min_value=0.1,
    max_value=24.0,
    value=2.0,
    step=0.1,
    help="From your 'Detention Time vs. Removal' plot"
)

overflow_rate = st.sidebar.number_input(
    "Overflow Rate (m/d)",
    min_value=1.0,
    max_value=10000.0,
    value=1200.0,
    step=10.0,
    help="From your 'Overflow Rate vs. Removal' plot"
)

target_removal = st.sidebar.number_input(
    "Target Removal (%)",
    min_value=0.0,
    max_value=100.0,
    value=75.0,
    step=1.0,
    help="The removal % these parameters achieve"
)

st.sidebar.markdown("---")
st.sidebar.subheader("2. Design Flow Rate")

flow_units = st.sidebar.selectbox(
    "Flow Units",
    ["m³/day", "m³/hour", "MGD (Million Gallons/Day)", "L/s"],
    index=0
)

flow_input = st.sidebar.number_input(
    f"Design Flow ({flow_units})",
    min_value=1.0,
    value=10000.0,
    step=100.0
)

# Convert to m³/day
if flow_units == "m³/day":
    flow_m3_day = flow_input
elif flow_units == "m³/hour":
    flow_m3_day = flow_input * 24
elif flow_units == "MGD (Million Gallons/Day)":
    flow_m3_day = flow_input * 3785.41  # 1 MG = 3785.41 m³
elif flow_units == "L/s":
    flow_m3_day = flow_input * 0.001 * 86400  # L/s to m³/day

st.sidebar.markdown("---")
st.sidebar.subheader("3. Basin Configuration")

num_basins = st.sidebar.number_input(
    "Number of Parallel Basins",
    min_value=1,
    max_value=10,
    value=2,
    step=1,
    help="Multiple basins allow for redundancy and maintenance"
)

# ==================== CALCULATIONS ====================

# Flow per basin
flow_per_basin = flow_m3_day / num_basins

# Calculate required volume (per basin)
volume_required = flow_per_basin * (detention_time / 24)  # m³

# Calculate required surface area (per basin)
surface_area_required = flow_per_basin / overflow_rate  # m²

# Initial dimension estimates
st.sidebar.markdown("---")
st.sidebar.subheader("4. Basin Dimensions")

st.sidebar.caption("Adjust dimensions to meet practical constraints")

# Typical depth range
depth = st.sidebar.slider(
    "Depth (m)",
    min_value=2.0,
    max_value=6.0,
    value=3.5,
    step=0.1,
    help="Typical range: 3-5 meters"
)

# Calculate required surface area for this depth
surface_area_for_volume = volume_required / depth

# Use the larger of the two area requirements
surface_area_actual = max(surface_area_required, surface_area_for_volume)

# Length to width ratio
l_w_ratio = st.sidebar.slider(
    "Length:Width Ratio",
    min_value=2.0,
    max_value=6.0,
    value=4.0,
    step=0.5,
    help="Typical range: 3:1 to 5:1"
)

# Calculate length and width
width = np.sqrt(surface_area_actual / l_w_ratio)
length = width * l_w_ratio

# Actual volume
volume_actual = surface_area_actual * depth

# Actual detention time
detention_time_actual = (volume_actual / flow_per_basin) * 24  # hours

# Actual overflow rate
overflow_rate_actual = flow_per_basin / surface_area_actual  # m/d

# ==================== DESIGN CHECKS ====================

st.header("Design Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Flow per Basin", f"{flow_per_basin:,.0f} m³/d")
    st.metric("Number of Basins", num_basins)
    st.metric("Total Plant Flow", f"{flow_m3_day:,.0f} m³/d")

with col2:
    st.metric("Basin Volume", f"{volume_actual:,.0f} m³")
    st.metric("Surface Area", f"{surface_area_actual:,.1f} m²")
    st.metric("Detention Time", f"{detention_time_actual:.2f} hours")

with col3:
    st.metric("Length", f"{length:.2f} m")
    st.metric("Width", f"{width:.2f} m")
    st.metric("Depth", f"{depth:.2f} m")

st.markdown("---")

# ==================== DETAILED CALCULATIONS ====================

st.header("Detailed Design Calculations")

# Horizontal velocity
horizontal_velocity = (flow_per_basin / 86400) / (width * depth)  # m/s

# Weir length (assume weirs on both ends)
weir_length = 2 * width  # m
weir_loading = (flow_per_basin / 86400) / weir_length  # m³/s/m
weir_loading_m3_d_m = flow_per_basin / weir_length  # m³/d/m

# Reynolds number (for laminar flow check)
# Assume kinematic viscosity = 1.0 x 10^-6 m²/s (20°C water)
kinematic_viscosity = 1.0e-6
reynolds_number = (horizontal_velocity * depth) / kinematic_viscosity

# Surface loading rate check
surface_loading = overflow_rate_actual

col1, col2 = st.columns(2)

with col1:
    st.subheader("Hydraulic Parameters")
    
    st.markdown(f"""
    **Horizontal Velocity:** {horizontal_velocity*100:.2f} cm/s  
    *Typical range: 0.15-0.45 cm/s*
    
    **Surface Loading Rate:** {surface_loading:.1f} m/d  
    *Your design value: {overflow_rate:.1f} m/d*
    
    **Overflow Rate:** {overflow_rate_actual:.1f} m/d  
    *Should match your settling column result*
    
    **Reynolds Number:** {reynolds_number:,.0f}  
    *< 2000 = Laminar flow (desired)*
    """)

with col2:
    st.subheader("Weir Design")
    
    st.markdown(f"""
    **Weir Length:** {weir_length:.2f} m  
    *Assumes weirs on both ends*
    
    **Weir Loading Rate:** {weir_loading:.4f} m³/s/m  
    *Or {weir_loading_m3_d_m:.1f} m³/d/m*
    
    **Typical range:** 125-500 m³/d/m  
    *(Lower is better for floc stability)*
    """)

st.markdown("---")

# ==================== DESIGN CHECKS ====================

st.header("Design Criteria Check")

checks = []

# Check 1: Detention time
dt_check = abs(detention_time_actual - detention_time) / detention_time < 0.1
checks.append({
    "Criterion": "Detention Time Match",
    "Target": f"{detention_time:.2f} hours",
    "Actual": f"{detention_time_actual:.2f} hours",
    "Status": "✅ Pass" if dt_check else "⚠️ Review",
    "Notes": "Within 10% of target" if dt_check else "Adjust depth or L:W ratio"
})

# Check 2: Overflow rate
or_check = abs(overflow_rate_actual - overflow_rate) / overflow_rate < 0.1
checks.append({
    "Criterion": "Overflow Rate Match",
    "Target": f"{overflow_rate:.1f} m/d",
    "Actual": f"{overflow_rate_actual:.1f} m/d",
    "Status": "✅ Pass" if or_check else "⚠️ Review",
    "Notes": "Within 10% of target" if or_check else "Adjust depth or L:W ratio"
})

# Check 3: Horizontal velocity
hv_check = 0.0015 <= horizontal_velocity <= 0.0045  # 0.15 to 0.45 cm/s in m/s
checks.append({
    "Criterion": "Horizontal Velocity",
    "Target": "0.15-0.45 cm/s",
    "Actual": f"{horizontal_velocity*100:.2f} cm/s",
    "Status": "✅ Pass" if hv_check else "⚠️ Review",
    "Notes": "Good for settling" if hv_check else "May cause scour or short-circuiting"
})

# Check 4: Length to width ratio
lw_check = 3.0 <= l_w_ratio <= 5.0
checks.append({
    "Criterion": "Length:Width Ratio",
    "Target": "3:1 to 5:1",
    "Actual": f"{l_w_ratio:.1f}:1",
    "Status": "✅ Pass" if lw_check else "⚠️ Review",
    "Notes": "Good plug flow" if lw_check else "Adjust for better hydraulics"
})

# Check 5: Depth
depth_check = 3.0 <= depth <= 5.0
checks.append({
    "Criterion": "Basin Depth",
    "Target": "3-5 m",
    "Actual": f"{depth:.1f} m",
    "Status": "✅ Pass" if depth_check else "⚠️ Review",
    "Notes": "Typical range" if depth_check else "Consider structural implications"
})

# Check 6: Weir loading
weir_check = 125 <= weir_loading_m3_d_m <= 500
checks.append({
    "Criterion": "Weir Loading",
    "Target": "125-500 m³/d/m",
    "Actual": f"{weir_loading_m3_d_m:.1f} m³/d/m",
    "Status": "✅ Pass" if weir_check else "⚠️ Review",
    "Notes": "Won't disturb floc" if weir_check else "Consider increasing weir length"
})

# Check 7: Reynolds number
re_check = reynolds_number < 2000
checks.append({
    "Criterion": "Flow Regime",
    "Target": "Re < 2000 (Laminar)",
    "Actual": f"Re = {reynolds_number:,.0f}",
    "Status": "✅ Pass" if re_check else "⚠️ Review",
    "Notes": "Laminar flow" if re_check else "Turbulent - may affect settling"
})

checks_df = pd.DataFrame(checks)
st.dataframe(checks_df, hide_index=True, use_container_width=True)

# Overall status
all_pass = all([c["Status"] == "✅ Pass" for c in checks])
if all_pass:
    st.success("🎉 All design criteria satisfied! Your basin design is ready.")
else:
    st.warning("⚠️ Some criteria need review. Adjust dimensions in the sidebar to optimize design.")

st.markdown("---")

# ==================== VISUALIZATION ====================

st.header("Basin Visualization")

tab1, tab2, tab3 = st.tabs(["3D View", "Plan View", "Profile View"])

with tab1:
    st.subheader("3D Basin Visualization")
    
    # Create 3D plot with plotly
    fig = go.Figure()
    
    # Define vertices for rectangular basin
    x = [0, length, length, 0, 0, length, length, 0]
    y = [0, 0, width, width, 0, 0, width, width]
    z = [0, 0, 0, 0, depth, depth, depth, depth]
    
    # Create edges
    edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom
        [4, 5], [5, 6], [6, 7], [7, 4],  # Top
        [0, 4], [1, 5], [2, 6], [3, 7]   # Vertical
    ]
    
    for edge in edges:
        fig.add_trace(go.Scatter3d(
            x=[x[edge[0]], x[edge[1]]],
            y=[y[edge[0]], y[edge[1]]],
            z=[z[edge[0]], z[edge[1]]],
            mode='lines',
            line=dict(color='blue', width=4),
            showlegend=False
        ))
    
    # Add water level
    fig.add_trace(go.Mesh3d(
        x=[0, length, length, 0],
        y=[0, 0, width, width],
        z=[depth*0.9, depth*0.9, depth*0.9, depth*0.9],
        color='lightblue',
        opacity=0.3,
        name='Water Level'
    ))
    
    # Add dimensions
    fig.add_trace(go.Scatter3d(
        x=[length/2],
        y=[-width*0.2],
        z=[0],
        mode='text',
        text=[f'L = {length:.1f} m'],
        textfont=dict(size=14, color='red'),
        showlegend=False
    ))
    
    fig.add_trace(go.Scatter3d(
        x=[length + length*0.1],
        y=[width/2],
        z=[0],
        mode='text',
        text=[f'W = {width:.1f} m'],
        textfont=dict(size=14, color='red'),
        showlegend=False
    ))
    
    fig.add_trace(go.Scatter3d(
        x=[length + length*0.1],
        y=[0],
        z=[depth/2],
        mode='text',
        text=[f'D = {depth:.1f} m'],
        textfont=dict(size=14, color='red'),
        showlegend=False
    ))
    
    fig.update_layout(
        scene=dict(
            xaxis_title='Length (m)',
            yaxis_title='Width (m)',
            zaxis_title='Depth (m)',
            aspectmode='data'
        ),
        height=600,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Plan View (Top Down)")
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Draw basin
    basin = Rectangle((0, 0), length, width, 
                      fill=True, facecolor='lightblue', 
                      edgecolor='black', linewidth=2)
    ax.add_patch(basin)
    
    # Add inlet zone
    inlet = Rectangle((0, 0), length*0.1, width,
                     fill=True, facecolor='lightgreen',
                     edgecolor='green', linewidth=2, alpha=0.5)
    ax.add_patch(inlet)
    ax.text(length*0.05, width/2, 'INLET\nZONE', 
           ha='center', va='center', fontsize=10, weight='bold')
    
    # Add settling zone
    ax.text(length*0.5, width/2, 'SETTLING ZONE', 
           ha='center', va='center', fontsize=14, weight='bold')
    
    # Add outlet zone
    outlet = Rectangle((length*0.9, 0), length*0.1, width,
                      fill=True, facecolor='lightyellow',
                      edgecolor='orange', linewidth=2, alpha=0.5)
    ax.add_patch(outlet)
    ax.text(length*0.95, width/2, 'OUTLET\nZONE', 
           ha='center', va='center', fontsize=10, weight='bold')
    
    # Flow direction arrows
    arrow_y = width * 0.8
    ax.arrow(length*0.15, arrow_y, length*0.2, 0,
            head_width=width*0.05, head_length=length*0.03,
            fc='blue', ec='blue', linewidth=2)
    ax.text(length*0.25, arrow_y + width*0.1, 'FLOW →',
           fontsize=12, weight='bold', color='blue')
    
    # Dimensions
    ax.plot([0, length], [-width*0.1, -width*0.1], 'k-', linewidth=2)
    ax.plot([0, 0], [-width*0.15, -width*0.05], 'k-', linewidth=2)
    ax.plot([length, length], [-width*0.15, -width*0.05], 'k-', linewidth=2)
    ax.text(length/2, -width*0.2, f'Length = {length:.1f} m',
           ha='center', fontsize=12, weight='bold')
    
    ax.plot([-length*0.1, -length*0.1], [0, width], 'k-', linewidth=2)
    ax.plot([-length*0.15, -length*0.05], [0, 0], 'k-', linewidth=2)
    ax.plot([-length*0.15, -length*0.05], [width, width], 'k-', linewidth=2)
    ax.text(-length*0.2, width/2, f'Width = {width:.1f} m',
           ha='center', va='center', rotation=90, fontsize=12, weight='bold')
    
    ax.set_xlim(-length*0.3, length*1.1)
    ax.set_ylim(-width*0.3, width*1.1)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Plan View - Sedimentation Basin', fontsize=16, weight='bold', pad=20)
    
    st.pyplot(fig)

with tab3:
    st.subheader("Profile View (Side View)")
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Draw basin profile
    basin_profile = Rectangle((0, 0), length, depth,
                             fill=True, facecolor='lightgray',
                             edgecolor='black', linewidth=2)
    ax.add_patch(basin_profile)
    
    # Draw water
    water = Rectangle((0, 0), length, depth*0.95,
                     fill=True, facecolor='lightblue',
                     edgecolor='blue', linewidth=1, alpha=0.6)
    ax.add_patch(water)
    
    # Draw sludge zone
    sludge = Rectangle((0, 0), length, depth*0.15,
                       fill=True, facecolor='saddlebrown',
                       edgecolor='brown', linewidth=1, alpha=0.5)
    ax.add_patch(sludge)
    ax.text(length/2, depth*0.08, 'SLUDGE ZONE',
           ha='center', va='center', fontsize=10, weight='bold', color='white')
    
    # Inlet structure
    ax.plot([length*0.05, length*0.05], [depth*0.3, depth*0.95], 'g-', linewidth=4)
    ax.text(length*0.05, depth, 'INLET',
           ha='center', va='bottom', fontsize=10, weight='bold', color='green')
    
    # Outlet weir
    ax.plot([length*0.95, length*0.95], [depth*0.5, depth*0.95], 'orange', linewidth=4)
    ax.text(length*0.95, depth, 'WEIR',
           ha='center', va='bottom', fontsize=10, weight='bold', color='orange')
    
    # Particle settling paths
    for i in range(5):
        x_start = length * 0.1
        y_start = depth * (0.4 + i * 0.1)
        x_end = length * (0.4 + i * 0.1)
        y_end = depth * 0.15
        ax.plot([x_start, x_end], [y_start, y_end], 'r--', alpha=0.5, linewidth=1.5)
    
    ax.text(length*0.3, depth*0.6, 'Particle\nSettling Paths',
           ha='center', fontsize=10, style='italic', color='red')
    
    # Dimensions
    ax.plot([0, length], [-depth*0.15, -depth*0.15], 'k-', linewidth=2)
    ax.plot([0, 0], [-depth*0.2, -depth*0.1], 'k-', linewidth=2)
    ax.plot([length, length], [-depth*0.2, -depth*0.1], 'k-', linewidth=2)
    ax.text(length/2, -depth*0.25, f'Length = {length:.1f} m',
           ha='center', fontsize=12, weight='bold')
    
    ax.plot([length*1.05, length*1.05], [0, depth], 'k-', linewidth=2)
    ax.plot([length*1.02, length*1.08], [0, 0], 'k-', linewidth=2)
    ax.plot([length*1.02, length*1.08], [depth, depth], 'k-', linewidth=2)
    ax.text(length*1.15, depth/2, f'Depth = {depth:.1f} m',
           ha='center', va='center', rotation=90, fontsize=12, weight='bold')
    
    ax.set_xlim(-length*0.1, length*1.25)
    ax.set_ylim(-depth*0.35, depth*1.15)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Profile View - Sedimentation Basin', fontsize=16, weight='bold', pad=20)
    
    st.pyplot(fig)

st.markdown("---")

# ==================== COST ESTIMATION ====================

st.header("Preliminary Cost Estimation")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Material Quantities")
    
    # Concrete volume (walls and floor)
    wall_thickness = 0.3  # m
    concrete_volume = (
        length * width * 0.3 +  # Floor
        2 * (length * depth * wall_thickness) +  # Long walls
        2 * (width * depth * wall_thickness)     # Short walls
    ) * num_basins
    
    st.markdown(f"""
    **Concrete Required:** {concrete_volume:.1f} m³  
    **Excavation Volume:** {(length * width * (depth + 0.5)) * num_basins:.1f} m³  
    **Basin Footprint:** {(length * width * num_basins):.1f} m²  
    """)

with col2:
    st.subheader("Cost Estimates")
    
    # Rough cost estimates (adjust for your region)
    concrete_cost = concrete_volume * 150  # $/m³
    excavation_cost = (length * width * (depth + 0.5)) * num_basins * 20  # $/m³
    equipment_cost = num_basins * 50000  # $ per basin for inlet/outlet structures
    
    total_cost = concrete_cost + excavation_cost + equipment_cost
    
    st.markdown(f"""
    **Concrete:** ${concrete_cost:,.0f}  
    **Excavation:** ${excavation_cost:,.0f}  
    **Equipment:** ${equipment_cost:,.0f}  
    **Total Estimated Cost:** ${total_cost:,.0f}  
    
    *Note: Rough estimates for preliminary design only*
    """)

st.markdown("---")

# ==================== DESIGN SUMMARY EXPORT ====================

st.header("Design Summary Report")

summary_data = {
    "Parameter": [
        "Design Flow Rate",
        "Number of Basins",
        "Flow per Basin",
        "Target Removal",
        "Detention Time (Design)",
        "Detention Time (Actual)",
        "Overflow Rate (Design)",
        "Overflow Rate (Actual)",
        "Basin Length",
        "Basin Width",
        "Basin Depth",
        "Basin Volume",
        "Surface Area",
        "Length:Width Ratio",
        "Horizontal Velocity",
        "Weir Loading",
        "Reynolds Number",
    ],
    "Value": [
        f"{flow_m3_day:,.0f} m³/d",
        f"{num_basins}",
        f"{flow_per_basin:,.0f} m³/d",
        f"{target_removal:.1f}%",
        f"{detention_time:.2f} hours",
        f"{detention_time_actual:.2f} hours",
        f"{overflow_rate:.1f} m/d",
        f"{overflow_rate_actual:.1f} m/d",
        f"{length:.2f} m",
        f"{width:.2f} m",
        f"{depth:.2f} m",
        f"{volume_actual:,.1f} m³",
        f"{surface_area_actual:,.1f} m²",
        f"{l_w_ratio:.1f}:1",
        f"{horizontal_velocity*100:.2f} cm/s",
        f"{weir_loading_m3_d_m:.1f} m³/d/m",
        f"{reynolds_number:,.0f}",
    ]
}

summary_df = pd.DataFrame(summary_data)
st.dataframe(summary_df, hide_index=True, use_container_width=True)

# Download button
csv = summary_df.to_csv(index=False)
st.download_button(
    label="📥 Download Design Summary (CSV)",
    data=csv,
    file_name="sedimentation_basin_design.csv",
    mime="text/csv"
)

st.success("✅ Design complete! Review all checks and download your summary.")
