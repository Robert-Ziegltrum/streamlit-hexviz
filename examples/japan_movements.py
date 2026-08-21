import streamlit_hexviz as shv
import pandas as pd
import streamlit as st


st.write('## Container moves in Japan')
st.write('example for the utilization of pre-indexed h3 data sets')

data = pd.read_csv('data/japan_movements.csv')
shv.h3_choropleth(data, h3_col='point_res_7',
                  value_col='count', h3_index_type='int')

st.info('use the navigation: recommended options: color: heat, transform log.')

st.code(""" 
import streamlit_hexviz as shv
import pandas as pd
import streamlit as st

data = pd.read_csv('data/earthquakes.csv')

shv.h3_choropleth(data, h3_col='point_res_7',
                  value_col='count', h3_index_type='int')

""", language='python')

st.info('Despite using csv loads for this example, this pattern can be very well used for loads for e.g. a database.')
