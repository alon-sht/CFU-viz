# %%
import pandas as pd #proccing of tables
import plotly.express as px #processing of plots
import numpy as np
from io import BytesIO
import streamlit as st
st.set_page_config(layout="wide")
pd.set_option("display.precision", 2)
pd.options.display.float_format = '{:,.2f}'.format
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
# %%
y_variables=["Normalized_Count_1","Normalized_Count_2","Normalized_Count_3","Normalized_Count_4","Normalized_Count_5"]
cols=['Donor', 'Sample Origin', 'Sample Type', 'Day', 'Sampling point',
       'Sample Dilution', 'Drop Assay Dilution', 'PBS Dilution',
       'Amount of Powder (g)', 'Normalization Factor', 'Average_by', 'Plate']
# upload_data_widget=pn.widgets.FileInput(accept='.xlsx')
head=st.columns(3)
head[0]=head[2]=st.write("")
head[1].image("Mybiotics_LOGO - Large.png",width=350)
st.title("MyCFUViz")

main=st.container()
upload_data_widget=main.file_uploader(label='Upload File', type=['xlsx'])

def excel_to_df(upload_data_widget):
    return pd.read_excel(BytesIO(
                    upload_data_widget.getvalue()), skiprows=1).round(3)

def get_filters(df):
       
       
       widget_dict={}
       global query
       query=f""
       st.sidebar.image("Mybiotics_LOGO - Large.png",width=250,)
       st.sidebar.header('Widgets',)
       st.sidebar.subheader('Filter Data')
       for y in df.columns[1:df.columns.get_loc("Dilution")]:
              if len(df[y].unique().tolist())>1:
                     widget_dict[y]=st.sidebar.multiselect(label=str(y),options=df[y].unique().tolist(),default=df[y].unique().tolist())    
                     query+=f"`{y}`  in {widget_dict[y]} & "
       


if upload_data_widget is not None:
       data=st.container()
       data.title("Raw Data")
       
       widgets=st.container()
       
       
       filtered_data=st.container()
       filtered_data.title('Filtered Data')
       
       data_text=data.text("Loading...")
       df=excel_to_df(upload_data_widget)
       data_text.text("Loaded")
       data.write(df.astype(str))
       get_filters(df)
       df_filtered=df.query(query[:-2])
       
       
       filtered_data.write(df_filtered.astype(str))
       st.sidebar.subheader('Plot Setting')
       x_val=st.sidebar.selectbox(label='X Value',options=['ID', 'Donor', 'Sample Origin', 'Sample Type', 'Day', 'Sampling point',
       'Sample Dilution', 'Drop Assay Dilution', 'PBS Dilution',
       'Amount of Powder (g)', 'Normalization Factor', 'Average_by', 'Plate',],index=1)
       color=st.sidebar.selectbox(label='Color',options=[None,'ID', 'Donor', 'Sample Origin', 'Sample Type', 'Day', 'Sampling point',
       'Sample Dilution', 'Drop Assay Dilution', 'PBS Dilution',
       'Amount of Powder (g)', 'Normalization Factor', 'Average_by', 'Plate',],index=0)
       facet=st.sidebar.selectbox(label='Facet',options=[None,'ID', 'Donor', 'Sample Origin', 'Sample Type', 'Day', 'Sampling point',
       'Sample Dilution', 'Drop Assay Dilution', 'PBS Dilution',
       'Amount of Powder (g)', 'Normalization Factor', 'Average_by', 'Plate',],index=0)
       height=st.sidebar.slider(label='Height',min_value=300,max_value=1200,value=500,step=50)
       names=st.sidebar.multiselect(label='Names',options=['ID', 'Donor', 'Sample Origin', 'Sample Type', 'Day', 'Sampling point',
       'Sample Dilution', 'Drop Assay Dilution', 'PBS Dilution',
       'Amount of Powder (g)', 'Normalization Factor', 'Average_by', 'Plate',],default=['Donor', 'Sample Origin', 'Sample Type'])    
       df_filtered['custom_name']=df_filtered[names].astype(str).agg('/'.join, axis=1)
       
       boxwidth=st.sidebar.slider(label='Box Width',min_value=0.1,max_value=1.0,value=0.8,step=0.1)
       points=st.sidebar.checkbox(label='Show Points', value=False)
       log=st.sidebar.checkbox(label='Log Y Axis', value=True)
       fig=px.box(df_filtered,x='custom_name',y=y_variables,color=color,height=height,log_y=log,facet_col=facet)
       fig.update_traces(width=boxwidth, boxmean=True)
       fig.update_xaxes(tickangle=90,matches=None)
       
       if points:
            fig.update_traces(boxpoints='all')
       else:
            fig.update_traces(boxpoints=None)
       st.plotly_chart(fig,use_container_width=True)
       

