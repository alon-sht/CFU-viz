# %%
import pandas as pd #proccing of tables
import plotly.express as px #processing of plots
import numpy as np
import panel as pn
from io import BytesIO
import panel as pn
pn.extension('tabulator','plotly',sizing_mode="stretch_width",)#align='center')
pn.param.ParamMethod.loading_indicator = True
pn.config.raw_css  = [
            """
            .sidenav .bk-root:nth-of-type(1) {
                z-index: 200
            }
            div.choices__list.choices__list--dropdown.is-active > div {
                background: var(--background-color);
            }
            """
            ]
# %%
y_variables=["Normalized_Count_1","Normalized_Count_2","Normalized_Count_3","Normalized_Count_4","Normalized_Count_5"]
cols=['Donor', 'Sample Origin', 'Sample Type', 'Day', 'Sampling point',
       'Sample Dilution', 'Drop Assay Dilution', 'PBS Dilution',
       'Amount of Powder (g)', 'Normalization Factor', 'Average_by', 'Plate']
upload_data_widget=pn.widgets.FileInput(accept='.xlsx')
main=[pn.Column("# Upload CFU Data file",upload_data_widget),
      pn.Column('# Data',"",visible=False),
      pn.Column('# Filters',"",visible=False),
      pn.Column('# Filtered Data',"",visible=False),
      pn.Column('# Parameters',"",visible=False),
      pn.Column('# Plots',visible=False)]
side=['# Filters',pn.Column()]
layout=pn.template.MaterialTemplate(
    site="CFU-Viz", title="CFU-Viz",
    main=main,
    )


def excel_to_df(excel):
    return pd.read_excel(BytesIO(
                    upload_data_widget.value), skiprows=1)


def get_filters(df):
    widgets={}
    default_widget=pn.widgets.MultiChoice(name='1',max_width=700,button_type='primary',margin=[10,10])
    filters=pn.FlexBox()
    for y in df.columns[1:df.columns.get_loc("Dilution")]:
        if len(df[y].unique().tolist())>1:
            widgets[y]=default_widget.clone(name=str(y),options=df[y].unique().tolist())
            widgets[y].value=widgets[y].options
            filters.append(widgets[y])
    
    # widgets.values()
    return widgets

# @pn.depends(filter_widget,watch=True)
# def dataframe_filter(filter_widget):
#     # df=df[df[filter_widgets.name].isin(filter_widgets.value)]
#     return pn.widgets.Tabulator(df)
    

def show_filters(event):
    df=excel_to_df(upload_data_widget.value)
    df=df.replace(0, np.nan)
    df['custom_name']=""
    for col in cols:
        if col in df.columns:
            df[col]=df[col].astype(str)
    filter_widgets=get_filters(df)

    widget_flex_box=pn.FlexBox(*filter_widgets.values())
    # widget_flex_box=pn.Column(*filter_widgets.values())
    
    filter_df=pn.widgets.Tabulator(df,height=350)
    for k,v in filter_widgets.items():
        filter_df.add_filter(v,k)
    main[1][-1]=pn.widgets.Tabulator(df.copy(),height=350)
    main[2][-1]=widget_flex_box
    main[3][-1]=filter_df
    # side[1]=pn.Column(*filter_widgets.values())
    # main[5].append(px.box(filter_df.current_view,x="Sample Type",y=y_variables))
    choose_x=pn.widgets.Select(options=list(filter_widgets.keys()),max_width=400)
    color_by=choose_x.clone(options=[None]+choose_x.options,value=None,name="Color By:")
    facet=choose_x.clone(options=[None]+choose_x.options,value=None,name="Facet By:")
    logy=pn.widgets.Checkbox(name='LOG',value=True,max_width=400)
    points=logy.clone(name='Show Points',value=False)
    height = pn.widgets.IntSlider(
        start=300, end=3000, value=600, step=50, name="Plot Height")
    boxwidth=pn.widgets.FloatSlider(start=0.1, end=1, value=0.6, step=0.1, name="Box Width")
    column_names_list=pn.widgets.MultiChoice(options=choose_x.options,value=choose_x.options[:2],name='Choose X axis value(s):',max_width=400)
    
    main[4].append(pn.Column(column_names_list,color_by,facet,height,boxwidth,logy,points,))
    for i in range(6):
        main[i].visible=True
    
    
    
    @pn.depends(choose_x,color_by,facet,logy,column_names_list,height,points,boxwidth)
    def plot(choose_x,color_by,facet,logy,column_names_list,height,points,boxwidth):
        # for col in column_names_list.value:
        #     df[col]=df[col].astype(str)
        filter_df.current_view['custom_name']=filter_df.current_view[column_names_list].agg('/'.join, axis=1)
        plot=px.box(filter_df.current_view,x='custom_name',y=y_variables,color=color_by,log_y=logy,facet_col=facet,height=height)
        plot.update_yaxes(exponentformat='E')
        plot.update_xaxes(tickangle=90,matches=None)
        plot.update_traces(width=boxwidth, boxmean=True)
        if points:
            plot.update_traces(boxpoints='all')
        else:
            plot.update_traces(boxpoints=None)
        # plot.show(config={'responsive': True,'toImageButtonOptions': {'format': 'svg',}})
        return pn.pane.Plotly(plot,)#config={'responsive': True,'toImageButtonOptions': {'format': 'svg',}})
    # def show_plot(event,choose_x):
    #     # print(event)
        
    #     main[5][-1]=px.box(filter_df.current_view,x=choose_x,y=y_variables)
    
    main[5].append(plot)
    # for filters in filter_widgets.values():
    #     filters.param.watch(plot,'value')
        
    

    



upload_data_widget.param.watch(show_filters,'value')

def get_user_instance():
    return layout.servable()

if __name__.startswith("bokeh_"):
    get_user_instance()
    

# # %%
# #variables
# filepath="" #keep empty if in root 
# filename="20.02.22_RD694_CFU_Alon.xlsx"
# columns_for_plot_name=["Donor","Day","Sample Type","Sample Origin"]
# y_variables=["Normalized_Count_1","Normalized_Count_2","Normalized_Count_3","Normalized_Count_4","Normalized_Count_5"]
# color_by="Sample Origin"
# facet_by=None # write None if you dont want to split plot by category
# log_axis=True
# show_mean=True
# plot_name="plot1"
# plot_width=900
# plot_height=700

# # %%
# # Read CSV file 
# #df=pd.read_csv(os.path.join(filepath,filename), skip_blank_lines=True)
# df=pd.read_excel(os.path.join(filepath,filename),skiprows=1)

# for x in columns_for_plot_name:
#   df[x]=df[x].astype(str)
# df["plot_names"]=df[columns_for_plot_name].agg('/'.join, axis=1)
# max_val_plus_one=log(df[y_variables].max().max(),10)+1

# df[y_variables]=df[y_variables].replace(0, np.nan)

# widgets={}
# default_widget=pn.widgets.MultiChoice(name='1')
# filters=pn.FlexBox()
# for y in df.columns[1:df.columns.get_loc("Dilution")]:
#   widgets[y]=default_widget.clone(name=str(y),options=df[y].unique().tolist(),value=df[y].unique().tolist())
#   filters.append(widgets[y])
# pn.extension()
# all=pn.FlexBox(*widgets.values(),)
# all


# # %%
# #Filter according to above filter
# df_filtered=df
# for widget in all:
#   df_filtered=df_filtered[df_filtered[widget.name].isin(widget.value)]


# # Plot
# plot=px.box(df_filtered,
#             x="plot_names",
#             y=y_variables,
#             log_y=log_axis,
#             color=color_by,
#             width=plot_width,
#             height=plot_height,
#             template='plotly_white',
#             boxmode='group',
#             facet_col=facet_by
#             )
# plot.update_traces(width=0.5)
# plot.update_yaxes(range=(1,max_val_plus_one),exponentformat='E')
# plot.update_xaxes(tickangle=90,matches=None)
# plot.update_traces(width=0.8, boxmean=show_mean)
# plot.show(config={'responsive': True,'toImageButtonOptions': {'format': 'svg',}})