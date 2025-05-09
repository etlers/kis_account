import plotly.express as px
import polars as pl

df = pl.read_csv(
    './data/log_data_20250509.csv',
    schema_overrides={
        "DTM": pl.Utf8,
        "PRC": pl.Int64,
    }
)

fig = px.line(df, x='DTM', y='PRC', title='인터랙티브 추세 그래프')
fig.show()