from pathlib import Path

import altair as alt
import polars as pl


class CitiesStations:
    def __init__(
        self,
        cities_csv: Path | str = '../data/cities.csv',
        stations_csv: Path | str = '../data/stations.csv',
        country: str = 'United States',
    ):
        self.cities: pl.LazyFrame = pl.scan_csv(cities_csv)
        self.stations: pl.LazyFrame = pl.scan_csv(stations_csv)
        self.country: str = country
        self.ldf: pl.LazyFrame = self._build_ldf()
        self.df: pl.DataFrame | None = None

    def _build_ldf(self) -> pl.LazyFrame:
        return (
            self._filter_cities_by_country(self.cities, self.country)
            .pipe(lambda ldf: self._join_on_city_id(self.stations, ldf))
            .pipe(self._rename_name_right_to_city)
            .pipe(self._rename_buildstart_to_start)
            .pipe(self._drop_empty_country_rows)
            .pipe(self._drop_empty_start)
            .pipe(self._change_start_to_datetime)
        )

    def show_graph(self) -> None:
        self.ldf.show_graph()

    def line_chart(self, file: str | None = None) -> alt.Chart:
        ldf = self._start_count()
        df = self._collect_df(ldf)
        chart: alt.Chart = df.plot.line(
            x='start', y='cumulative', color='city'
        )
        if isinstance(file, str):
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

    def _collect_df(
        self, ldf: pl.LazyFrame, reset: bool = True
    ) -> pl.DataFrame:
        if reset or self.df is None:
            self.df = ldf.collect()
        return self.df

    def _start_count(self) -> pl.LazyFrame:
        return (
            self.ldf.group_by(['city', 'start'])
            .agg(pl.len())
            .sort(['city', 'start'])
            .with_columns(
                pl.col('len').cum_sum().over('city').alias('cumulative')
            )
        )

    @staticmethod
    def _filter_cities_by_country(
        ldf: pl.LazyFrame, country: str
    ) -> pl.LazyFrame:
        return ldf.filter(pl.col('country') == country)

    @staticmethod
    def _join_on_city_id(
        left_ldf: pl.LazyFrame, right_ldf: pl.LazyFrame
    ) -> pl.LazyFrame:
        return left_ldf.join(
            right_ldf, left_on='city_id', right_on='id', how='left'
        )

    @staticmethod
    def _drop_empty_country_rows(ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.drop_nulls(subset='country')

    @staticmethod
    def _rename_buildstart_to_start(ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.rename({'buildstart': 'start'})

    @staticmethod
    def _rename_name_right_to_city(ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.rename({'name_right': 'city'})

    @staticmethod
    def _drop_empty_start(ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.filter(pl.col('start') > 0)

    @staticmethod
    def _change_start_to_datetime(ldf: pl.LazyFrame) -> pl.LazyFrame:
        return ldf.with_columns(
            pl.datetime(pl.col('start'), 1, 1).alias('date_start')
        )
