# %%
import pandas as pd
import plotly.express as px 
import numpy as np
from io import BytesIO
import streamlit as st
from PIL import Image
import warnings


# %%
st.set_page_config(layout="wide",page_title="MyCFUViz",page_icon=Image.open("fav.ico"))
pd.options.display.float_format = '{:,.2f}'.format


hide_streamlit_style = """
              <style>
              #MainMenu {visibility: hidden;}
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
            
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 


# %%
y_variables=["Normalized_Count_1","Normalized_Count_2","Normalized_Count_3","Normalized_Count_4","Normalized_Count_5"]
ignore_list=['Count_1','Count_2','Count_3','Count_4','Count_5','Average','LOG','STD','Average Dilutions','Average STD']
default_dict={
                     'color':None,
                     'facet':None,
                     'height':700,
                     'names':"Average_by",
                     'boxwidth':0.8,
                     'points':False,
                     'log':True,
                     'remove_zero':False,
                     'start_at_one':False,
                     'font_size':14,
                     'xlabels':True,
                     'ref_line':False,
                     'manually_sort_values':False
                     }
       
       

def st_header_section():
       # Set up header section of app
       head=st.columns(3)
       head[0]=head[2]=st.write("")
       head[1].image("Mybiotics_LOGO - Large.png",width=350)
       st.title("MyCFUViz")


def st_template_download():
       # Set up template download section
       download_column=st.container()
       download_column.subheader("Template to use for the app")
       with open('Template_CFU.xlsx','rb') as f:
              download_column.download_button('Click Me to Download Template XLSX File',f,file_name='Template.xlsx')
       download_column.markdown('Feel free to change the names of Sample Data columns or add new columns. Other columns should not be changed')

def st_file_upload_section():
       # Set up file upload section of app
       global upload_data_widget
       upload_column=st.container()
       upload_column.subheader("File Upload (use intended template)")
       upload_data_widget=upload_column.file_uploader(label='Upload File', type=['xlsx'],accept_multiple_files=True)


def st_data_section():
       global df
       # Set up section where data is shown
       st.subheader("DataFrames")
       data=st.expander('Raw DataFrame (Click to Show)')
       data.subheader("Raw Data")
       data_text=data.text("Loading data file...")
       df=excel_to_df(upload_data_widget)
       data.write(df.astype(str))
       data_text.text("Data file loaded")


def filter_data():
       # Filter data according to widgets
       global df_filtered, df_melt
       df_filtered=df.copy().query(query[:-2])
       if remove_zero:
              df_filtered[y_variables]=df_filtered[y_variables].replace(0,np.nan)
       else:
              df_filtered[y_variables]=df_filtered[y_variables].replace(0,1.00001)
       if manually_sort_values and 'TestedAgentDilution' in df.columns:
              df_filtered=df_filtered.sort_values(by=sort_by,ascending=sort_by_ascending)
       df_filtered['custom_name']=df_filtered[names].astype(str).agg('/'.join, axis=1)
       df_melt=pd.melt(df_filtered,id_vars=[x for x in df_filtered.columns if x not in y_variables+ignore_list],value_vars=y_variables)


def st_filtered_data_section():
       
       # Set up section where filtered data is shown
       filtered_data=st.expander("Filtered DataFrame (Click to Show)")
       filtered_data.subheader('Filtered Data')
       filtered_data.write(df_filtered.astype(str))





def excel_to_df(upload_data_widget):
       # Get input: excel file
       # Return pandas df
       global cols, df
       warnings.simplefilter(action='ignore', category=UserWarning)
       if len(upload_data_widget)==1:
              df=pd.read_excel(BytesIO(
                    upload_data_widget[0].getvalue()), skiprows=1).round(3)
       elif len(upload_data_widget)>1:
              df=pd.read_excel(BytesIO(
                    upload_data_widget[0].getvalue()), skiprows=1).round(3)
              for file in upload_data_widget[1:]:
                     df=pd.concat([df,pd.read_excel(BytesIO(
                    file.getvalue()), skiprows=1).round(3)])
                     
       ind=list(df.columns).index('Plate')
       cols=df.columns.tolist()[:ind+1]
       df[cols] = df[cols].replace(np.nan, "")
       return df


def add_logo_and_links_to_sidebar():
       #Adds logo and links to the different sections in the sidebar
       st.sidebar.image("Mybiotics_LOGO - Large.png",width=250,)
       links=st.sidebar.container()
       # links.subheader('Links')
       # links.markdown("[File Upload](#file-upload)", unsafe_allow_html=True)
       # links.markdown("[DataFrames](#dataframes)", unsafe_allow_html=True)
       # # links.markdown("[Filtered Data](#filtered-data)", unsafe_allow_html=True)
       # links.markdown("[Figures](#figures)", unsafe_allow_html=True)
       
       
def get_filters_and_add_widgets_to_sidebar(df):
       # Parse the df and get filter widgets based on columns
       
       global query, widget_dict
       widget_dict={}
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
       
def add_df_sort_settings_to_sidebar():
       global sort_by,manually_sort_values,sort_by_ascending
       
       df_sort_st=st.sidebar.expander("Data Sort Settings")
       df_sort_st.subheader('Data Sort Settings')
       updated_default_dict=default_dict
       multi_options=[None]+cols
       
       
       manually_sort_values=df_sort_st.checkbox(label='Manually Sort Values', value=updated_default_dict['manually_sort_values'])
       df_sort_st.markdown('Pick up to five parameters to sort by. Note the order and whether they are in ascending or descending order.')
       df_sort_st.markdown('---')
       
       if "Experiment" in multi_options: val1=multi_options.index("Experiment")
       else: val1=0
       sort1=df_sort_st.selectbox('Sort By (1)',options=multi_options,index=val1)
       sort1_ascending=df_sort_st.checkbox("Ascending? (1)",value=False)
       df_sort_st.markdown('---')
       if "TimePoint" in multi_options: val2=multi_options.index("TimePoint")
       else: val2=0
       sort2=df_sort_st.selectbox('Sort By (2)',options=multi_options,index=val2)
       sort2_ascending=df_sort_st.checkbox("Ascending? (2)",value=False)
       df_sort_st.markdown('---')
       if "TestedPhase" in multi_options: val3=multi_options.index("TestedPhase")
       else: val3=0
       sort3=df_sort_st.selectbox('Sort By (3)',options=multi_options,index=val3)
       sort3_ascending=df_sort_st.checkbox("Ascending? (3)",value=False)
       df_sort_st.markdown('---')
       if "TestedAgent" in multi_options: val4=multi_options.index("TestedAgent")
       else: val4=0
       sort4=df_sort_st.selectbox('Sort By (4)',options=multi_options,index=val4)
       sort4_ascending=df_sort_st.checkbox("Ascending? (4)",value=False)
       df_sort_st.markdown('---')
       if "TestedAgentDilution" in multi_options: val5=multi_options.index("TestedAgentDilution")
       else: val5=0
       sort5=df_sort_st.selectbox('Sort By (5)',options=multi_options,index=val5)
       sort5_ascending=df_sort_st.checkbox("Ascending? (5)",value=False)
       
       sort_by=[sort1,sort2,sort3,sort4,sort5]
       sort_by=[x for x in sort_by if x]
       # print(sort_by)
       sort_by_ascending=[sort1_ascending,sort2_ascending,sort3_ascending,sort4_ascending,sort5_ascending]
       sort_by_ascending=[sort_by_ascending[i] for i,x in enumerate(sort_by) if x]
       # print(sort_by_ascending)
       
       

       
def add_plot_settings_to_sidebar():
       # Adds plot settings widget to sidebar
       global color, facet, height, names,boxwidth,points,log,remove_zero,start_at_one,font_size,xlabels,\
                     updated_default_dict,ref_line,show_meta_on_hover,multi_options,ylim_top,ylim_bottom,\
                            manually_set_ylim,log_ylim,ylim_values

       
       # updated_default_dict=set_values_from_url(default_dict)
       updated_default_dict=default_dict
       
       plot_settings=st.sidebar.expander("Plot Settings")
       plot_settings.subheader('Plot Widgets')
       # plot_settings.button("Reset Defaults",on_click=reset_all_defaults)
       multi_options=[None]+cols
       color=plot_settings.selectbox(label='Color',options=multi_options,index=multi_options.index(updated_default_dict['color']))
       facet=plot_settings.selectbox(label='Facet',options=multi_options,index=multi_options.index(updated_default_dict['facet']))
       height=plot_settings.slider(label='Height',min_value=300,max_value=1200,value=int(updated_default_dict['height']),step=50)
       font_size=plot_settings.slider(label='Font Size',min_value=1,max_value=25,value=int(updated_default_dict['font_size']))
       temp_opts=['SampleID/PlateID', 'Experiment', 'Bacteria', 'SampleOrigin',
       'TestedPhase', 'TimePoint', 'TestedAgent', 'TestedAgentDilution',
        'Plate']
       #Choose columns by which to aggregate samples
       #Remove columns that only have one value 
       agg_opts = [opt for opt in temp_opts if opt in cols if len(df[opt].drop_duplicates())>1]
       if len(agg_opts)==0:
              agg_opts=['Average_by']
              

       
       names=plot_settings.multiselect(label='Name Samples By Chosen Columns',options=cols,default=agg_opts)
       boxwidth=plot_settings.slider(label='Box Width',min_value=0.1,max_value=1.0,value=float(updated_default_dict['boxwidth']),step=0.1)
       plot_settings.markdown("---")
       manually_set_ylim=plot_settings.checkbox("Manually Set Y-Lim", value=False)
       
       ylim_bottom,ylim_top=plot_settings.slider(label='Manually set ylim (minimum and maximum)',min_value=-20.0,max_value=20.0,value=[-1.0,8.0],step=0.2,)#format="10^%f")
       plot_settings.markdown("*If the chosen value is x, positive are 10^x, while negative x values are -10^x")
       # ylim_bottom=plot_settings.slider(label='Manually set ylim (min)',min_value=-20,max_value=20,value=0)
       ylim_values=plot_settings.markdown(f"")
       plot_settings.markdown("---")
       points=plot_settings.checkbox(label='Show Points', value=updated_default_dict['points'])
       xlabels=plot_settings.checkbox(label='Show X axis labels', value=updated_default_dict['xlabels'])
       log=plot_settings.checkbox(label='Log Y Axis', value=updated_default_dict['log'])
       start_at_one=plot_settings.checkbox(label='Start Axis at 1', value=updated_default_dict['start_at_one'],)#disabled=True)
       remove_zero=plot_settings.checkbox(label='Remove Zero Values', value=updated_default_dict['remove_zero'])
       ref_line=plot_settings.checkbox(label='Draw Reference Line', value=updated_default_dict['ref_line'])
       show_meta_on_hover=plot_settings.checkbox("Show Metadata On Hover",value=True)
       
def set_values_from_url(defdict):
       for val in defdict.keys():
              if val in st.experimental_get_query_params().keys():
                     defdict[val]=st.experimental_get_query_params()[val][0]
                     if defdict[val]=='None':
                            defdict[val]=None
                     elif defdict[val]=='True':
                            defdict[val]=True
                     elif defdict[val]=='False':
                            defdict[val]=False
       return defdict

# def reset_all_defaults():
#        updated_default_dict=default_dict
       
       
def add_custom_name_column():
       df_filtered['custom_name']=df_filtered[names].astype(str).agg('/'.join, axis=1)


def st_plot_section():
       # Set up section where main cfu plot is shown 
       st_figure=st.container()
       st_figure.markdown("---")
       st_figure.subheader("Figures")
       st_figure.subheader("CFU Plot")
       #Plot
       fig=boxplot(df_filtered,y_variables,y_label='CFU')
       st_figure.plotly_chart(fig,use_container_width=True)
       




def get_ylim(df,y,force_disable_axis_start_at_one,force_disable_log):
       #Get limit of y axis based on parameters
       if log and not force_disable_axis_start_at_one:
              max_val=np.log10(df[y].max().max())+0.5
              y_val=10**max_val
              min_val=np.log10(df[y].min().min())-0.5              
       else:
              max_val=df[y].max().max()*1.05
              y_val=max_val
              if df[y].min().min()>0:
                     min_val=df[y].min().min()*0.95
              else:
                     min_val=df[y].min().min()*1.05
       if manually_set_ylim:
              how_to_set_ylim='manually'
              if (log) and (not force_disable_log):
                     return [ylim_bottom,ylim_top,ylim_top,how_to_set_ylim]
              elif ylim_bottom!=0:       
                     return [int(ylim_bottom/abs(ylim_bottom))*10**abs(ylim_bottom),10**ylim_top,10**ylim_top,how_to_set_ylim]
              else:
                     return [1,10**ylim_top,10**ylim_top,how_to_set_ylim]
       else:
              how_to_set_ylim='automatically'
              if start_at_one and not force_disable_axis_start_at_one:
                     return [0,max_val,y_val,how_to_set_ylim]
              elif not start_at_one:
                     return [min_val,max_val,y_val,how_to_set_ylim]
         
         
def boxplot(df,y,ref_val=1,y_label=None,force_disable_log=False,force_disable_axis_start_at_one=False):
    
       if color:
              df[color]=df[color].astype(str)
       if force_disable_log: 
              logy=False 
       else: 
              logy=log
       fig=px.box(df,x='custom_name',y=y,color=color,height=height,log_y=logy,facet_col=facet)
       min_val,max_val,y_val,how_to_set_ylim=get_ylim(df,y,force_disable_axis_start_at_one,force_disable_log)
       if how_to_set_ylim=='automatically':
              ylim_values.markdown(f"Y Limits are {how_to_set_ylim} set")
       else:
              ylim_values.markdown(f"Y Limits are {how_to_set_ylim} set to {min_val: .1E} and {max_val: .1E}")
       
       
       fig.update_layout(yaxis_range=[min_val,max_val],font=dict(size=font_size,),hovermode="x")
       fig.update_traces(width=boxwidth, boxmean=True)
       fig.update_xaxes(tickangle=90,matches=None,title=None,dtick=1,autorange=True,showticklabels=xlabels)
       fig.update_yaxes(exponentformat='E',title=y_label)

       if points:
              fig.update_traces(boxpoints='all',jitter=0.05)
       else:
              fig.update_traces(boxpoints=None)
              
       hover_plot = px.bar(df, x="custom_name", y=[y_val] * len(df["custom_name"]),
                                          barmode="overlay",hover_data=cols,facet_col=facet,log_y=log,color=color)
       hover_plot.update_traces(width=boxwidth, opacity=0,showlegend=False)
       hover_plot.update_layout(yaxis_range=[0,max_val])
       if show_meta_on_hover:
              fig.add_traces(hover_plot.data)
       if ref_line:
              fig.add_hline(y=ref_val)
    
       return fig

def choose_reference():
       global ref_value
       st.markdown('---')
       st_choose_ref_sample=st.container()
       st_choose_ref_sample.subheader("Choose Reference Sample")
       choose_ref_sample=st_choose_ref_sample.selectbox(label='Reference Sample',options=df_filtered['custom_name'].unique())
       choose_ref_type=st_choose_ref_sample.selectbox(label='Min/Max/Mean/Median',options=['Mean','Median','Min','Max',])
       ref_opts=df_filtered[df_filtered['custom_name'].isin([choose_ref_sample])][y_variables]
       if choose_ref_type=='Min':
              ref_value=ref_opts.min().min()
       elif choose_ref_type=='Max':
              ref_value=ref_opts.max().max()
       elif choose_ref_type=='Median':
              ref_value=ref_opts.median().median()
       elif choose_ref_type=='Mean':
              ref_value=ref_opts.mean().mean()
       st_choose_ref_sample.markdown(f"Reference value is set to the {choose_ref_type} value of '{choose_ref_sample}'. \n\n Chosen reference value is {ref_value:.2}")

 
def percent_survaviability_plot_section():
       st.markdown('---')
       st_survivability=st.container()
       st_survivability.subheader("% Survivability Plot")
       st_survivability.markdown("Uses the reference sample chosen in the sidebar.")
       
       # Calculate % out of reference
       y_norm=[val+'%' for val in y_variables]
       df_filtered[y_norm]=df_filtered[y_variables]*100/ref_value
       
       
       #Plot % out of reference plot
       fig=boxplot(df_filtered,y_norm,ref_val=100,y_label='% Survivability')
       st_survivability.plotly_chart(fig,use_container_width=True)
       
def ref_excluded_plot_section():       
       
       st.markdown('---')
       st_survivability=st.container()
       st_survivability.subheader("Delta From Reference")
       st_survivability.markdown("Referece subtracted from the rest of the values. Uses the reference sample chosen in the sidebar.")
       
       # Calculate values by subtracting value of ref sample
       y_ref_excluded=[val+'_ref_excluded' for val in y_variables]
       df_filtered[y_ref_excluded]=df_filtered[y_variables]-ref_value
       
       #Plotting, force disable log and force disable start at one. 
       if log:
              data=y_ref_excluded_log
       else:
              data=y_ref_excluded
       fig2=boxplot(df_filtered,data,y_label='Log Delta',ref_val=0,force_disable_log=True,force_disable_axis_start_at_one=True)
       st_survivability.plotly_chart(fig2,use_container_width=True)
       
       
       
def update_parameters_in_link():
              st.experimental_set_query_params(
                     color=color, 
                     facet=facet, 
                     height=height, 
                     names=names, 
                     boxwidth=boxwidth, 
                     points=points, 
                     log=log, 
                     remove_zero=remove_zero, 
                     start_at_one=start_at_one, 
                     font_size=font_size, 
                     xlabels=xlabels, 
                     **widget_dict
                     )
              

def main():
       # Main part of the app
       st_header_section()
       st_template_download()
       st_file_upload_section()
       if upload_data_widget:
              st_data_section()
              
              add_logo_and_links_to_sidebar()
              get_filters_and_add_widgets_to_sidebar(df)
              add_df_sort_settings_to_sidebar()
              add_plot_settings_to_sidebar()
              # set_values_from_url()
              # update_parameters_in_link()
              filter_data()
              st_filtered_data_section()
              # add_custom_name_column()
              st_plot_section()
              # st_plot2_section()
              choose_reference()
              percent_survaviability_plot_section()
              ref_excluded_plot_section()
              
if __name__=='__main__':
       main()

# %%
