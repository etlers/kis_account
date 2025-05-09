import com_func as CF
import polars as pl

df = pl.read_csv(
    './data/log_data_20250509.csv',
    schema_overrides={
        "DTM": pl.Utf8,
        "PRC": pl.Int64,
    }
)

buy_prc = 11610 * 1.005
print(buy_prc)

filtered_df = df.filter(pl.col("PRC") > buy_prc)
print(filtered_df)
filtered_df = filtered_df.filter(pl.col("DTM") > '20250509 132200')
print(filtered_df)