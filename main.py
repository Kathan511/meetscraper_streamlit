import streamlit as st
import re
import plotly.express as px
from datetime import datetime
import datetime as dt
import pytz
import pandas as pd
import seaborn as sns




def epoch_to_ist_date(epoch_time):
    # Define IST timezone
    ist = pytz.timezone('Asia/Kolkata')
    
    # Convert epoch to datetime in UTC
    utc_time = datetime.utcfromtimestamp(epoch_time)
    
    # Convert UTC time to IST
    ist_time = utc_time.astimezone(ist)
    
    # Format the IST time to 'YYYY-MM-DD'
    formatted_date = ist_time.strftime('%Y-%m-%d')
    
    return formatted_date


def replace_ai_number(input_string):
    # Define the regular expression pattern to find "AI-" followed by digits
    pattern = r'\bAI[- ]\d+'
    
    # Define the replacement string
    replacement = 'AI'
    
    # Use re.sub() to replace occurrences of the pattern with the replacement string
    result = re.sub(pattern, replacement, input_string)
    
    return result

st.set_page_config(layout='wide')
# CSS to change the color of selected items in the multiselect dropdown
st.markdown("""
    <style>
.stMultiSelect [data-baseweb="tag"] {
    background-color: #6C757D;  /* Cool Gray */
    color: white;               /* White Text */
    border-radius: 5px;         /* Slightly rounded */
    padding: 5px;               /* Padding for minimal look */
    font-weight: normal;        /* Regular font weight */
}            
    </style>
    """, unsafe_allow_html=True)

st.title("Event Activity Radar")
st.text("Uncover the Hottest Trends, Top Keywords, and Leading Organizers for elevating IQM’s future Meet-ups!")

conn=st.connection("postgresql", type="sql")
df = conn.query('SELECT * FROM public.event_records;', ttl="10m")
df['topic']=df['topic'].apply(lambda x:replace_ai_number(x))

#change date
df['event_time']=df['event_time_epoch'].apply(lambda x:epoch_to_ist_date(x))

##
df['event_time']=pd.to_datetime(df['event_time'])

# Streamlit date input setup
min_date=df['event_time'].min()
max_date=df['event_time'].max()


# User date range input for vacation next year
today = dt.date.today()
default_start_date = today - dt.timedelta(days=90)

date_range = st.date_input(
    "Date Range",
    (default_start_date, today),
    min_date,
    max_date,
    format="DD.MM.YYYY",
)

#get unique cities
all_cities=df['city'].unique().tolist()

# Get the City
selected_cities=st.multiselect("Cities:",all_cities,all_cities)

if st.button("Submit"):
    
    start_date, end_date = date_range
    iqm_group_rank=conn.query(f"""select city, group_name,sum(rsvps) as total_rsvps,avg(rsvps) as avg_rsvps from event_records er 
                            where group_name='iqm-meetup-ahmedabad' 
                            and  event_time_epoch between EXTRACT(EPOCH FROM TO_TIMESTAMP('{start_date}', 'YYYY-MM-DD'))  and EXTRACT(EPOCH FROM TO_TIMESTAMP('{end_date}', 'YYYY-MM-DD'))
                            group by city,group_name;""", ttl="10m")

    # Filter dataframe based on the selected date range
    filtered_df = df[(df['event_time'] >= pd.to_datetime(start_date)) & (df['event_time'] <= pd.to_datetime(end_date)) 
                     & (df['city'].isin(selected_cities))]
    
    #get the city color pallete
    palette = sns.color_palette("pastel", len(selected_cities)).as_hex()
    city_color_map = dict(zip(selected_cities, palette))

    #Group info dataframe
    group_sorted_df = filtered_df.groupby(['city','group_name']).agg(total_rsvps=('rsvps','sum'),avg_rsvps=('rsvps','mean')).reset_index()

    group_sorted_df = group_sorted_df.sort_values('total_rsvps', ascending=False).head(20)

    #Top Event
    event_sorted_df = filtered_df.groupby(['city','event_name','group_name']).agg(registrations=('rsvps','max')) \
    .reset_index().sort_values('registrations',ascending=False)
    #renaming columns
    event_sorted_df.rename(columns={'city':'City','event_name':"Event Name",'group_name':"Organizer Name",
                                    'registrations':"Total Registrations"},inplace=True)
    #re arranging columns
    event_sorted_df=event_sorted_df[['Organizer Name','Event Name','Total Registrations','City']]



    #city dataframe
    city_sorted_df=filtered_df.groupby('city').agg(Events=('event_id','count')).reset_index().sort_values('Events',ascending=False)

    average_registrations_event = filtered_df.groupby(['city','group_name', 'event_name']).agg({'rsvps': 'sum'}).reset_index().sort_values('rsvps',ascending=False).head(100)

    pie_data=filtered_df.groupby(['topic']).agg(AVG_RSVPS=('rsvps','mean'),TOTAL_RSVPS=('rsvps','sum')).reset_index().sort_values('TOTAL_RSVPS',ascending=False).head(10)
    #renaming column
    pie_data.rename(columns={'AVG_RSVPS':"Average Registrations",'TOTAL_RSVPS':"Total Registrations"},inplace=True)
    #Seperator
    st.markdown('---')

    #KPIs
    #Online and Offline events
    col1,col2,col3=st.columns([0.2, 0.6, 0.2],gap='small')
    online_events=len(df[df['event_type'] == 'ONLINE'])
    offline_events=len(df[df['event_type'] == 'PHYSICAL'])
    col1.markdown('Total Events')
    
    col1.dataframe({'Online':[online_events],"Offline":[offline_events]},use_container_width=True)


    #top city events
    col3.markdown("City With Highest Events")
    col3.dataframe(city_sorted_df.head(1),hide_index=True,use_container_width=True)

    #top group info
    col2.markdown("Top Event")
    col2.dataframe(event_sorted_df.head(1),hide_index=True,use_container_width=True)


    #Seperator
    st.markdown('---')

    fig = px.pie(pie_data, values='Average Registrations', names='topic', title="Trending Topics",hover_data=['Total Registrations'])
    st.plotly_chart(fig, use_container_width=True)

    #top registrations across events
    rsvp_sorted_df = filtered_df.sort_values('rsvps', ascending=False).head(20)

    # Create the bar plot for rsvps
    rsvp_event_fig = px.bar(
        rsvp_sorted_df,
        x='event_name',
        y='rsvps',
        color='city',
        hover_name='group_name',
        title="Top 20 Events by Registrations",
        color_discrete_map=city_color_map,
        labels={"event_name": "Event Name", "rsvps": "RSVP"},
        category_orders={"event_name": rsvp_sorted_df['event_name']}  
    )
    st.plotly_chart(rsvp_event_fig,use_container_width=True)

    #top communities that organize events

    group_fig=px.bar(group_sorted_df,x='group_name',
                        color='city',color_discrete_map=city_color_map,category_orders={"group_name": group_sorted_df['group_name']},
                          y='total_rsvps',title="Top 20 Organizers by Registrations",labels={"group_name":"Group Name","total_rsvps":" Total RSVP"})

    st.plotly_chart(group_fig,use_container_width=True)

    # Create a treemap chart
    tree_fig = px.treemap(
        average_registrations_event.head(50),
        path=['group_name','event_name'],  # Path specifies the hierarchy; in this case, we only have one level
        values='rsvps',        # Values represent the average registrations
        title='Event Registration Split Per Organizer',
        color_discrete_map=city_color_map,
        color='city')
    
    


    # Show the IQM rank
    st.plotly_chart(tree_fig,use_container_width=True)

    #grouped info
    # grouped_df_total_rsvp=filtered_df.groupby(['city','group_name']).agg(total_rsvps=('rsvps','sum'),avg_rsvps=('rsvps','mean')).sort_values('total_rsvps',ascending=False).reset_index()
    grouped_df_avg_rsvp=filtered_df.groupby(['city','group_name']).agg(total_rsvps=('rsvps','sum'),avg_rsvps=('rsvps','mean'),total_events=('event_id','count')).sort_values('avg_rsvps',ascending=False).reset_index()

    if len(grouped_df_avg_rsvp[grouped_df_avg_rsvp['group_name']=='iqm-meetup-ahmedabad'])==0:
        # grouped_df_total_rsvp=pd.concat([grouped_df_total_rsvp,iqm_group_rank]).sort_values('total_rsvps',ascending=False).reset_index(drop=True)
        grouped_df_avg_rsvp=pd.concat([grouped_df_avg_rsvp,iqm_group_rank]).sort_values('avg_rsvps',ascending=False).reset_index(drop=True)

    
    else:
        # grouped_df_total_rsvp=grouped_df_total_rsvp.sort_values('total_rsvps',ascending=False)
        grouped_df_avg_rsvp=grouped_df_avg_rsvp.sort_values('avg_rsvps',ascending=False)


    #set the index
    # grouped_df_total_rsvp.index=pd.RangeIndex(start=1, stop=len(grouped_df_total_rsvp) + 1)
    grouped_df_avg_rsvp.index=pd.RangeIndex(start=1, stop=len(grouped_df_avg_rsvp) + 1)

    
    #Seperator
    st.markdown('---')


    #get the index of iqm-meetup-group
    # row_number_total_rsvps = grouped_df_total_rsvp[grouped_df_total_rsvp['group_name'] == 'iqm-meetup-ahmedabad'].index[0]
    row_number_avg_rsvps = grouped_df_avg_rsvp[grouped_df_avg_rsvp['group_name'] == 'iqm-meetup-ahmedabad'].index[0]

    #renaming the columns
    # grouped_df_total_rsvp=grouped_df_total_rsvp.rename(columns={'city':"City",'group_name':"Group Name",'total_rsvps':"Total Registrations",'avg_rsvps':"Average Registrations"})
    grouped_df_avg_rsvp=grouped_df_avg_rsvp.rename(columns={'city':"City",'group_name':"Group Name",'total_rsvps':"Total Registrations",'avg_rsvps':"Average Registrations",'total_events':"Total Events"})

    # CSS and HTML for displaying current rank
    rank_html_code="""
    <style>
    .rank-container {{
        display: flex;              /* Inline layout */
        justify-content: center;    /* Center align the content */
        align-items: center;        /* Vertically center items */
        margin-top: 20px;           /* Add some margin from the top */
    }}
    .rank-label {{
        font-size: 1.2em;           /* Medium font size for rank label */
        color: white;             /* Lighter gray for rank label */
        margin-right: 10px;         /* Space between label and rank */
    }}
    .rank-number {{
        font-size: 2em;             /* Larger font for rank number */
        color: #ff4757;             /* Vibrant red color for rank number */
        font-weight: bold;          /* Bold text */
        margin-right: 20px;         /* Space between rank number and event name */
    }}
    </style>

    <div class="rank-container">
        <span class="rank-label">IQM Meetup Group's Current Rank By {} Registrations.</span>
        <span class="rank-number">#{}</span>
    </div>
    """
    # rank_col1,rank_col2=st.columns(2)
    # rank_col1.markdown(rank_html_code.format("Total",row_number_total_rsvps), unsafe_allow_html=True)
    # rank_col1.dataframe(grouped_df_total_rsvp,use_container_width=True)

    st.markdown(rank_html_code.format("Average",row_number_avg_rsvps), unsafe_allow_html=True)
    st.dataframe(grouped_df_avg_rsvp,use_container_width=True)
