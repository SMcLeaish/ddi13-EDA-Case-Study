from pathlib import Path

import altair as alt
import polars as pl


class CitiesStations:
    def __init__(
        self, country: str, cities_csv: Path | str, stations_csv: Path | str
    ):
        self.cities: pl.LazyFrame = pl.scan_csv(cities_csv)
        self.stations: pl.LazyFrame = pl.scan_csv(stations_csv)
        self.country: str = country
        self.ldf: pl.LazyFrame = self._build_ldf()
        self.df: pl.DataFrame | None = None

    def _build_ldf(self) -> pl.LazyFrame:
        return (
            self.filter_cities_by_country(self.cities, self.country)
            .pipe(lambda ldf: self.join_on_city_id(self.stations, ldf))
            .pipe(self.rename_name_right_to_city)
            .pipe(self.rename_buildstart_to_start)
            .pipe(self.drop_empty_country_rows)
            .pipe(self.drop_empty_start)
            .pipe(self.change_start_to_datetime)
        )

    def _collect_df(
        self, ldf: pl.LazyFrame, reset: bool = True
    ) -> pl.DataFrame:
        if reset or self.df is None:
            self.df = ldf.collect()
        return self.df

    def show_graph(self) -> None:
        self.ldf.show_graph()

    def _start_count(self) -> pl.LazyFrame:
        return (
            self.ldf.group_by(['city', 'start'])
            .agg(pl.len())
            .sort(['city', 'start'])
            .with_columns(
                pl.col('len').cum_sum().over('city').alias('cumulative')
            )
        )

    def filter_cities_by_country(
        self, ldf: pl.LazyFrame, country: str
    ) -> pl.LazyFrame:
        return ldf.filter(pl.col('country') == country)

    def join_on_city_id(
        self, left_ldf: pl.LazyFrame, right_ldf: pl.LazyFrame
    ) -> pl.LazyFrame:
        return left_ldf.join(
            right_ldf, left_on='city_id', right_on='id', how='left'
        )

    def drop_empty_country_rows(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.drop_nulls(subset='country')

    def rename_buildstart_to_start(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.rename({'buildstart': 'start'})

    def rename_name_right_to_city(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.rename({'name_right': 'city'})

    def drop_empty_start(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.filter(pl.col('start') > 0)

    def change_start_to_datetime(self, ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.with_columns(
            pl.datetime(pl.col('start'), 1, 1).alias('date_start')
        )

    def line_chart(self, file: str | None = None) -> alt.Chart:
        ldf = self._start_count()
        df = self._collect_df(ldf)
        chart: alt.Chart = df.plot.line(
            x='start', y='cumulative', color='city'
        )
        if file:
            chart.save(file)  # type: ignore
        return chart

    def histogram(
        self, stacked: bool = False, file: str | None = None
    ) -> alt.Chart:
        df = self._collect_df(self.ldf)
        chart = (
            alt.Chart(df)
            .mark_bar(  # type: ignore
            )
            .encode(
                x=alt.X(
                    'start:Q',
                    bin={'maxbins': 20},
                    axis=alt.Axis(format='d', title='Year'),
                ),
                y=alt.Y(
                    'count()',
                    stack='zero',
                    axis=alt.Axis(title='Numer of Stations Built'),
                ),
            )
            .properties(title='Urban Rail Built in the US 1832-Present')
        )

        if stacked:
            chart = chart.encode(color=alt.Color('city:N'))

        if file:
            chart.save(file)  # type: ignore
        return chart
