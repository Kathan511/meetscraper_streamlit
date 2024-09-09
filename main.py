import streamlit as st
import re
import plotly.express as px
from datetime import datetime
import datetime as dt
import pytz
import pandas as pd



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
st.title("EventMatrix")
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

d = st.date_input(
    "Select Date Range for Events",
    (default_start_date, today),
    min_date,
    max_date,
    format="DD.MM.YYYY",
)

if st.button("submit"):
    
    start_date, end_date = d

    # Filter dataframe based on the selected date range
    filtered_df = df[(df['event_time'] >= pd.to_datetime(start_date)) & (df['event_time'] <= pd.to_datetime(end_date))]

    average_registrations_event = filtered_df.groupby(['group_name', 'event_name']).agg({'rsvps': 'sum'}).reset_index()

    pie_data=filtered_df.groupby(['topic'])['rsvps'].sum().reset_index().sort_values('rsvps',ascending=False).head(10)

    #Seperator
    st.markdown('---')

    #KPIs
    col1,col2=st.columns(2)
    col1.metric("*Total Number of Online Events*", len(filtered_df[filtered_df['event_type'] == 'ONLINE']))
    col2.metric("*Total Number of Offline Events*", len(filtered_df[filtered_df['event_type'] == 'PHYSICAL']))
    
    #Cols for Top topic/group
    top_col1,top_col2=st.columns(2)

    # col2.metric("Total Number of Offline Events",)
    top_col1.metric("*topic with highest registrations*",pie_data['topic'].iloc[0])
    top_col2.metric("*Event Group with highest registrations*",filtered_df.groupby('group_name')['rsvps'].sum().reset_index().sort_values('rsvps',ascending=False).iloc[0]['group_name'])

    #Seperator
    st.markdown('---')

    fig = px.pie(pie_data, values='rsvps', names='topic', title="Top 10 Events per Topic (AI-Generated-Experimental)")
    st.plotly_chart(fig, use_container_width=True)


    #top registrations across events
    rsvp_event_fig=px.bar(filtered_df.sort_values('rsvps',ascending=False).head(20),x='event_name'
                          ,y='rsvps',hover_name='group_name',title="Top 20 Events by Registrations",labels={"event_name":"Event Name",
                                                                                                         "rsvps":"RSVP"})
    st.plotly_chart(rsvp_event_fig,use_container_width=True)

    #top communities that organize events
    group_fig=px.bar(filtered_df.groupby('group_name')['rsvps'].sum().reset_index().sort_values('rsvps',ascending=False).head(20),x='group_name'
                          ,y='rsvps',title="Top 20 Event Organizing Groups by Registrations",labels={"group_name":"Group Name","rsvps":"RSVP"})
    group_fig.update_traces(marker_color='orange')

    st.plotly_chart(group_fig,use_container_width=True)

    # Create a treemap chart
    tree_fig = px.treemap(
        average_registrations_event,
        path=['group_name','event_name'],  # Path specifies the hierarchy; in this case, we only have one level
        values='rsvps',        # Values represent the average registrations
        title='Registrations per Event Group'
    )

    # Show the figure
    st.plotly_chart(tree_fig,use_container_width=True)

    #Seperator
    st.markdown('---')

    st.dataframe(filtered_df)




