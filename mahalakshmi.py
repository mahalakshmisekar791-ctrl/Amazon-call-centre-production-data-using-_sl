import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Contact Center Dashboard",
    page_icon="📞",
    layout="wide"
)

# --- 2. DATA LOADING & CLEANING (Only run once) ---
@st.cache_data
def load_data():
    """Loads, cleans, and prepares the contact center data."""
    try:
        # NOTE: Using a raw string (r"...") for the path
        # ⚠️ This path is absolute and only works on your local machine. 
        # For deployment, replace this with a relative path or a cloud/remote data source.
        df = pd.read_excel(r"C:\\Users\DELL\\OneDrive\\Desktop\\python maha\\st_lt 2\\Data Research.xlsx")
    except FileNotFoundError:
        st.error("Error: Data file not found. Please check the file path.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred during data loading: {e}")
        return pd.DataFrame()

    if not df.empty:
        # Clean up column names
        # Assuming you intended to remove non-alphanumeric characters except underscore
        df.columns = df.columns.astype(str).str.replace('[^A-Za-z0-9_]+', '', regex=True)
        
        # Rename key columns (make sure these original names exist in your Excel file)
        df = df.rename(columns={
            'contact_date': 'Date', # Check your raw column name
            'asic1': 'Category',    # Check your raw column name
            'site1': 'Region',      # Check your raw column name
            'media_leg_result': 'Result' # Check your raw column name
        })
        
        # Convert Date column
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # Handle missing values
        df['Category'] = df['Category'].fillna('Unknown')
        df['Region'] = df['Region'].fillna('Unknown')
        df['Result'] = df['Result'].fillna('Unknown')
        
        # Calculate Total Contacts per row
        df['ContactCount'] = 1 
        
    return df

# Load the data globally
df = load_data()

# Check if data loaded successfully
if df.empty:
    st.stop()


# --- 3. PAGE FUNCTIONS ---

def sidebar_filters(df_input):
    """Creates sidebar filters and returns the filtered DataFrame."""
    st.sidebar.header("Dashboard Filters")
    
    df_filtered = df_input.copy() 
    
    # Date Range Filter setup
    # Ensure min/max dates are not NaT if df['Date'] has missing values
    valid_dates = df_input['Date'].dropna()
    min_date_val = valid_dates.min().date() if not valid_dates.empty else pd.Timestamp.now().date()
    max_date_val = valid_dates.max().date() if not valid_dates.empty else pd.Timestamp.now().date()

    # Handle case where min_date > max_date (e.g., if only one date is present)
    if min_date_val > max_date_val:
         min_date_val, max_date_val = max_date_val, min_date_val

    # Date Range Filter widget
    date_range = st.sidebar.date_input(
        "Date Range",
        (min_date_val, max_date_val),
        min_value=min_date_val,
        max_value=max_date_val
    )
    
    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        # Include the entire end day
        end_date = end_date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) 
        df_filtered = df_filtered[(df_filtered['Date'] >= start_date) & (df_filtered['Date'] <= end_date)]

    # Category Filter
    all_categories = df_filtered['Category'].unique().tolist()
    category_selection = st.sidebar.multiselect(
        "Category (asic1)",
        options=all_categories,
        default=all_categories
    )
    
    # Region Filter
    all_regions = df_filtered['Region'].unique().tolist()
    region_selection = st.sidebar.multiselect(
        "Region (site1)",
        options=all_regions,
        default=all_regions
    )
    
    # Apply remaining filters
    df_filtered = df_filtered[
        (df_filtered['Category'].isin(category_selection)) &
        (df_filtered['Region'].isin(region_selection))
    ]
    
    return df_filtered


def overview_kpis(df_filtered):
    """Defines the content for the Overview & KPIs page (Page 1)."""
    st.title("📞 Amazon production Contact Center Analytics Dashboard")
    st.markdown("Created by: **Mahalakshmi S**")
    st.markdown("A data analysis dashboard based on the Contact Center Analytics data.")

    if df_filtered.empty:
        st.warning("No data matches the selected filters. Please adjust your selections.")
        return

    # --- KPIs with st.metric() ---
    st.header("Key Performance Indicators 📊")
    
    # KPI Calculation
    total_contacts = df_filtered.shape[0] 
    total_handled = df_filtered[df_filtered['Result'] == 'Handled']['ContactCount'].sum()
    handling_rate = (total_handled / total_contacts * 100) if total_contacts > 0 else 0
    
    prev_handling_rate = 85.4 # Placeholder for delta calculation
    handling_delta = handling_rate - prev_handling_rate

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Total Contacts", value=f"{total_contacts:,.0f}")
    with col2:
        st.metric(label="Total Handled", value=f"{total_handled:,.0f}")
    with col3:
        st.metric(
            label="Handling Rate", 
            value=f"{handling_rate:.1f}%", 
            delta=f"{handling_delta:.1f}% vs Prior Period",
            delta_color=("inverse" if handling_delta < 0 else "normal")
        )
    
    st.markdown("---") 

    # Trend 1: Daily Contact Volume (Line Chart)
    st.subheader("Daily Contact Volume Trend")
    daily_volume = df_filtered.groupby(df_filtered['Date'].dt.date)['ContactCount'].sum().reset_index()
    daily_volume.columns = ['Date', 'ContactCount']
    fig_line = px.line(
        daily_volume, 
        x='Date', 
        y='ContactCount', 
        title='Total Contacts by Day',
        markers=True
    ).update_layout(yaxis_title="Contacts (Volume)", xaxis_title="Date")
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---") 
    
    # Daily Result Breakdown (Stacked Bar Chart)
    st.subheader("Daily Handling Success Breakdown (Filtered)")
    daily_results = df_filtered.groupby([df_filtered['Date'].dt.date, 'Result'])['ContactCount'].sum().reset_index()
    daily_results.columns = ['Date', 'Result', 'ContactCount']

    fig_stacked = px.bar(
        daily_results,
        x='Date',
        y='ContactCount',
        color='Result',
        title='Daily Volume by Result Type (Handled vs. Other)',
        color_discrete_map={'Handled': 'green', 'Transfer': 'red', 'Unknown': 'gray', 'OtherResult': 'blue'} 
    )
    fig_stacked.update_layout(xaxis_title="Date", yaxis_title="Contacts (Volume)", barmode='stack')
    st.plotly_chart(fig_stacked, use_container_width=True)


def detailed_analysis(df_filtered):
    """Defines the content for the Detailed Analysis page (Page 2)."""
    st.title("🔬 Detailed Analysis")
    st.markdown("Deep dive into contact category and regional performance.")

    if df_filtered.empty:
        st.warning("No data matches the selected filters. Please adjust your selections.")
        return

    col4, col5 = st.columns(2)

    # Trend 2: Contacts by Category (Bar Chart)
    with col4:
        st.subheader("Contacts by Primary Category")
        category_counts = df_filtered.groupby('Category')['ContactCount'].sum().reset_index()
        fig_bar = px.bar(
            category_counts.sort_values(by='ContactCount', ascending=False), 
            x='Category', 
            y='ContactCount', 
            title='Volume by Category',
            color='Category' 
        ).update_layout(xaxis_title="", yaxis_title="Contacts", showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    # Trend 3: Contacts by Region (Pie Chart)
    with col5:
        st.subheader("Contact Distribution by Region")
        region_counts = df_filtered.groupby('Region')['ContactCount'].sum().reset_index()
        fig_pie = px.pie(
            region_counts, 
            values='ContactCount', 
            names='Region', 
            title='Distribution by Region',
            hole=0.3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
# --- 4. MAIN APP LOGIC (Page Selector) ---
def main():
    """The main function to handle page routing via the sidebar."""
    
    # Apply all sidebar filters and get the filtered data
    df_filtered = sidebar_filters(df)

    st.sidebar.markdown("---")
    st.sidebar.title("Navigation")
    
    # Define page names as variables for consistency and to avoid typos
    PAGE_OVERVIEW = "1. Contact Center Analytics Dashboard"
    PAGE_DETAILED = "2. Detailed Analysis"
    
    # Widget: Radio button for page selection
    page = st.sidebar.radio("Go to Page", [PAGE_OVERVIEW, PAGE_DETAILED])

    # Route to the selected page, passing the filtered data
    # NOTE: The typo was fixed here: "1.Contact" -> "1. Contact"
    if page == PAGE_OVERVIEW:
        overview_kpis(df_filtered)
    elif page == PAGE_DETAILED:
        detailed_analysis(df_filtered)

# --- APPLICATION ENTRY POINT ---
if __name__ == "__main__":
    main()

