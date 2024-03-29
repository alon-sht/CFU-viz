# %%
from calendar import c
import pandas as pd
import plotly.express as px
import numpy as np
from io import BytesIO
import streamlit as st
from PIL import Image
import warnings
import plotly.io as pio
from scipy.stats import mannwhitneyu, wilcoxon, kruskal
from st_aggrid import (
    GridOptionsBuilder,
    AgGrid,
    GridUpdateMode,
    DataReturnMode,
    JsCode,
)
from streamlit_toggle import st_toggle_switch
from streamlit_sortables import sort_items

pio.templates.default = "plotly"


# %%
st.set_page_config(
    layout="wide", page_title="MyCFUViz", page_icon=Image.open("fav.ico")
)
pd.options.display.float_format = "{:,.2f}".format
loaded = False
ref_value = 1
hide_streamlit_style = """
              <style>
              #MainMenu {visibility: hidden;}
              footer {visibility: hidden;}
            </style>
            """

st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# %%
y_variables = [
    "Normalized_Count_1",
    "Normalized_Count_2",
    "Normalized_Count_3",
    "Normalized_Count_4",
    "Normalized_Count_5",
]
ignore_list = [
    "Count_1",
    "Count_2",
    "Count_3",
    "Count_4",
    "Count_5",
    "Average",
    "LOG",
    "STD",
    "Average Dilutions",
    "Average STD",
]
default_dict = {
    "color": None,
    "facet": None,
    "height": 700,
    "names": "Average_by",
    "boxwidth": 0.8,
    "points": False,
    "log": True,
    "remove_zero": False,
    "start_at_one": False,
    "font_size": 16,
    "xlabels": True,
    "ref_line": False,
    "manually_sort_values": False,
    "turn_xlabels": True,
}

cols_for_reference = ["TestedPhase", "TimePoint", "TestedAgent"]


def st_header_section():
    # Set up header section of app
    head = st.columns(3)
    head[0] = head[2] = st.write("")
    head[1].image("logo.png", width=350)
    st.title("MyCFUViz")


def st_template_download():
    # Set up template download section
    download_column = st.container()
    download_column.subheader("Template to use for the app")
    download_column.markdown(
        "Feel free to change the names of Sample Data columns or add new columns. Other columns should not be changed."
    )
    with open("Template_CFU.xlsx", "rb") as f:
        download_column.download_button(
            "Click Me to Download Template XLSX File", f, file_name="Template.xlsx"
        )


def st_file_upload_section():
    # Set up file upload section of app
    global upload_data_widget, uploaded_file_names
    upload_container = st.container()
    upload_container_col1, upload_container_col2 = upload_container.columns(2)
    upload_container.subheader("File Upload (use intended template)")
    upload_container.markdown(
        "You can add multiple files, the app will combine them. Make sure the columns in each file are the same."
    )
    upload_data_widget = upload_container.file_uploader(
        label="Upload File", type=["xlsx"], accept_multiple_files=True
    )
    uploaded_file_names = ""
    # for file in upload_data_widget:
    #        upload_data_widget+=str(file.name)
    #        upload_data_widget+=","
    # uploaded_file_names=uploaded_file_names[:-1]


def load_dataframe():
    global df, loaded
    df = excel_to_df(upload_data_widget)
    # st.session_state.df=df
    loaded = True


def return_df(which):
    if which == "df_melt":
        return df_melt
    if which == "df":
        return df
    elif which == "df_filtered":
        return df_filtered


def filter_data():
    # print("filter_data")
    # Filter data according to widgets
    global df_filtered, df_melt
    df_filtered = df.copy().query(query[:-2])
    # st.session_state.df_filtered=df_filtered
    df_filtered["only_zero"] = np.where(
        df_filtered[y_variables].mean(axis=1) == 0, "y", "n"
    )
    # st.write(.astype(str))
    if remove_zero == "Remove Zero Values Only When Not All Counts Are Zero":
        # df_filtered[y_variables].where(df_filtered['only_zero']=='n').replace(0,np.nan)
        for col in y_variables:
            df_filtered.loc[
                (df_filtered["only_zero"] == "n") & (df_filtered[col] == 0), col
            ] = np.nan
        df_filtered[y_variables] = df_filtered[y_variables].replace(0, 1.00001)
    elif remove_zero == "Remove All Zero Values":
        df_filtered[y_variables] = df_filtered[y_variables].replace(0, np.nan)
    elif remove_zero == "Don't Remove Zero Values":
        df_filtered[y_variables] = df_filtered[y_variables].replace(0, 1.00001)
    # if manually_sort_values:
    # df_filtered['TestedAgentDilution']=df_filtered['TestedAgentDilution'].str.extract('(\d+)', expand=False).astype('float').astype('Int64')
    df_filtered = df_filtered.sort_values(by=sort_by, ascending=sort_by_ascending)
    df_filtered["custom_name"] = df_filtered[names].astype(str).agg("|".join, axis=1)

    df_melt = pd.melt(
        df_filtered,
        id_vars=[x for x in df_filtered.columns if x not in y_variables + ignore_list],
        value_vars=y_variables,
    )
    update_df_melt_according_to_ref()

    # st.write(df_melt.astype(str))


def update_df_melt_according_to_ref():
    df_melt["value_norm"] = df_melt["value"] * 100 / ref_value
    df_melt["value_delta_ref"] = df_melt["value"] - ref_value
    df_melt["value_delta_ref_log"] = np.log10(df_melt["value"] / ref_value)


def st_data_section():
    # Set up section where data is shown
    st.subheader("DataFrames")
    data = st.container()
    load_data = data.checkbox(
        "Show Data Table", key="load_data", help="Click to show the data table"
    )

    if load_data:
        # unfiltered_data = data.checkbox(
        #     "Data before applying filters", key="original_data"
        # )
        # if unfiltered_data:
        data.write(df_melt.astype(str))
        st.download_button(
            "Download DataFrame",
            data=to_excel(df_melt),
            file_name="df.xlsx",
            mime="application/vnd.ms-excel",
        )

    # data=st.expander('Raw DataFrame (Click to Show)')


def excel_to_df(upload_data_widget):
    # Get input: excel file
    # Return pandas df
    global cols, df
    warnings.simplefilter(action="ignore", category=UserWarning)
    # if len(upload_data_widget) == 1:
    #     xl = pd.ExcelFile(BytesIO(upload_data_widget[0].getvalue()), engine="openpyxl")
    #     sheet = st.radio(
    #         "In case of multiple sheets, please select which one to use.",
    #         xl.sheet_names,
    #     )
    #     df = pd.read_excel(
    #         BytesIO(upload_data_widget[0].getvalue()), skiprows=1, sheet_name=sheet
    #     ).round(3)
    if len(upload_data_widget) >= 1:
        df = pd.concat(
            [
                pd.read_excel(BytesIO(file.getvalue()), skiprows=1).round(3)
                for file in upload_data_widget
            ]
        )

        # df = pd.read_excel(BytesIO(upload_data_widget[0].getvalue()), skiprows=1).round(
        #     3
        # )
        # for file in upload_data_widget[1:]:
        #     df = pd.concat(
        #         [df, pd.read_excel(BytesIO(file.getvalue()), skiprows=1).round(3)]
        #     )

    ind = list(df.columns).index("Count_1")
    cols = df.columns.tolist()[: ind - 1]
    # st.write(cols)
    df[cols] = df[cols].replace(np.nan, "")
    return df


def add_logo_and_links_to_sidebar():
    # Adds logo and links to the different sections in the sidebar
    st.sidebar.image(
        "logo.png",
        width=250,
    )
    # links=st.sidebar.container()
    # links.subheader('Links')
    # links.markdown("[File Upload](#file-upload)", unsafe_allow_html=True)
    # links.markdown("[DataFrames](#dataframes)", unsafe_allow_html=True)
    # # links.markdown("[Filtered Data](#filtered-data)", unsafe_allow_html=True)
    # links.markdown("[Figures](#figures)", unsafe_allow_html=True)


def get_filters_and_add_widgets_to_sidebar(df):
    # Parse the df and get filter widgets based on columns

    global query, widget_dict
    widget_dict = {}
    query = f""
    st.sidebar.header(
        "Widgets",
    )
    filter_widgets = st.sidebar.expander("Data Filters")
    filter_widgets.subheader("Filter Data")
    filter_widgets.markdown(
        "After selecting filters press the 'Apply Filters' button at the bottom."
    )
    filter_widgets.markdown("Only shows columns that contain more than 1 unique value.")
    form = filter_widgets.form("form1")

    if "Dilution" in df.columns:
        sample_data_col = "Dilution"
    elif "CountedDilution" in df.columns:
        sample_data_col = "CountedDilution"
    else:
        sample_data_col = df.columns[-1]

    for y in cols:  # df.columns[1 : df.columns.get_loc(sample_data_col)]:
        if len(df[y].unique().tolist()) > 1:
            widget_dict[y] = form.multiselect(
                label=str(y),
                options=df[y].unique().tolist(),
                default=df[y].unique().tolist(),
                key=str(y),
            )
            query += f"`{y}`  in {widget_dict[y]} & "

    form.form_submit_button("Apply Filters")


def add_df_sort_settings_to_sidebar():
    global sort_by, sort_by_ascending

    df_sort_st = st.sidebar.expander("Data Sort Settings")
    df_sort_st.subheader("Data Sort Settings")

    sort_by = []
    sort_by_ascending = []
    st.write("To sort the data, select the columns to sort by")
    sort_by_cols = df_sort_st.multiselect(
        "Columns to sort by", options=cols, default=[], key="sort_by_cols"
    )
    if sort_by_cols:
        df_sort_st.write("Reorder categories by dragging and dropping:")
        with df_sort_st:
            sort_by = sort_items(sort_by_cols)
            st.session_state.sort_by = sort_by
            sort_by_ascending = []
            for i in sort_by:
                test_default = (
                    st.session_state[f"sort_asc_{i}"]
                    if f"sort_asc_{i}" in st.session_state
                    else False
                )
                asc = st_toggle_switch(
                    f"Sort {i} Ascending",
                    default_value=True,
                    key=f"sort_asc_{i}",
                    label_after=False,
                )
                sort_by_ascending.append(asc if asc else False)


def add_plot_settings_to_sidebar():
    # Adds plot settings widget to sidebar
    global color, facet, height, names, boxwidth, points, log, remove_zero, start_at_one, font_size, xlabels, updated_default_dict, ref_line, show_meta_on_hover, multi_options, ylim_top, ylim_bottom, manually_set_ylim, log_ylim, ylim_values, annotate, agg_opts, show_axis_on_each, show_ylabel, show_line, boxmean, annotate_format, turn_xlabels, annotate_max, annotate_min, annotation_color, manually_set_y_to_show  # ,color_palette_list

    # updated_default_dict=set_values_from_url(default_dict)
    updated_default_dict = default_dict

    plot_settings = st.sidebar.expander("Plot Settings")
    plot_settings.subheader("Plot Widgets")
    # plot_settings.button("Reset Defaults",on_click=reset_all_defaults)
    multi_options = [None] + cols
    exclude_opts = [
        "Sample Elution",
        "Sample Dilution",
        "DNA Kit Extraction Factor",
        "Volume of DNA/well",
        "ml in Tube (before pellet)",
        "Normalization Factor",
        "Drop Assay Dilution",
        "PBS Dilution",
        "Amount of Powder (g)",
    ]
    agg_opts = [
        opt
        for opt in multi_options
        if opt in cols
        if len(df[opt].drop_duplicates()) > 1
        if opt not in exclude_opts
    ]
    if len(agg_opts) == 0:
        agg_opts = ["Average_by"]
    names_help = f"""Choose names of clumns the aggregate to represent a sample. \\
              See following example, where two samples have the same TreatmentName but other parameters are different\\
              ID | ExpID | TreatmentName \\
              M1 | RD001 | WetMatrix \\
              M2 | RD002 | WetMatrix \\
              If you choose all three columns, you will have two distinct names:\\
              'M1/RD001/WetMatrix' & 'M2/RD002/WetMatrix'. \\
              But if you only use TreatmentName column you will get one common name for both samples - 'WetMatrix' - then these samples will be averaged into one box."""
    names = plot_settings.multiselect(
        label="Name Samples By Chosen Columns",
        options=cols,
        default=agg_opts,
        key="names",
        help=names_help,
    )
    color_help = "Choose a column from the data to color the plots by."
    color = plot_settings.multiselect(
        label="Color",
        options=multi_options[1:],
        # index=multi_options.index(updated_default_dict["color"]),
        key="color",
        help=color_help,
    )

    # color_palette = plot_settings.selectbox(
    #     "Select Color Palette",
    #     options=dir(px.colors.qualitative),
    #     index=dir(px.colors.qualitative).index("Plotly"),
    # )
    # print(exec("px.colors.qualitative."+str(color_palette)))

    # print(color_palette_list)
    facet_help = "Choose a column to split the plots into subplot"
    facet = plot_settings.selectbox(
        label="Split Into Subplot",
        options=multi_options,
        index=multi_options.index(updated_default_dict["facet"]),
        key="facet",
        help=facet_help,
    )

    height = plot_settings.slider(
        label="Height",
        min_value=300,
        max_value=1200,
        value=int(updated_default_dict["height"]),
        step=50,
        key="height",
        help="Height of the plot",
    )
    font_size = plot_settings.slider(
        label="Font Size",
        min_value=1,
        max_value=25,
        value=int(updated_default_dict["font_size"]),
        key="font_size",
    )

    # temp_opts=cols
    # Choose columns by which to aggregate samples
    # Remove columns that only have one value

    boxwidth_help = "Relative space that the box takes - If the value is 1 each box will be connected to the box next to it, decreasing the value decreases the box width and increases the distance between adjacent boxes"
    boxwidth = plot_settings.slider(
        label="Box Width",
        min_value=0.1,
        max_value=1.0,
        value=float(updated_default_dict["boxwidth"]),
        step=0.1,
        key="boxwidth",
        help=boxwidth_help,
    )

    points_help = "Shows sample points on the plot next to the boxes. \n \
              \nTip: If points and plots overlap, you can play with the Box Width slider."
    points = plot_settings.checkbox(
        label="Show Points",
        key="show_points",
        value=updated_default_dict["points"],
        help=points_help,
    )
    xlabels = plot_settings.checkbox(
        label="Show X axis labels",
        key="xlabels",
        value=updated_default_dict["xlabels"],
        help="Show or hide X axis labels",
    )
    turn_xlabels = plot_settings.checkbox(
        label="Turn X axis labels",
        key="turn_xlabels",
        value=updated_default_dict["turn_xlabels"],
        help="Turn X axis labels by 90 degrees and split into multiple rows",
    )
    log = plot_settings.checkbox(
        label="Log Y Axis",
        key="logy",
        value=updated_default_dict["log"],
        help="When selected, Y axis is in log scale.",
    )
    start_at_one = plot_settings.checkbox(
        label="Start Axis at 1",
        key="start_at_one",
        value=updated_default_dict["start_at_one"],
        help="When selected, Y axis starts at 1",
    )  # disabled=True)
    # remove_zero=plot_settings.checkbox(label='Remove Zero Values',key='remove_zero', value=updated_default_dict['remove_zero'])
    plot_settings.markdown("---")
    manually_set_ylim_help = (
        "Select this checkbox to manually set the limits of the Y axis."
    )
    manually_set_ylim = plot_settings.checkbox(
        "Manually Set Y-Lim",
        value=False,
        key="manually_set_ylim",
        help=manually_set_ylim_help,
    )
    if manually_set_ylim:
        # ylim_bottom,ylim_top=plot_settings.slider(label='Manually set ylim (minimum and maximum)',min_value=-10.0,max_value=10.0,value=[-1.0,8.0],step=0.2,key='ylim')#format="10^%f")
        ylim_c1, ylim_c2 = plot_settings.columns(2)
        ylim_bottom = ylim_c1.number_input(
            label="Y-Limit Bottom",
            min_value=-15.00,
            max_value=15.00,
            value=-2.00,
            step=0.02,
            key="ylim_min",
        )
        ylim_top = ylim_c2.number_input(
            label="Y-Limit Bottom",
            min_value=-15.00,
            max_value=15.00,
            value=5.00,
            step=0.02,
            key="ylim_max",
        )
        plot_settings.markdown(
            "*If the chosen value is x, positive are 10^x, while negative x values are -10^x"
        )
    # ylim_bottom=plot_settings.slider(label='Manually set ylim (min)',min_value=-20,max_value=20,value=0)
    ylim_values = plot_settings.empty()
    plot_settings.markdown("---")

    remove_zero_help = "'Remove Zero Values Only When Not All Counts Are Zero' removes zeros only when some of the counts of the same sample equal to zero."
    remove_zero = plot_settings.selectbox(
        label="Remove Zero Values",
        options=[
            "Don't Remove Zero Values",
            "Remove Zero Values Only When Not All Counts Are Zero",
            "Remove All Zero Values",
        ],
        key="remove_zero",
        help=remove_zero_help,
    )
    ref_line_help = "When selected, a reference line is shown. In the % Survavability plot the line is at 100%, Delta plot reference line is set to 0."
    ref_line = plot_settings.checkbox(
        label="Draw Reference Line",
        key="ref_line",
        value=updated_default_dict["ref_line"],
        help=ref_line_help,
    )
    show_meta_on_hover = plot_settings.checkbox(
        "Show Metadata On Hover",
        key="show_meta_on_hover",
        value=True,
        help="Choose to show or not to show metadata of a sample upon hovering on the plot.",
    )
    show_axis_on_each = plot_settings.checkbox(
        label="Show Axis on Each Subplot",
        value=True,
        key="show_axis_on_each",
        help="When selected, shows Y axis values on each sub-plot. When not selected, shows only on the left sub-plot.",
    )
    show_ylabel = plot_settings.checkbox(
        label="Show Y-Label",
        value=True,
        help="Select to hide Y-axis Label.",
        key="show_y",
    )
    show_line_help = "When selected, a line is drawn between the averages of the same-colored plots. When multiple subplots are shown, the line is drawn within each subplot separately."
    show_line = plot_settings.checkbox(
        label="Connect a Line Between Same-Colored Boxes",
        value=False,
        help=show_line_help,
    )
    annotate_help = "Shows the selected metric (mean/median etc) in the top portion of the chart.\n\nAnnotations currently don't work together with 'facet'."
    annotate = plot_settings.selectbox(
        label="Show Annotations Above Plot",
        key="annotate",
        options=[
            None,
            "Mean",
            "Median",
            "Standart Deviation",
            "Standart Error Mean",
        ],
        help=annotate_help,
    )
    annotate_format_help = "Choose the format of the value shown."

    # if annotate:
    _, col = plot_settings.columns([1, 9])
    annotate_format = col.radio(
        label="Annotation Format",
        key="annotate_format",
        options=["Scientific", "Decimal", "%"],
        help=annotate_format_help,
        horizontal=True,
    )
    manually_set_y_to_show = plot_settings.selectbox(
        "Manually Set Value to show", ["Autoset", "Value", "% From Reference"]
    )
    annotate_max = plot_settings.checkbox(
        label="Show Max Value Above Box",
        key="annotate_max",
        # help=annotate_help,
    )
    annotate_min = plot_settings.checkbox(
        label="Show Min Value Above Box",
        key="annotate_min",
        # help=annotate_help,
    )
    annotation_color = plot_settings.color_picker("Annotation Color", "#000000")
    boxmean = plot_settings.selectbox(
        "Show on Box",
        options=["Mean and Median", "Mean, Median and SD", "Only Median"],
        key="boxmean",
    )


def statistics(df, value_to_use):
    statistic = st.selectbox(
        "Choose Statistic Test", options=["Mann Whitney U", "Kruskal Wallis"]
    )

    from itertools import combinations

    df_list = []
    for i, (name1, name2) in enumerate(combinations(df["custom_name"].unique(), 2)):
        if statistic == "Mann Whitney U":
            stat, p = mannwhitneyu(
                df[df["custom_name"] == name1][value_to_use].dropna().tolist(),
                df[df["custom_name"] == name2][value_to_use].dropna().tolist(),
            )
        elif statistic == "Kruskal Wallis":
            stat, p = kruskal(
                df[df["custom_name"] == name1][value_to_use].dropna().tolist(),
                df[df["custom_name"] == name2][value_to_use].dropna().tolist(),
            )
        df_list.append(
            [
                name1,
                name2,
                np.where(df["custom_name"].unique() == name1)[0][0],
                np.where(df["custom_name"].unique() == name2)[0][0],
                df[df["custom_name"] == name1][value_to_use].dropna().median(),
                df[df["custom_name"] == name1][value_to_use].dropna().mean(),
                df[df["custom_name"] == name2][value_to_use].dropna().median(),
                df[df["custom_name"] == name2][value_to_use].dropna().mean(),
                stat,
                p,
                # "ns" if p >= 0.05 else "YES",
                "ns"
                if p >= 0.05
                else "★"
                if p >= 0.01
                else "★★"
                if p >= 0.001
                else "★★★",
            ]
        )

    ag_df = pd.DataFrame(
        df_list,
        columns=[
            "Group 1",
            "Group 2",
            "I1",
            "I2",
            "Median 1",
            "Mean 1",
            "Median 2",
            "Mean 2",
            "Statistic",
            "P-Value",
            "Significant",
        ],
    )
    ag_df["Level"] = 1
    # move 'significant' column to the front
    ag_df = ag_df[
        ["Significant"] + [col for col in ag_df.columns if col != "Significant"]
    ]
    gb = GridOptionsBuilder.from_dataframe(ag_df)

    gb.configure_selection("multiple", use_checkbox=True)
    gb.configure_column("Level", editable=True)

    gridOptions = gb.build()

    st.write(
        "Select the p-values you want to add to the plot (only works when the plot is not split into subplots)"
    )
    manually_set_p_height = st.checkbox(
        "Manually set p-value height", value=False, key="manually_set_p_height"
    )
    if manually_set_p_height:
        st.write(
            "Edit the 'Level' column to change the height of the p-value shown (By double clicking and pressing Enter to accept)."
        )
    df_out = AgGrid(
        ag_df, gridOptions=gridOptions, columns_auto_size_mode="FIT_CONTENTS"
    )
    st.download_button(
        "Download statistics output as excel",
        data=to_excel(df_out.data),
        file_name="statistics_output.xlsx",
        mime="application/vnd.ms-excel",
    )
    p_to_add = []
    for i in df_out.selected_rows:
        p_to_add.append([i["I1"], i["I2"], i["Significant"], i["Level"]])
    return p_to_add, manually_set_p_height


def show_df(df, value_to_use):
    assert "custom_name" in df.columns, "custom_name column is missing"
    with st.expander("DataFrame"):
        df_to_show = (
            df.groupby("custom_name")
            .agg(
                {value_to_use: ["mean", "median", "std", "sem", "min", "max", "count"]}
            )
            .reset_index()
        )
        # remove multiindex for column names by merging them
        df_to_show.columns = df_to_show.columns.map("_".join)
        st.write(df_to_show)


def add_custom_name_column():
    df_filtered["custom_name"] = df_filtered[names].astype(str).agg("/".join, axis=1)


import io


def to_excel(df) -> bytes:
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1")
    writer.close()
    processed_data = output.getvalue()
    return processed_data


def st_plot_section():
    # Set up section where main cfu plot is shown
    st_figure = st.container()
    st_figure.markdown("---")

    st_figure.subheader("CFU Plot")
    exp_container = st_figure.container()
    # Plot
    plot_yaxis_label = st_figure.text_input(
        "Change Y-Axis Label (e.g. qPCR, CFU, Bacterial Counts)", value="CFU"
    )

    fig = boxplot(df_melt, "value", y_label=plot_yaxis_label)
    fig.update_layout(margin=dict(b=140))
    fig.update_layout(bg_dict)
    # st.write(fig.to_dict()["data"])

    import io

    buffer = io.StringIO()
    # html_bytes = BytesIO(buffer.getvalue().encode())
    fig.write_html(file=buffer, include_plotlyjs="cdn")
    st.download_button(
        "Download Current Plot as HTML",
        data=buffer.getvalue().encode(),
        file_name="plot.html",
    )
    stat_bool = st.checkbox("Show Statistic Test Results")
    if stat_bool:
        p_to_add, manually_set_p_height = statistics(df_melt, "value")
        add_p(fig, p_to_add, manually_set_p_height, exp_container)
    st_figure.plotly_chart(fig, use_container_width=True, theme=None)
    show_df(df_melt, "value")
    # st.write(df_melt)


def get_ylim(df, y, force_disable_axis_start_at_one, force_disable_log):
    # Get limit of y axis based on parameters
    if log and not force_disable_axis_start_at_one:
        max_val = np.log10(df[y].max()) + 1
        y_val = 10**max_val
        min_val = np.log10(df[y].min()) - 1
    else:
        max_val = df[y].max() * 1.1
        y_val = max_val
        if df[y].min() > 0:
            min_val = df[y].min() * 0.95
        else:
            min_val = df[y].min() * 1.05
    if manually_set_ylim:
        how_to_set_ylim = "manually"
        if (log) and (not force_disable_log):
            return [ylim_bottom, ylim_top, ylim_top, how_to_set_ylim]
        elif ylim_bottom != 0:
            return [
                int(ylim_bottom / abs(ylim_bottom)) * 10 ** abs(ylim_bottom),
                10**ylim_top,
                10**ylim_top,
                how_to_set_ylim,
            ]
        else:
            return [1, 10**ylim_top, 10**ylim_top, how_to_set_ylim]
    else:
        how_to_set_ylim = "automatically"
        if start_at_one and not force_disable_axis_start_at_one:
            return [0, max_val, y_val, how_to_set_ylim]
        elif not start_at_one:
            return [min_val, max_val, y_val, how_to_set_ylim]


def boxplot(
    df,
    y,
    ref_val=1,
    y_label=None,
    force_disable_log=False,
    force_disable_axis_start_at_one=False,
):
    groupby = ["custom_name"]
    if color:
        df["Color"] = df[color].astype(str).agg("|".join, axis=1)
        # df[color] = df[color].astype(str)
        groupby.append("Color")
    else:
        df["Color"] = "all"
    if facet:
        groupby.append(facet)

    if force_disable_log:
        logy = False
    else:
        logy = log
    fig = px.box(
        df,
        x="custom_name",
        y=y,
        # labels={
        #     "Experiment": True
        #     # "custom_name": "custom_name".replace("|", "<br>")
        #     # for i in df["custom_name"].unique()
        # },
        color="Color" if color else None if color else None if color else None,
        height=height,
        log_y=logy,
        facet_col=facet,
        facet_col_spacing=0.03,
        boxmode="overlay",
    )

    fig.update_xaxes(categoryarray=df["custom_name"].tolist())  # categoryorder="array",
    min_val, max_val, y_val, how_to_set_ylim = get_ylim(
        df, y, force_disable_axis_start_at_one, force_disable_log
    )
    if how_to_set_ylim == "automatically":
        ylim_values.markdown(f"Y Limits are {how_to_set_ylim} set")
    else:
        ylim_values.markdown(
            f"Y Limits are {how_to_set_ylim} set to {min_val:.3} and {max_val:.3}"
        )
    # change x label of each trace to custom_name but replace "|" with line break

    fig.update_layout(
        margin={"t": 100},
        yaxis_range=[min_val, max_val],
        font=dict(
            size=font_size,
        ),
        hovermode="x",
    )
    fig.for_each_annotation(
        lambda a: a.update(text=a.text.replace(str(facet) + "=", ""))
    )
    if boxmean == "Mean and Median":
        boxmean_val = True
    elif boxmean == "Mean, Median and SD":
        boxmean_val = "sd"
    elif boxmean == "Only Median":
        boxmean_val = None

    fig.update_traces(width=boxwidth, boxmean=boxmean_val)

    fig.update_xaxes(
        tickangle=90,
        matches=None,
        title=None,
        dtick=1,
        autorange=True,
        showticklabels=xlabels,
    )
    if turn_xlabels:
        names = dict(enumerate(df["custom_name"].unique()))
        for i in names.keys():
            names[i] = names[i].replace("|", "<br>")
        # st.write(st.session_state["names"])
        axis_text = "<br>".join(st.session_state["names"])

        # names1 = {v: v.replace("|", "<br>") for v in df["custom_name"].unique()}
        # st.write(names1)
        fig.update_xaxes(
            tickangle=0,
            tickvals=list(names.keys()),
            ticktext=list(names.values()),
            # labelalias=names1,
        )
        fig.add_annotation(
            x=0,
            y=0,
            xref="paper",
            yanchor="top",
            xanchor="center",
            yref="paper",
            text=axis_text,
            showarrow=False,
            font=dict(size=font_size),
        )
        # st.write(fig.data)

    if y_label and show_ylabel:
        label = y_label
    else:
        label = None
    fig.update_yaxes(
        exponentformat="E",
        title=label,
    )
    if show_axis_on_each:
        fig.update_yaxes(showticklabels=show_axis_on_each)

    if points:
        fig.update_traces(boxpoints="all", jitter=0.05, pointpos=-1.1)
    else:
        fig.update_traces(boxpoints="outliers")

    hover_plot = (
        px.bar(
            df,
            x="custom_name",
            y=[y_val] * len(df["custom_name"]),
            barmode="overlay",
            # histfunc="avg",
            # text_auto=".2e",
            hover_data=cols,
            facet_col=facet,
            log_y=log,
            color="Color" if color else None if color else None,
        )
        .update_traces(
            opacity=0,
            width=boxwidth,
            showlegend=False,
            textposition="outside",
        )
        .update_layout(yaxis_range=[0, max_val], uniformtext_minsize=8)
        .update_xaxes(matches=None)
    )

    if show_meta_on_hover:
        fig.add_traces(hover_plot.data)
    if annotate:
        agg_functions = {
            None: lambda x: x,
            "Mean": np.mean,
            "Median": np.median,
            "Standard Deviation": np.std,
            # "Standard Error Mean": np.sem,
        }
        agg_func = agg_functions[annotate]
        if manually_set_y_to_show == "Autoset":
            y_to_show = y
        elif manually_set_y_to_show == "% From Reference":
            y_to_show = "value_norm"
        elif manually_set_y_to_show == "Value":
            y_to_show = "value"
        annotations = iterate_categories_and_create_annotaitons(
            df_melt, y_to_show, agg_func, facet, yshift=0, color=annotation_color
        )
        for annotation in annotations:
            fig.add_annotation(annotation)
    if annotate_max:
        annotations = iterate_categories_and_create_annotaitons(
            df_melt,
            y,
            np.max,
            facet,
            yshift=10,
            y_loc="inplace",
            color=annotation_color,
        )
        for annotation in annotations:
            fig.add_annotation(annotation)
    if annotate_min:
        annotations = iterate_categories_and_create_annotaitons(
            df_melt,
            y,
            np.min,
            facet,
            yshift=-10,
            y_loc="inplace",
            color=annotation_color,
        )
        for annotation in annotations:
            fig.add_annotation(annotation)
    if ref_line:
        fig.add_hline(y=ref_val)

    if show_line:
        line_fig = px.line(
            df.groupby(groupby, sort=False, as_index=False).agg({y: "mean"}),
            x="custom_name",
            y=y,
            color="Color" if color else None,
            height=height,
            log_y=logy,
            facet_col=facet,
            facet_col_spacing=0.03,
        )
        line_fig.update_layout(showlegend=False)
        fig.add_traces(line_fig.data)

    show_lines_from_reference(fig, y)
    return fig.update_xaxes(matches=None)


def iterate_categories_and_create_annotaitons(
    df, value_col, agg_func, facet_chose, y_loc="top", yshift=0, color="black"
):
    ann = []
    groupby_cols = [facet_chose, "custom_name"] if facet_chose else ["custom_name"]
    agg_df = df.reset_index().groupby(groupby_cols)[value_col].agg(agg_func).to_frame()
    if facet_chose:
        for i, variable in enumerate(df[facet_chose].unique()):
            for target_category, value in agg_df.loc[(variable,)].itertuples(name=None):
                ann.append(
                    dict(
                        x=target_category,
                        y=1.0
                        if y_loc == "top"
                        else np.log10(value),  # np.log10(value),
                        xref="x" + str(i + 1),
                        yref="paper" if y_loc == "top" else "y" + str(i + 1),
                        text=f"{value:.2e}"
                        if annotate_format == "Scientific"
                        else (
                            f"{value:,.2f}"
                            if annotate_format == "Decimal"
                            else f"{value:.2f}%"
                        ),
                        font=dict(color=color),
                        showarrow=False,
                        ax=40,
                        yshift=yshift,
                    )
                )
    else:
        for target_category, value in agg_df.itertuples(name=None):
            ann.append(
                dict(
                    x=target_category,
                    y=1.0 if y_loc == "top" else np.log10(value),  # np.log10(value),
                    xref="x",
                    yref="paper" if y_loc == "top" else "y",
                    text=f"{value:.2e}"
                    if annotate_format == "Scientific"
                    else (
                        f"{value:,.2f}"
                        if annotate_format == "Decimal"
                        else f"{value:,.2f}%"
                    ),
                    font=dict(color=color),
                    showarrow=False,
                    ax=40,
                    yshift=yshift,
                )
            )
    return ann


def barplot(
    df,
    y,
    ref_val=1,
    y_label=None,
    force_disable_log=False,
    force_disable_axis_start_at_one=False,
):
    groupby = ["custom_name"]
    if color:
        df[color] = df[color].astype(str)
        groupby.append(color)
    if facet:
        groupby.append(facet)
    if force_disable_log:
        logy = False
    else:
        logy = log

    fig = px.bar(
        df.groupby(groupby, sort=False, as_index=False).agg({y: "mean"}),
        x="custom_name",
        y=y,
        color="Color" if color else None,
        height=height,
        log_y=logy,
        facet_col=facet,
        facet_col_spacing=0.03,
        barmode="overlay",
    )
    min_val, max_val, y_val, how_to_set_ylim = get_ylim(
        df, y, force_disable_axis_start_at_one, force_disable_log
    )
    if how_to_set_ylim == "automatically":
        ylim_values.markdown(f"Y Limits are {how_to_set_ylim} set")
    else:
        ylim_values.markdown(
            f"Y Limits are {how_to_set_ylim} set to {min_val:.3} and {max_val:.3}"
        )

    fig.update_layout(
        yaxis_range=[min_val, max_val],
        font=dict(
            size=font_size,
        ),
        hovermode="x",
    )
    # fig.update_traces(width=boxwidth,)
    fig.update_xaxes(
        tickangle=90,
        matches=None,
        title=None,
        dtick=1,
        autorange=True,
        showticklabels=xlabels,
    )
    if y_label and show_ylabel:
        label = y_label
    else:
        label = None
    fig.update_yaxes(
        exponentformat="E",
        title=label,
    )
    if show_axis_on_each:
        fig.update_yaxes(showticklabels=show_axis_on_each)

    # if points:
    #        fig.update_traces(boxpoints='all',jitter=0.05)
    # else:
    #        fig.update_traces(boxpoints=False)

    hover_plot = px.box(
        df,
        x="custom_name",
        y=[y_val] * len(df["custom_name"]),
        boxmode="overlay",
        hover_data=cols,
        facet_col=facet,
        log_y=log,
        color="Color" if color else None,
    )
    hover_plot.update_traces(width=boxwidth, opacity=0, showlegend=False)
    hover_plot.update_layout(yaxis_range=[0, max_val])

    if show_meta_on_hover:
        fig.add_traces(hover_plot.data)
    if ref_line:
        fig.add_hline(y=ref_val)
    if annotate:
        ann = []
        for i, val in enumerate(
            list(
                df_melt.groupby(["custom_name"], sort=False, as_index=False)
                .agg({"value": "mean"})
                .round(2)["value"]
            )
        ):
            ann.append(
                dict(
                    x=i,
                    y=1.05,
                    text=f"{val:.2}",
                    showarrow=False,
                    xref="x",
                    yref="paper",
                )
            )
        fig.layout.annotations = ann
    return fig


def show_lines_from_reference(fig, y):
    with st.sidebar.expander("Add verticle lines"):
        lines_from = st.radio("Show lines from", options=["Value", "Sample"])
        if lines_from == "Value":
            ref_value = st.number_input("Input ref value")
        if lines_from == "Sample":
            ref_sample_for_hlines = st.selectbox(
                "Select Sample", df_melt["custom_name"].unique().tolist()
            )
            ref_sample_value_type = st.radio(
                "Value Type", ["Mean", "Median", "Min", "Max"]
            )
            if ref_sample_value_type == "Mean":
                ref_value = (
                    df_melt.groupby(by="custom_name")[y]
                    .mean()
                    .loc[ref_sample_for_hlines]
                )
            elif ref_sample_value_type == "Median":
                ref_value = (
                    df_melt.groupby(by="custom_name")[y]
                    .median()
                    .loc[ref_sample_for_hlines]
                )
            elif ref_sample_value_type == "Min":
                ref_value = (
                    df_melt.groupby(by="custom_name")[y]
                    .min()
                    .loc[ref_sample_for_hlines]
                )
            elif ref_sample_value_type == "Max":
                ref_value = (
                    df_melt.groupby(by="custom_name")[y]
                    .max()
                    .loc[ref_sample_for_hlines]
                )
            st.write(f"Ref Value is {ref_value}")
        # reference_to_show_lines_from = st.selectbox("Reference to show line from", options = df_filtered["custom_name"].unique().tolist())
        show_lines_from_ref = st.multiselect(
            "Show lines from reference",
            options=[100, 75, 50, 25, 10, 1, 0.1, 0.01],
            key="show_lines_from_ref",
        )
        for line in show_lines_from_ref:
            fig.add_hline(y=ref_value * line / 100)
            fig.add_annotation(
                text=str(line) + "%",
                x=0.999,
                yshift=10,
                y=np.log10(ref_value * line / 100) if log else ref_value * line / 100,
                xref="paper",
                showarrow=False,
                yref="y",
            )


def choose_reference():
    global ref_value, y_norm  # ,y_ref_excluded,y_ref_excluded_log
    st.markdown("---")
    st_choose_ref_sample = st.sidebar.expander("Choose Reference Sample")
    st_choose_ref_sample.subheader("Choose Reference Sample")
    choose_ref_sample_help = "Choose which sample to use as reference for the calculation for % survavability."
    choose_ref_sample = st_choose_ref_sample.selectbox(
        label="Reference Sample",
        options=df_filtered["custom_name"].unique(),
        key="ref_sample",
        help=choose_ref_sample_help,
    )
    choose_ref_type_help = (
        "Choose wheter to use the mean/median/max/min value from the reference sample"
    )
    choose_ref_type = st_choose_ref_sample.selectbox(
        label="Min/Max/Mean/Median",
        options=[
            "Mean",
            "Median",
            "Min",
            "Max",
        ],
        key="ref_sample_type",
        help=choose_ref_type_help,
    )

    # ref_opts=df_filtered[df_filtered['custom_name'].isin([choose_ref_sample])][y_variables]
    ref_opts = df_melt[df_melt["custom_name"] == choose_ref_sample]["value"]
    if choose_ref_type == "Min":
        ref_value = ref_opts.min()
    elif choose_ref_type == "Max":
        ref_value = ref_opts.max()
    elif choose_ref_type == "Median":
        ref_value = ref_opts.median()
    elif choose_ref_type == "Mean":
        ref_value = ref_opts.mean()
    st_choose_ref_sample.markdown(
        f"Reference value is set to the {choose_ref_type} value of '{choose_ref_sample}'. \n\n Chosen reference value is {ref_value:.4}"
    )
    update_df_melt_according_to_ref()


def percent_survaviability_plot_section():
    st.markdown("---")
    st_survivability = st.container()
    st_survivability.subheader("% Survivability Plot")
    st_survivability.markdown("Uses the reference sample chosen in the sidebar.")

    # Plot % out of reference plot
    fig = boxplot(df_melt, "value_norm", ref_val=100, y_label="% Survivability")

    stat_bool = st.checkbox("Show Statistic Test Results")
    if stat_bool:
        p_to_add, manually_set_p_height = statistics(df_melt, "value_norm")
        add_p(fig, p_to_add, manually_set_p_height)
    st_survivability.plotly_chart(fig, use_container_width=True, theme=None)
    show_df(df_melt, "value_norm")


def ref_excluded_plot_section():
    st.markdown("---")
    st_delta_plot = st.container()
    st_delta_plot.subheader("Delta From Reference")
    st_delta_plot.markdown(
        "Referece subtracted from the rest of the values. Uses the reference sample chosen in the sidebar."
    )

    # Plotting, force disable log and force disable start at one.
    if log:
        data = "value_delta_ref_log"
    else:
        data = "value_delta_ref"
    fig2 = boxplot(
        df_melt,
        data,
        y_label="Log Delta",
        ref_val=0,
        force_disable_log=True,
        force_disable_axis_start_at_one=True,
    )
    stat_bool = st.checkbox("Show Statistic Test Results")
    if stat_bool:
        p_to_add, manually_set_p_height = statistics(df_melt, data)
        add_p(fig2, p_to_add, manually_set_p_height)
    st_delta_plot.plotly_chart(fig2, use_container_width=True, theme=None)
    show_df(df_melt, data)


def auto_ref_excluded_plot_section():
    st.markdown("---")
    st_auto_delta_plot = st.container()
    st_auto_delta_plot.subheader("Delta From Reference (auto-set)")
    # st_auto_delta_plot.markdown("Referece subtracted from the rest of the values. Uses the reference sample chosen in the sidebar.")
    st_auto_delta_plot.markdown("Consult Alon before using this plot.")

    # Plotting, force disable log and force disable start at one.
    if log:
        data = "value_delta_auto_ref_log"
    else:
        data = "value_delta_auto_ref"
    fig3 = boxplot(
        df_melt,
        data,
        y_label="Log Delta",
        ref_val=0,
        force_disable_log=True,
        force_disable_axis_start_at_one=True,
    )
    # fig4 = barplot(
    #     df_melt,
    #     data,
    #     y_label="Log Delta",
    #     ref_val=0,
    #     force_disable_log=True,
    #     force_disable_axis_start_at_one=True,
    # )
    delta_auto_set = st_auto_delta_plot.checkbox(
        "I consulted Alon and I want to see this plot"
    )
    if delta_auto_set:
        stat_bool = st.checkbox("Show Statistic Test Results")
        if stat_bool:
            p_to_add, manually_set_p_height = statistics(df_melt, data)
            add_p(fig3, p_to_add, manually_set_p_height)
        st_auto_delta_plot.plotly_chart(fig3, use_container_width=True, theme=None)
        show_df(df_melt, data)
        # st_auto_delta_plot.subheader("Bar Chart Using Only Mean Value")
        # st_auto_delta_plot.plotly_chart(fig4, use_container_width=True, theme=None)


def auto_assign_ref_sample():
    default_columns_for_ref = [
        x
        for x in agg_opts
        if x not in ["TimePoint", "TestedAgent", "TestedAgentDilution"]
    ]
    auto_ref = st.sidebar.expander("Auto Assign Reference Sample (Consult Alon)")
    ref_columns_help = "'Columns to take for reference' should be the same columns as taken for the plot names, excluding TestedAgent and TestedAgentDilution. As well as excluding the column by which the reference is determined."
    ref_columns = auto_ref.multiselect(
        "Columns to take for reference",
        options=cols,
        default=default_columns_for_ref,
        help=ref_columns_help,
    )
    df_melt["ref_name"] = df_melt[ref_columns].astype(str).agg("/".join, axis=1)
    if "TimePoint" in df_melt.columns:
        tp = list(df_melt.columns).index("TimePoint")
    else:
        tp = 0
    col_for_ref = auto_ref.selectbox(
        "Choose column to search reference by", options=list(df_melt.columns), index=tp
    )
    if "t0" in df_melt[col_for_ref].unique().tolist():
        val_t0 = list(df_melt[col_for_ref].unique().tolist()).index("t0")
    else:
        val_t0 = 0
    val_for_ref = auto_ref.selectbox(
        "Choose column to search reference by",
        options=df_melt[col_for_ref].unique().tolist(),
        index=val_t0,
    )

    ref_for_each_sample_type = (
        df_melt[df_melt[col_for_ref] == val_for_ref]
        .groupby(by=["ref_name"])
        .agg({"value": "mean"})
    )
    auto_ref.markdown("Chosen References:")
    auto_ref.write(ref_for_each_sample_type.astype(str))
    df_melt["auto_ref_sample"] = df_melt["ref_name"].map(
        ref_for_each_sample_type.to_dict()["value"]
    )
    df_melt["value_delta_auto_ref"] = df_melt["value"] - df_melt["auto_ref_sample"]
    df_melt["value_delta_auto_ref_log"] = np.log10(
        df_melt["value"] / df_melt["auto_ref_sample"],
        where=(df_melt["value"] / df_melt["auto_ref_sample"] != 0),
    )


def update_parameters_in_link():
    st.experimental_set_query_params(
        color=st.session_state.color,
        facet=st.session_state.facet,
        annotate=st.session_state.annotate,
        # ref_sample=st.session_state.ref_sample,
        ref_sample_type=st.session_state.ref_sample_type,
        height=st.session_state.height,
        font_size=st.session_state.font_size,
        boxwidth=st.session_state.boxwidth,
        ylim=st.session_state.ylim,
        points=st.session_state.show_points,
        xlabels=st.session_state.xlabels,
        log=st.session_state.logy,
        start_at_one=st.session_state.start_at_one,
        remove_zero=st.session_state.remove_zero,
        ref_line=st.session_state.ref_line,
        show_meta_on_hover=st.session_state.show_meta_on_hover,
        manually_set_ylim=st.session_state.manually_set_ylim,
        #        # names=st.session_state.names,
        #        # **widget_dict
    )
    # st.sidebar.write(experimental_get_query_params())


def set_values_from_url(url_params):
    # st.sidebar.write(st.experimental_get_query_params())
    # for val in st.experimental_get_query_params().keys():
    #        if val in st.session_state.keys():
    #               st.session_state[val]=st.experimental_get_query_params()[val]
    selectbox_widgets = [
        "color",
        "facet",
        "annotate",
        "ref_sample",
        "ref_sample_type",
        "remove_zero",
    ]
    for widget in selectbox_widgets:
        if widget in url_params.keys():
            if url_params[widget][0] == "None":
                val = None
            else:
                val = url_params[widget][0]
            st.session_state[widget] = val

    int_slider_widgets = ["height", "font_size"]
    for widget in int_slider_widgets:
        if widget in url_params.keys():
            st.session_state[widget] = int(url_params[widget][0])

    float_slider_widgets = ["boxwidth", "ylim"]
    for widget in float_slider_widgets:
        if widget in url_params.keys():
            if widget == "ylim":
                st.session_state[widget] = [
                    float(url_params[widget][0]),
                    float(url_params[widget][1]),
                ]
            else:
                st.session_state[widget] = float(url_params[widget][0])

    bool_widgets = [
        "points",
        "xlabels",
        "log",
        "start_at_one",
        "ref_line",
        "show_meta_on_hover",
        "manually_set_ylim",
    ]
    for widget in bool_widgets:
        if widget in url_params.keys():
            if str(url_params[widget][0]) == False:
                val = False
            else:
                val = True
            st.session_state[widget] = val


def save_and_upload_settings():
    from json import dumps, loads
    from time import strftime

    global save_and_use_settings
    save_and_use_settings = st.sidebar.expander(
        "Save Current Settings Or Upload Saved Settings"
    )
    settings_to_download = {
        k: v
        for k, v in st.session_state.items()
        if "button" not in k and "file_uploader" not in k and "FormSubmitter" not in k
    }
    custom_filename = save_and_use_settings.text_input(
        label="Choose name for the settings file",
        placeholder="Leave blank to use current date and time as the file name.",
        value="",
    )
    add_date_to_name = save_and_use_settings.checkbox(
        "Add date and time to filename", value=True
    )
    if add_date_to_name:
        timeanddate = strftime("%Y%m%d-%H%M%S")
    else:
        timeanddate = ""
    settings_filename = timestr = (
        str(timeanddate) + " " + str(custom_filename) + str(".json")
    )
    save_and_use_settings.download_button(
        label="Save Current Settings as a File",
        data=dumps(settings_to_download, default=str),
        file_name=settings_filename,
    )
    save_and_use_settings.markdown("---")

    upload_settings_widget = save_and_use_settings.file_uploader(
        label="Upload Previously Saved Settings File",
        type=["json"],
        accept_multiple_files=False,
    )

    if upload_settings_widget:
        uploaded_settings = loads(upload_settings_widget.getvalue())
        failed = []
        succeeded = []
        button_apply_uploaded_settings = save_and_use_settings.button(
            "Apply Settings",
            on_click=apply_uploaded_settings,
            args=(uploaded_settings,),
        )


def apply_uploaded_settings(json_settings):
    failed = []
    succeeded = []
    for k, v in json_settings.items():
        try:
            st.session_state[k] = v
            succeeded.append(k)
        except:
            failed.append(k)
    save_and_use_settings.success(
        f"Successfully uploaded {str(len(succeeded))} out of {str(len(succeeded)+len(failed))} settings"
    )
    if len(failed) > 0:
        save_and_use_settings.error(
            f"Failed to upload the following settings: {failed}"
        )


def add_p(fig, array_cols, manually_set_p_height, container=st.container()):
    # test = container.checkbox("Test new UI for height of P value")
    # from streamlit_vertical_slider import vertical_slider
    # cont=container.columns(len(array_cols) if len(array_cols)>0 else 1)

    h0 = 1.02
    hdif = 0.04
    for z, [ind1, ind2, symbol, level] in enumerate(array_cols):
        if manually_set_p_height:
            z = float(level)
        #     if test:

        #         # for i in array_cols:
        # #             #verticle slider to set height
        #             with cont[int(z)]:
        #                 z = vertical_slider( key = f"vs_{ind1}_{ind2}",
        #                     default_value=z,
        #                     step=0.5,
        #                     min_value=-10,
        #                     max_value=5,)
        #                 st.write(f"{ind1}_vs_{ind2}")
        #     else:
        #         level1 = level

        #     h = 1 + (0.04 * float(level1 if level1 else level))
        fig.add_shape(
            type="line",
            yref="paper",
            x0=ind1 + 0.02,
            y0=h0 + z * hdif,
            x1=ind2 - 0.02,
            y1=h0 + z * hdif,
        )
        fig.add_shape(
            type="line",
            yref="paper",
            x0=ind1 + 0.02,
            y0=h0 + z * hdif,
            x1=ind1 + 0.02,
            y1=h0 + z * hdif - 0.01,
        )
        fig.add_shape(
            type="line",
            yref="paper",
            x0=ind2 - 0.02,
            y0=h0 + z * hdif,
            x1=ind2 - 0.02,
            y1=h0 + z * hdif - 0.01,
        )

        fig.add_annotation(
            x=(ind1 + ind2) / 2,
            text=symbol,
            y=h0 + z * hdif,
            yanchor="bottom",
            yref="paper",
            font_size=12,
            showarrow=False,
        )


def plotly_white_theme():
    global bg_dict
    plotly_white = st.sidebar.checkbox(
        "Use White Plot Background", value=False, key="plotly_white_theme"
    )
    if plotly_white:
        pio.templates.default = "plotly_white"
        bg_dict = {
            "plot_bgcolor": "rgba(0, 0, 0, 0)",
            "paper_bgcolor": "rgba(0, 0, 0, 0)",
        }
    else:
        bg_dict = {}


def main():
    # Main part of the app
    # st.sidebar.button("Get Parameters from URL",on_click=set_values_from_url)
    # url_params=st.experimental_get_query_params()
    # set_values_from_url(url_params)
    st_header_section()
    st_template_download()
    st_file_upload_section()

    if upload_data_widget:
        load_dataframe()
    if loaded:
        add_logo_and_links_to_sidebar()
        get_filters_and_add_widgets_to_sidebar(df)
        add_df_sort_settings_to_sidebar()
        add_plot_settings_to_sidebar()

        # set_values_from_url()
        # update_parameters_in_link()
        filter_data()
        choose_reference()

        auto_assign_ref_sample()
        save_and_upload_settings()
        st_data_section()
        plotly_white_theme()

        st.markdown("---")
        st.subheader("Figures")
        choose_plot = st.radio(
            "Choose which plot you want to see:",
            options=[
                "Regular CFU Plot",
                "% Survivability Plot",
                "Delta From Reference",
                "Delta from Auto-Set Reference",
            ],
            horizontal=True,
        )
        if choose_plot == "Regular CFU Plot":
            st_plot_section()
        elif choose_plot == "% Survivability Plot":
            percent_survaviability_plot_section()
        elif choose_plot == "Delta From Reference":
            ref_excluded_plot_section()
        elif choose_plot == "Delta from Auto-Set Reference":
            try:
                auto_ref_excluded_plot_section()
            except Exception as e:
                st.text("Could not do auto-assign reference :(")
                st.warning(e)
        else:
            st.warning("Something went wrong")

        # st.sidebar.write(dict(st.session_state))

        # st.sidebar.write(st.session_state)
        # st.sidebar.button("Set Parameters in URL",on_click=update_parameters_in_link)
        # st.sidebar.markdown("After setting parameters in the URL you can copy it and save it. Next time you can use the fill link and most parameters will be saved (not including filters).")
        # update_parameters_in_link()


if __name__ == "__main__":
    main()

# %%
