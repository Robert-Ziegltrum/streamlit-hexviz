import streamlit_hexviz as shv
import streamlit as st
import pandas as pd

import geopandas as gpd

st.write("## Earthquakes with  geopandas")
st.write("Example for loading geopandas into h3 map.")

df = pd.read_csv("data/earthquakes.csv")

# 2. Convert to GeoDataFrame with Point geometry
data = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
    crs="EPSG:4326",  # Standard WGS 84 latitude/longitude coordinate system
)
# dropping existing lat and lon column. Otherwise h3_map creates a warning.
data = data.drop(columns=["latitude", "longitude"])
shv.h3_map(data)

st.info("use the navigation: recommended options: color: heat, transform log.")

st.code(
    """
        import streamlit_hexviz as shv
        import streamlit as st
        import pandas as pd

        import geopandas as gpd

        st.write("## Earthquakes with  geopandas")
        st.write("example for the utilization of pre-indexed h3 data sets")

        df = pd.read_csv("data/earthquakes.csv")

        # 2. Convert to GeoDataFrame with Point geometry
        data = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
            crs="EPSG:4326",  # Standard WGS 84 latitude/longitude coordinate system
        )

shv.h3_map(data)

""",
    language="python",
)

st.info(
    "Despite using csv loads for this example, this pattern can be very well used for loads for e.g. a database."
)
