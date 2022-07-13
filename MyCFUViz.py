# %%
import pandas as pd
import plotly.express as px 
import numpy as np
from io import BytesIO
import streamlit as st
from PIL import Image

st.set_page_config(layout="wide",page_title="MyCFUViz",page_icon=Image.open("fav.ico"))
pd.options.display.float_format = '{:,.2f}'.format
hide_streamlit_style = """
              <style>
              footer {visibility: hidden;}
              [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
                     width: 500px;
                     }
              [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
                     width: 500px;
                     margin-left: -500px;
                     }
            </style>
            """
            
            

# hide_streamlit_style = """
#               <style>
#               #MainMenu {visibility: hidden;}
#               footer {visibility: hidden;}
#               [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
#                      width: 500px;
#                      }
#               [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
#                      width: 500px;
#                      margin-left: -500px;
#                      }
#             </style>
#             """            
            
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 


# %%
y_variables=["Normalized_Count_1","Normalized_Count_2","Normalized_Count_3","Normalized_Count_4","Normalized_Count_5"]
# cols=['Donor', 'Sample Origin', 'Sample Type', 'Day', 'Sampling point',
#        'Sample Dilution', 'Drop Assay Dilution', 'PBS Dilution',
#        'Amount of Powder (g)', 'Normalization Factor', 'Average_by', 'Plate']

def st_header_section():
       # Set up header section of app
       head=st.columns(3)
       head[0]=head[2]=st.write("")
       head[1].image("Mybiotics_LOGO - Large.png",width=350)
       st.title("MyCFUViz")


def st_file_upload_section():
       # Set up file upload section of app
       global upload_data_widget
       upload_column=st.container()
       upload_column.subheader("File Upload")
       upload_data_widget=upload_column.file_uploader(label='Upload File', type=['xlsx'])
       


def st_data_section():
       global df
       # Set up section where data is shown
       data=st.container()
       data.subheader("Raw Data")
       data_text=data.text("Loading data file...")
       df=excel_to_df(upload_data_widget)
       data.write(df.astype(str))
       data_text.text("Data file loaded")
def filter_data():
       # Filter data according to widgets
       global df_filtered
       df_filtered=df.query(query[:-2])
       
def st_filtered_data_section():
       
       # Set up section where filtered data is shown
       filtered_data=st.container()
       filtered_data.subheader('Filtered Data')
       
       filtered_data.write(df_filtered.astype(str))


def st_plot_section():
       # Set up section where plots are shown
       st_figure=st.container()
       st_figure.subheader("Figures")
       st_figure.subheader("CFU Plot")
       if remove_zero:
              df=df_filtered.replace(0,np.nan)
       else:
              df=df_filtered
       fig=px.box(df,x='custom_name',y=y_variables,color=color,height=height,log_y=log,facet_col=facet)
       # if start_at_one:
       #        fig.update_layout(yaxis_range=[1,np.log10(df[y_variables].max().max())+0.5])
       # else:
       #        fig.update_layout(yaxis_range=[np.log10(df[y_variables].min().min())-0.5,np.log10(df[y_variables].max().max())+0.5])
       fig.update_traces(width=boxwidth, boxmean=True)
       fig.update_xaxes(tickangle=90,matches=None,title=None)
       if points:
            fig.update_traces(boxpoints='all')
       else:
            fig.update_traces(boxpoints=None)
       with st.spinner(text="In progress..."):
              st_figure.plotly_chart(fig,use_container_width=True)


def excel_to_df(upload_data_widget):
       # Get input: excel file
       # Return pandas df
       global cols
       df=pd.read_excel(BytesIO(
                    upload_data_widget.getvalue()), skiprows=1).round(3)
       ind=list(df.columns).index('Plate')
       cols=df.columns.tolist()[:ind+1]
       df[cols] = df[cols].replace(np.nan, "")
       return df


def add_logo_and_links_to_sidebar():
       #Adds logo and links to the different sections in the sidebar
       st.sidebar.image("Mybiotics_LOGO - Large.png",width=250,)
       links=st.sidebar.container()
       links.subheader('Links')
       links.markdown("[File Upload](#file-upload)", unsafe_allow_html=True)
       links.markdown("[Raw Data](#raw-data)", unsafe_allow_html=True)
       links.markdown("[Filtered Data](#filtered-data)", unsafe_allow_html=True)
       links.markdown("[Figures](#figures)", unsafe_allow_html=True)
       
       
def get_filters_and_add_widgets_to_sidebar(df):
       # Parse the df and get filter widgets based on columns
       widget_dict={}
       global query
       query=f""
       st.sidebar.header('Widgets',)
       filter_widgets=st.sidebar.expander("Data Filters. After choosing filters press the button at the bottom.")
       filter_widgets.subheader('Filter Data')
       form=filter_widgets.form('form1')
       
       if "Dilution" in df.columns:
              sample_data_col="Dilution"
       elif "CountedDilution" in df.columns:
              sample_data_col="CountedDilution"
       else:
              sample_data_col=df.columns[-1]
       
       
       for y in df.columns[1:df.columns.get_loc(sample_data_col)]:
              if len(df[y].unique().tolist())>1:
                     widget_dict[y]=form.multiselect(label=str(y),options=df[y].unique().tolist(),default=df[y].unique().tolist())    
                     query+=f"`{y}`  in {widget_dict[y]} & "
       form.form_submit_button("Fiter Data")
       
def add_plot_settings_to_sidebar():
       # Adds plot settings widget to sidebar
       global color, facet, height, names,boxwidth,points,log,remove_zero,start_at_one
       plot_settings=st.sidebar.expander("Plot Settings")
       plot_settings.subheader('Plot Widgets')
       color=plot_settings.selectbox(label='Color',options=[None]+cols,index=0)
       facet=plot_settings.selectbox(label='Facet',options=[None]+cols,index=0)
       height=plot_settings.slider(label='Height',min_value=300,max_value=1200,value=500,step=50)
       temp_opts=['SampleID/PlateID', 'Experiment', 'Bacteria', 'SampleOrigin',
       'TestedPhase', 'TimePoint', 'TestedAgent', 'TestedAgentDilution',
        'Plate']
       agg_opts=[]
       for opt in temp_opts:
              if opt in cols:
                     agg_opts.append(opt)
       if len(agg_opts)==0:
              agg_opts=['Average_by']
       names=plot_settings.multiselect(label='Name Samples By Chosen Columns',options=cols,default=agg_opts)
       boxwidth=plot_settings.slider(label='Box Width',min_value=0.1,max_value=1.0,value=0.8,step=0.1)
       points=plot_settings.checkbox(label='Show Points', value=False)
       log=plot_settings.checkbox(label='Log Y Axis', value=True)
       start_at_one=plot_settings.checkbox(label='Start Axis at 1', value=False,disabled=True)
       remove_zero=plot_settings.checkbox(label='Remove Zero Values', value=True)
       
def add_custom_name_column():
       df_filtered['custom_name']=df_filtered[names].astype(str).agg('/'.join, axis=1)
       
       
def percent_survaviaviluty_section():
       st_survivability=st.container()
       st_survivability.subheader("% Survivability Plot")
       if remove_zero:
              df=df_filtered.replace(0,np.nan)
       else:
              df=df_filtered
       choose_ref_sample=st_survivability.selectbox(label='Reference Sample',options=df_filtered['custom_name'].unique())
       choose_ref_type=st_survivability.selectbox(label='Min/Max/Mean/Median',options=['Min','Max','Mean','Median'])
       ref_opts=df[df['custom_name'].isin([choose_ref_sample])][y_variables]
       if choose_ref_type=='Min':
              ref_value=ref_opts.min().min()
       elif choose_ref_type=='Max':
              ref_value=ref_opts.max().max()
       elif choose_ref_type=='Median':
              ref_value=ref_opts.median().median()
       elif choose_ref_type=='Mean':
              ref_value=ref_opts.mean().mean()
       st_survivability.text(f"Reference value is set to the {choose_ref_type} value of '{choose_ref_sample}'. \n Chosen reference value is {ref_value}")
       y_norm=[val+'%' for val in y_variables]
       df[y_norm]=df[y_variables]*100/ref_value
       # st_survivability.text(df)
       fig=px.box(df,x='custom_name',y=y_norm,color=color,height=height,log_y=log,facet_col=facet,)
       # if start_at_one:
       #        if log:
       #               fig.update_layout(yaxis_range=[1,np.log10(df[y_variables].max().max())+0.5])
       #        else:
       #               fig.update_yaxes(autorange=True)
       # else:
       #        if log:
       #               fig.update_layout(yaxis_range=[np.log10(df[y_variables].min().min())-0.5,np.log10(df[y_variables].max().max())+0.5])
       #        else:
       #               fig.update_yaxes(autorange=True)
       fig.update_traces(width=boxwidth, boxmean=True)
       fig.update_xaxes(tickangle=90,matches=None,title=None)
       if points:
            fig.update_traces(boxpoints='all')
       else:
            fig.update_traces(boxpoints=None)
       with st.spinner(text="In progress..."):
              st_survivability.plotly_chart(fig,use_container_width=True)
       # st_survivability
       
       
       
       

def main():
       # Main part of the app
       st_header_section()
       st_file_upload_section()
       if upload_data_widget is not None:
              st_data_section()
              
              add_logo_and_links_to_sidebar()
              get_filters_and_add_widgets_to_sidebar(df)
              filter_data()
              st_filtered_data_section()
              add_plot_settings_to_sidebar()
              add_custom_name_column()
              st_plot_section()
              percent_survaviaviluty_section()
              
              
if __name__=='__main__':
       main()

# %%
