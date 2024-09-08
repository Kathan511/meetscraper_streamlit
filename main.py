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
default_start_date = today - dt.timedelta(days=30)

d = st.date_input(
    "Select Date Range for Events",
    (default_start_date, today),
    min_date,
    max_date,
    format="MM.DD.YYYY",
)

if st.button("submit"):
    start_date, end_date = d

    # Filter dataframe based on the selected date range
    filtered_df = df[(df['event_time'] >= pd.to_datetime(start_date)) & (df['event_time'] <= pd.to_datetime(end_date))]
    pie_data=filtered_df.groupby(['topic'])['rsvps'].sum().reset_index().sort_values('rsvps',ascending=False).head(10)
    st.dataframe(filtered_df)

    #KPIs
    col1,col2,col3,col4=st.columns(4)

    col1.metric("Total Number of Online Events",len(filtered_df[filtered_df['event_type']=='ONLINE']))
    col2.metric("Total Number of Offline Events",len(filtered_df[filtered_df['event_type']=='PHYSICAL']))
    col3.metric("Top Topics by RSVP Count",filtered_df['topic'].value_counts().head(1).index[0])
    col4.metric("Top Group by Event Organization",filtered_df['group_name'].value_counts().head(1).index[0])



    fig = px.pie(pie_data, values='rsvps', names='topic', title="Top 10 Events per Topic (AI-Generated)")
    st.plotly_chart(fig, use_container_width=True)


    #top registrations across events
    rsvp_event_fig=px.bar(filtered_df.sort_values('rsvps',ascending=False).head(20),x='event_name'
                          ,y='rsvps',hover_name='group_name',title="Top Events by Registrations")
    st.plotly_chart(rsvp_event_fig,use_container_width=True)

    #top communities that organize events
    group_fig=px.bar(df['group_name'].value_counts().reset_index().head(10),x='group_name'
                          ,y='count',title="Top Event-Organizing Groups")
    st.plotly_chart(group_fig,use_container_width=True)




