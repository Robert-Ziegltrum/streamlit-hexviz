import streamlit_hexviz as shv
import pandas as pd
import streamlit as st


st.write('## Earthquakes in California')

data = pd.read_csv('data/earthquakes.csv')
data = data[data["place"].str.contains("CA", na=False)]

shv.a5_map(df=data, lat='latitude', lon='longitude', use_sidebar_controls=True)

st.dataframe(data.head(20))

st.code(""" 
import streamlit_hexviz as shv
import pandas as pd
import streamlit as st

data = pd.read_csv('data/earthquakes.csv')

shv.a5_map(df=data, lat='latitude', lon='longitude', use_sidebar_controls=True)

st.dataframe(data.head(20))

""", language='python')
