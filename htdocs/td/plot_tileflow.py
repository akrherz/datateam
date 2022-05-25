"""Plot!"""
# pylint: disable=abstract-class-instantiated
import sys
import datetime

import pandas as pd
import numpy as np
from paste.request import parse_formvars
from pyiem.util import get_sqlalchemy_conn

sys.path.append("/opt/datateam/htdocs/td")
from common import CODES, getColor, send_error, COPYWRITE

LINESTYLE = [
    "-",
    "-",
    "-",
    "-",
    "-",
    "-",
    "-",
    "-",
    "-.",
    "-.",
    "-.",
    "-.",
    "-.",
    "-",
    "-.",
    "-.",
    "-.",
    "-.",
    "-.",
    "-.",
    "-.",
    "-.",
    "-.",
    "-.",
]
BYCOL = {
    "daily": "day",
    "weekly": "week",
    "monthly": "month",
    "yearly": "year",
}


def get_weather(uniqueid, sts, ets):
    """Retreive the daily precipitation"""
    # Convert ids
    with get_sqlalchemy_conn("td") as conn:
        df = pd.read_sql(
            "SELECT date, precipitation from weather_data "
            "WHERE siteid = %s and date >= %s and date <= %s "
            "ORDER by date ASC",
            conn,
            index_col="date",
            params=(uniqueid, sts.date(), ets.date()),
        )
    df.index = pd.DatetimeIndex(df.index.values)
    df["ticks"] = (
        df.index.values.astype("datetime64[ns]").astype(np.int64) // 10**6
    )
    return df


def make_plot(form, start_response):
    """Make the plot"""
    uniqueid = form.get("site", "ISUAG")

    sts = datetime.datetime.strptime(
        form.get("date", "2014-01-01"), "%Y-%m-%d"
    )
    days = int(form.get("days", 1))
    ungroup = int(form.get("ungroup", 0))
    ets = sts + datetime.timedelta(days=days)
    wxdf = get_weather(uniqueid, sts, ets)
    by = form.get("by", "daily")
    with get_sqlalchemy_conn("td") as conn:
        df = pd.read_sql(
            f"SELECT date_trunc('{BYCOL[by]}', date)::date as v, "
            "coalesce(plotid, location) as datum, sum(discharge) as discharge "
            "from tile_flow_and_n_loads_data WHERE siteid = %s "
            "and date between %s and %s GROUP by v, datum ORDER by v ASC",
            conn,
            params=(uniqueid, sts.date(), ets.date()),
        )
    if len(df.index) < 3:
        send_error(start_response, "js", "No / Not Enough Data Found, sorry!")
    linecol = "datum"
    if ungroup == 0:
        # Generate the plotid lookup table
        with get_sqlalchemy_conn("td") as conn:
            plotdf = pd.read_sql(
                "SELECT * from meta_plot_identifier where siteid = %s",
                conn,
                params=(uniqueid,),
                index_col="plotid",
            )

        def lookup(row):
            """Lookup value."""
            try:
                return plotdf.loc[row["datum"], "dwm_treatment"]
            except KeyError:
                return row["datum"]

        df["treatment"] = df.apply(lookup, axis=1)
        del df["datum"]
        df = df.groupby(["treatment", "v"]).mean()
        df = df.reset_index()
        linecol = "treatment"

    # Begin highcharts output
    start_response("200 OK", [("Content-type", "application/javascript")])
    title = f"Tile Flow for {uniqueid} ({sts:%-d %b %Y} to {ets:%-d %b %Y})"
    s = []
    plot_ids = df[linecol].unique()
    plot_ids.sort()
    if ungroup == "0":
        plot_ids = plot_ids[::-1]
    df["ticks"] = pd.to_datetime(df["v"]).astype(np.int64) // 10**6
    seriestype = "line" if by in ["daily"] else "column"
    for i, plotid in enumerate(plot_ids):
        df2 = df[df[linecol] == plotid]
        if df2.empty:
            continue
        s.append(
            (
                """{type: '"""
                + seriestype
                + """',
            """
                + getColor(plotid, i)
                + """,
            name: '"""
                + CODES.get(plotid, plotid)
                + """',
            data: """
                + str(
                    [
                        [a, b]
                        for a, b in zip(
                            df2["ticks"].values, df2["discharge"].values
                        )
                    ]
                )
                + """
        }"""
            )
            .replace("None", "null")
            .replace("nan", "null")
        )
    if not wxdf.empty:
        s.append(
            (
                """{type: 'column',
            name: 'Precip',
            color: '#0000ff',
            yAxis: 1,
            data: """
                + str(
                    [
                        [a, b]
                        for a, b in zip(
                            wxdf["ticks"].values, wxdf["precipitation"].values
                        )
                    ]
                )
                + """
        }"""
            )
            .replace("None", "null")
            .replace("nan", "null")
        )
    series = ",".join(s)
    res = (
        """
$("#hc").highcharts({
    """
        + COPYWRITE
        + """
    title: {text: '"""
        + title
        + """'},
    chart: {zoomType: 'x'},
    yAxis: [
        {title: {text: 'Discharge (mm)'}},
        {title: {text: 'Daily Precipitation (mm)'},
         reversed: true,
         maxPadding: 1,
         opposite: true},
    ],
    plotOptions: {
        line: {turboThreshold: 0},
        series: {
            cursor: 'pointer',
            allowPointSelect: true,
            point: {
                events: {
                    click: function() {
                        editPoint(this);
                    }
                }
            }
        }
    },
    xAxis: {
        type: 'datetime'
    },
    tooltip: {
        dateTimeLabelFormats: {
            hour: "%b %e %Y, %H:%M",
            minute: "%b %e %Y, %H:%M"
        },
        shared: true,
        valueDecimals: 0,
        valueSuffix: ' mm'
    },
    series: ["""
        + series
        + """]
});
    """
    )
    return res.encode("utf-8")


def application(environ, start_response):
    """Do Something"""
    form = parse_formvars(environ)
    return [make_plot(form, start_response)]
