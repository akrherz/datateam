"""This is our fancy pants download function

select string_agg(column_name, ', ') from
    (select column_name, ordinal_position from information_schema.columns where
    table_name='management' ORDER by ordinal_position) as foo;
"""
import sys
import os
import re
import datetime
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from paste.request import parse_formvars
import pandas as pd
from pandas.io.sql import read_sql
import numpy as np
from pyiem.util import get_dbconn

VARNAME_RE = re.compile(r"^[A-Z]+[0-9]$")
EMAILTEXT = """
Sustainable Corn CAP - Research and Management Data
Requested: %s UTC
Website: https://datateam.agron.iastate.edu/cscap/
Contact: sustainablecorn@iastate.edu

Please click here to download your spreadsheet file.

    %s (link will remain active for 30 days)

Please reference this data set in publications as:

Abendroth, Lori J., Daryl E. Herzmann, Giorgi Chighladze, Eileen J. Kladivko,
Matthew J. Helmers, Laura Bowling, Michael Castellano, Richard M. Cruse,
Warren A. Dick, Norman R. Fausey, Jane Frankenberger, Aaron J. Gassmann,
Alexandra Kravchenko, Rattan Lal, Joseph G. Lauer, Daren S. Mueller,
Emerson D. Nafziger, Nsalambi Nkongolo, Matthew O'Neal, John E. Sawyer,
Peter Scharf, Jeffrey S. Strock, and Maria B. Villamil. 2017.
Sustainable Corn CAP Research Data (USDA-NIFA Award No. 2011-68002-30190).
National Agricultural Library - ARS - USDA.
https://dx.doi.org/10.15482/USDA.ADC/1411953

You are encouraged to contact the Sustainable Corn CAP personnel listed above
to ensure proper data interpretation and may also consider co-authoring
with them. You shall have no claim of ownership to any intellectual
property rights in any part of the data, content, functions, features,
code, data exploration tools, logos or other intellectual property
comprising this database.

The coauthors individually and the Sustainable Corn CAP collectively
shall NOT be responsible or liable for the accuracy, reliability and
completeness of any information included in the database nor for the
suitability of its application for a particular purpose. Data users
are encouraged to notify the coauthors regarding data quality
and other issues concerning the data, tools, and functionality of this
website. Contact sustainablecorn@iastate.edu with any questions or concerns
regarding usage and application of the data available at this site.

"""

FERTELEM = [
    "nitrogen",
    "phosphorus",
    "phosphate",
    "potassium",
    "potash",
    "sulfur",
    "calcium",
    "magnesium",
    "zinc",
    "iron",
]
KGH_LBA = 1.12085

# runtime storage
MEMORY = dict(stamp=datetime.datetime.utcnow())


def get_vardf(pgconn, tabname):
    """Get a dataframe of descriptors for this tabname"""
    return read_sql(
        """
        select element_or_value_display_name as varname,
        number_of_decimal_places_to_round_up::numeric::int as round,
        short_description, units from data_dictionary_export WHERE
        spreadsheet_tab = %s
    """,
        pgconn,
        params=(tabname,),
        index_col="varname",
    )


def replace_varname(varname):
    """We want varname to be zero padded, where appropriate"""
    if VARNAME_RE.match(varname):
        return "%s0%s" % (varname[:-1], varname[-1])
    return varname


def pprint(msg):
    """log a pretty message for my debugging fun"""
    utcnow = datetime.datetime.utcnow()
    delta = (utcnow - MEMORY["stamp"]).total_seconds()
    MEMORY["stamp"] = utcnow
    sys.stderr.write("timedelta: %.3f %s\n" % (delta, msg))


def valid2date(df):
    """If dataframe has valid in columns, rename it to date"""
    if "valid" in df.columns:
        df.rename(columns={"valid": "date"}, inplace=True)


def conv(value, detectlimit):
    """Convert a value into something that gets returned"""
    # Careful here, we need to keep missing values for a later replacement
    if value is None or value == "":
        return None
    if value in ["n/a", "did not collect"]:
        return None
    if value.startswith("<"):
        if detectlimit == "1":
            return value
        floatval = float(value[1:])
        if detectlimit == "2":
            return floatval / 2.0
        if detectlimit == "3":
            return floatval / 2 ** 0.5
        if detectlimit == "4":
            return "M"
    try:
        return float(value)
    except Exception:
        return value


def do_dictionary(pgconn, writer):
    """Add Data Dictionary to the spreadsheet"""
    df = read_sql(
        "SELECT * from data_dictionary_export ORDER by ss_order ASC",
        pgconn,
        index_col=None,
    )
    for col in ["ss_order", "number_of_decimal_places_to_round_up"]:
        df.drop(col, axis=1, inplace=True)
    df.to_excel(writer, "Data Dictionary", index=False)
    # Increase column width
    worksheet = writer.sheets["Data Dictionary"]
    worksheet.set_column("A:D", 36)
    worksheet.set_column("E:E", 18)
    worksheet.set_column("F:F", 36)
    worksheet.set_column("G:J", 12)
    worksheet.set_column("K:K", 60)


def do_metadata_master(pgconn, writer, sites, missing):
    """get Metadata master data"""
    df = read_sql(
        """
    SELECT uniqueid,
    nwlon as "NW Lon", nwlat as "NW Lat", swlon as "SW Lon", swlat as "SW Lat",
    selon as "SE Lon", selat as "SE Lat", nelon as "NE Lon", nelat as "NE Lat",
    rawlonlat as "raw LonLat", state, county, city as "city",
    landscapeslope as "landscape slope",
    tilespacing as "tile spacing",
    tiledepth as "tile depth",
    sitearea as "site area",
    numberofplots as "number of plots"
    from metadata_master
    WHERE uniqueid in %s
    ORDER by uniqueid
    """,
        pgconn,
        params=(tuple(sites),),
        index_col=None,
    )
    df.replace(["None", None, ""], np.nan, inplace=True)
    df.dropna(how="all", inplace=True)
    df.fillna(missing, inplace=True)
    df, worksheet = add_bling(
        pgconn, writer, df, "Site Metadata", "Site Metadata"
    )
    worksheet.set_column("A:A", 12)
    worksheet.set_column("L:R", 12)


def do_ghg(pgconn, writer, sites, ghg, missing):
    """get GHG data"""
    cols = ", ".join(['%s as "%s"' % (s, s) for s in ghg])
    df = read_sql(
        f"""
    SELECT d.uniqueid, d.plotid, d.date, d.year, d.method, d.subsample,
    d.position, {cols}
    from ghg_data d JOIN plotids p on (d.uniqueid = p.uniqueid and
    d.plotid = p.plotid)
    WHERE (p.herbicide != 'HERB2' or p.herbicide is null)
    and d.uniqueid in %s
    ORDER by d.uniqueid, year, date, plotid
    """,
        pgconn,
        params=(tuple(sites),),
        index_col=None,
    )
    df.fillna(missing, inplace=True)
    df, worksheet = add_bling(pgconn, writer, df, "GHG", "GHG")
    worksheet.set_column("C:C", 12)


def do_ipm(pgconn, writer, sites, ipm, missing):
    """get IPM data"""
    cols = ", ".join(ipm)
    df = read_sql(
        f"""
    SELECT d.uniqueid, d.plotid, d.date, d.year, {cols}
    from ipm_data d JOIN plotids p on (d.uniqueid = p.uniqueid and
    d.plotid = p.plotid)
    WHERE (p.herbicide != 'HERB2' or p.herbicide is null) and
    d.uniqueid in %s
    ORDER by d.uniqueid, year, date, plotid
    """,
        pgconn,
        params=(tuple(sites),),
        index_col=None,
    )
    df.fillna(missing, inplace=True)
    df.columns = [s.upper() if s.startswith("ipm") else s for s in df.columns]
    df, worksheet = add_bling(pgconn, writer, df, "IPM", "IPM")
    worksheet.set_column("C:C", 12)


def do_agronomic(pgconn, writer, sites, agronomic, detectlimit, missing):
    """get agronomic data"""
    df = read_sql(
        """
    SELECT d.uniqueid, d.plotid, d.varname, d.year, d.value
    from agronomic_data d JOIN plotids p on (d.uniqueid = p.uniqueid and
    d.plotid = p.plotid)
    WHERE (p.herbicide != 'HERB2' or p.herbicide is null) and
    d.uniqueid in %s and varname in %s
    ORDER by uniqueid, year, plotid
    """,
        pgconn,
        params=(tuple(sites), tuple(agronomic)),
        index_col=None,
    )
    df["value"] = df["value"].apply(lambda x: conv(x, detectlimit))
    df = pd.pivot_table(
        df,
        index=("uniqueid", "plotid", "year"),
        values="value",
        columns=("varname",),
        aggfunc=lambda x: " ".join(str(v) for v in x),
    )
    # fix column names
    df.columns = map(replace_varname, df.columns)
    vardf = get_vardf(pgconn, "Agronomic")
    for colname in df.columns:
        places = 0
        if colname in vardf.index.values:
            places = vardf.at[colname, "round"]
        df[colname] = pd.to_numeric(df[colname], errors="coerce")
        df[colname] = df[colname].apply(
            (
                lambda x: round(x, int(places))
                if isinstance(x, (int, float))
                else x
            )
        )
    # reorder columns
    cols = df.columns.values.tolist()
    cols.sort()
    df = df.reindex(cols, axis=1)
    # String aggregate above creates a mixture of None and "None"
    df.replace(["None", None], np.nan, inplace=True)
    df.dropna(how="all", inplace=True)
    df.fillna(missing, inplace=True)
    df.reset_index(inplace=True)
    valid2date(df)
    df, _worksheet = add_bling(pgconn, writer, df, "Agronomic", "Agronomic")


def add_bling(pgconn, writer, df, sheetname, tabname):
    """Do fancy things"""
    # Insert some headers rows
    metarows = [{}, {}]
    cols = df.columns
    vardf = get_vardf(pgconn, tabname)
    for i, colname in enumerate(cols):
        if i == 0:
            metarows[0][colname] = "description"
            metarows[1][colname] = "units"
            continue
        if colname in vardf.index:
            metarows[0][colname] = vardf.at[colname, "short_description"]
            metarows[1][colname] = vardf.at[colname, "units"]
    df = pd.concat([pd.DataFrame(metarows), df], ignore_index=True)
    # re-establish the correct column sorting
    df = df.reindex(cols, axis=1)
    df.to_excel(writer, sheetname, index=False)
    worksheet = writer.sheets[sheetname]
    worksheet.freeze_panes(3, 0)
    return df, worksheet


def do_soil(pgconn, writer, sites, soil, detectlimit, missing):
    """get soil data"""
    # pprint("do_soil: " + str(soil))
    # pprint("do_soil: " + str(sites))
    # pprint("do_soil: " + str(years))
    df = read_sql(
        """
    SELECT d.uniqueid, d.plotid, d.depth,
    coalesce(d.subsample, '1') as subsample, d.varname, d.year, d.value,
    coalesce(d.sampledate::text, '') as sampledate
    from soil_data d JOIN plotids p ON (d.uniqueid = p.uniqueid and
    d.plotid = p.plotid)
    WHERE (p.herbicide != 'HERB2' or p.herbicide is null) and
    d.uniqueid in %s and varname in %s
    ORDER by uniqueid, year, plotid, subsample
    """,
        pgconn,
        params=(tuple(sites), tuple(soil)),
        index_col=None,
    )
    pprint("do_soil() query done")
    df["value"] = df["value"].apply(lambda x: conv(x, detectlimit))
    pprint("do_soil() value replacement done")
    df = pd.pivot_table(
        df,
        index=(
            "uniqueid",
            "plotid",
            "depth",
            "subsample",
            "year",
            "sampledate",
        ),
        values="value",
        columns=("varname",),
        aggfunc=lambda x: " ".join(str(v) for v in x),
    )
    # fix column names
    df.columns = map(replace_varname, df.columns)
    vardf = get_vardf(pgconn, "Soil")
    for colname in df.columns:
        places = 0
        if colname in vardf.index.values:
            places = vardf.at[colname, "round"]
        if pd.isnull(places):
            continue
        df[colname] = pd.to_numeric(df[colname], errors="ignore")
        df[colname] = df[colname].apply(
            (
                lambda x: round(x, int(places))
                if isinstance(x, (int, float))
                else x
            )
        )
    # reorder columns
    cols = df.columns.values.tolist()
    cols.sort()
    df = df.reindex(cols, axis=1)
    # String aggregate above creates a mixture of None and "None"
    df.replace(["None", None], np.nan, inplace=True)
    pprint("do_soil() len of inbound df %s" % (len(df.index)))
    df.dropna(how="all", inplace=True)
    df.fillna(missing, inplace=True)
    pprint("do_soil() len of outbound df %s" % (len(df.index)))
    pprint("do_soil() pivot_table done")
    df.reset_index(inplace=True)
    df["sampledate"] = df["sampledate"].replace("", missing)
    valid2date(df)
    pprint("do_soil() valid2date done")
    df, worksheet = add_bling(pgconn, writer, df, "Soil", "Soil")
    pprint("do_soil() to_excel done")
    workbook = writer.book
    format1 = workbook.add_format({"num_format": "@"})
    worksheet.set_column("B:B", 12, format1)


def do_operations(pgconn, writer, sites, missing):
    """Return a DataFrame for the operations"""
    opdf = read_sql(
        """
    SELECT uniqueid, cropyear, operation, valid, cashcrop, croprot,
    plantryemethod, planthybrid, plantmaturity, plantrate, plantrateunits,
    terminatemethod, biomassdate1, biomassdate2, depth, limerate,
    manuresource, manuremethod, manurerate,
    manurerateunits, fertilizerform, fertilizercrop, fertilizerapptype,
    fertilizerformulation, productrate, nitrogenelem, phosphoruselem,
    potassiumelem, sulfurelem, zincelem, magnesiumelem, ironelem, calciumelem,
    stabilizer, stabilizerused, stabilizername, comments,
    -- These are deleted below
    nitrogen, phosphorus, phosphate, potassium,
    potash, sulfur, calcium, magnesium, zinc, iron
    from operations where uniqueid in %s
    ORDER by uniqueid ASC, cropyear ASC, valid ASC
    """,
        pgconn,
        params=(tuple(sites),),
    )
    opdf["productrate"] = pd.to_numeric(opdf["productrate"], errors="coerce")
    for fert in FERTELEM:
        opdf[fert] = pd.to_numeric(opdf[fert], errors="coerce")
    for col in ["biomassdate1", "biomassdate2", "valid"]:
        opdf.at[opdf[col].isnull(), col] = missing

    # __________________________________________________________
    # case 1, values are > 0, so columns are in %
    df = opdf[opdf["productrate"] > 0]
    for elem in FERTELEM:
        opdf.loc[df.index, elem] = (
            df["productrate"] * KGH_LBA * df[elem] / 100.0
        )
    opdf.loc[df.index, "productrate"] = df["productrate"] * KGH_LBA

    # ________________________________________________________
    # case 2, value is -1 and so columns are in lbs / acre
    df = opdf[opdf["productrate"] < 0]
    opdf.loc[df.index, "productrate"] = None
    for elem in FERTELEM:
        opdf.loc[df.index, elem] = df[elem] * KGH_LBA
        del opdf[elem]
    valid2date(opdf)
    del opdf["productrate"]
    opdf, worksheet = add_bling(
        pgconn, writer, opdf, "Field Operations", "Field Operations"
    )
    worksheet.set_column("C:C", 18)
    worksheet.set_column("D:D", 12)
    worksheet.set_column("M:N", 12)


def do_management(pgconn, writer, sites):
    """Return a DataFrame for the management"""
    opdf = read_sql(
        """
    SELECT uniqueid, cropyear, notill, irrigation, irrigationamount,
    irrigationmethod, residueremoval, residuehow, residuebiomassweight,
    residuebiomassmoisture, residueplantingpercentage, residuetype,
    limeyear, comments
    from management where uniqueid in %s
    ORDER by cropyear ASC
    """,
        pgconn,
        params=(tuple(sites),),
    )
    opdf.to_excel(writer, "Residue, Irrigation", index=False)


def do_pesticides(pgconn, writer, sites):
    """Return a DataFrame for the pesticides"""
    opdf = read_sql(
        """
    SELECT uniqueid, cropyear, operation, valid, timing, method,
    cropapplied,
    cashcrop, totalrate, pressure,
    product1, rate1, rateunit1,
    product2, rate2, rateunit2,
    product3, rate3, rateunit3,
    product4, rate4, rateunit4,
    adjuvant1, adjuvant2, comments
    from pesticides where uniqueid in %s and
    operation != 'seed'
    ORDER by uniqueid ASC, cropyear ASC, valid ASC
    """,
        pgconn,
        params=(tuple(sites),),
    )
    valid2date(opdf)
    opdf, worksheet = add_bling(
        pgconn, writer, opdf, "Pesticides", "Pesticides"
    )
    worksheet.set_column("D:D", 12)


def do_plotids(pgconn, writer, sites):
    """Write plotids to the spreadsheet"""
    opdf = read_sql(
        """
        SELECT uniqueid, rep, plotid, tillage, rotation,
        drainage, nitrogen, landscape,
        y2011 as "2011crop", y2012 as "2012crop", y2013 as "2013crop",
        y2014 as "2014crop", y2015 as "2015crop",
        agro as "agro_data", soil as "soil_data",
        ghg as "ghg_data", ipmcscap as "ipmcscap_data",
        ipmusb as "ipmusb_data",
        soilseriesname1,
        lower(soiltextureseries1) as soiltextureseries1,
        soilseriesdescription1,
        soiltaxonomicclass1,
        soilseriesname2,
        lower(soiltextureseries2) as soiltextureseries2,
        soilseriesdescription2,
        soiltaxonomicclass2,
        soilseriesname3,
        lower(soiltextureseries3) as soiltextureseries3,
        soilseriesdescription3,
        soiltaxonomicclass3,
        soilseriesname4,
        lower(soiltextureseries4) as soiltextureseries4,
        soilseriesdescription4,
        soiltaxonomicclass4
        from plotids p LEFT JOIN xref_rotation x on (p.rotation = x.code)
        where uniqueid in %s and
        (herbicide != 'HERB2' or herbicide is null)
        ORDER by uniqueid, plotid ASC
    """,
        pgconn,
        params=(tuple(sites),),
    )
    opdf, worksheet = add_bling(
        pgconn,
        writer,
        opdf[opdf.columns],
        "Plot Identifiers",
        "Plot Identifiers",
    )
    # Make plotids as strings and not something that goes to dates
    workbook = writer.book
    format1 = workbook.add_format({"num_format": "0"})
    worksheet.set_column("B:B", 12, format1)


def do_notes(pgconn, writer, sites, missing):
    """Write notes to the spreadsheet"""
    opdf = read_sql(
        """
        SELECT "primary" as uniqueid, overarching_data_category, data_type,
        replace(growing_season, '.0', '') as growing_season,
        comments
        from highvalue_notes where "primary" in %s
        ORDER by "primary" ASC, overarching_data_category ASC, data_type ASC,
        growing_season ASC
    """,
        pgconn,
        params=(tuple(sites),),
    )
    opdf.replace(["None", None, ""], np.nan, inplace=True)
    opdf.dropna(how="all", inplace=True)
    opdf.fillna(missing, inplace=True)
    opdf[opdf.columns].to_excel(writer, "Notes", index=False)
    # Increase column width
    worksheet = writer.sheets["Notes"]
    worksheet.set_column("B:B", 36)
    worksheet.set_column("C:D", 18)
    worksheet.set_column("E:G", 36)


def do_dwm(pgconn, writer, sites, missing):
    """Write dwm to the spreadsheet"""
    opdf = read_sql(
        """
        SELECT uniqueid, plotid, cropyear, cashcrop, boxstructure,
        outletdepth, outletdate, comments
        from dwm where uniqueid in %s
        ORDER by uniqueid ASC, cropyear ASC
    """,
        pgconn,
        params=(tuple(sites),),
    )
    opdf.replace(["None", None, ""], np.nan, inplace=True)
    opdf.dropna(how="all", inplace=True)
    opdf.fillna(missing, inplace=True)
    _df, worksheet = add_bling(
        pgconn,
        writer,
        opdf[opdf.columns],
        "Drainage Control Structure Mngt",
        "Drainage Control Structure Mngt",
    )
    worksheet.set_column("G:G", 12)
    worksheet.set_column("H:H", 30)


def do_work(form):
    """do great things"""
    pgconn = get_dbconn("td")
    email = form.get("email")
    sites = form.getall("sites[]")
    if not sites:
        sites.append("XXX")
    agronomic = form.getall("agronomic[]")
    soil = form.getall("soil[]")
    ghg = form.getall("ghg[]")
    # water = form.getall('water[]')
    ipm = form.getall("ipm[]")
    shm = form.getall("shm[]")
    missing = form.get("missing", "M")
    if missing == "__custom__":
        missing = form.get("custom_missing", "M")
    pprint("Missing is %s" % (missing,))
    detectlimit = form.get("detectlimit", "1")

    # pylint: disable=abstract-class-instantiated
    writer = pd.ExcelWriter("/tmp/td.xlsx", engine="xlsxwriter")

    # First sheet is Data Dictionary
    if "SHM5a" in shm:
        do_dictionary(pgconn, writer)
        pprint("do_dictionary() is done")

    # Sheet two is plot IDs
    if "SHM4a" in shm:
        do_plotids(pgconn, writer, sites)
        pprint("do_plotids() is done")

    # Measurement Data
    if agronomic:
        do_agronomic(pgconn, writer, sites, agronomic, detectlimit, missing)
        pprint("do_agronomic() is done")
    if soil:
        do_soil(pgconn, writer, sites, soil, detectlimit, missing)
        pprint("do_soil() is done")
    if ghg:
        do_ghg(pgconn, writer, sites, ghg, missing)
        pprint("do_ghg() is done")
    if ipm:
        do_ipm(pgconn, writer, sites, ipm, missing)
        pprint("do_ipm() is done")

    # Management
    # Field Operations
    if "SHM1a" in shm:
        do_operations(pgconn, writer, sites, missing)
        pprint("do_operations() is done")
    # Pesticides
    if "SHM2a" in shm:
        do_pesticides(pgconn, writer, sites)
        pprint("do_pesticides() is done")
    # Residue and Irrigation
    if "SHM3a" in shm:
        do_management(pgconn, writer, sites)
        pprint("do_management() is done")
    # Site Metadata
    if "SHM8a" in shm:
        do_metadata_master(pgconn, writer, sites, missing)
        pprint("do_metadata_master() is done")
    # Drainage Management
    if "SHM7a" in shm:
        do_dwm(pgconn, writer, sites, missing)
        pprint("do_dwm() is done")
    # Notes
    if "SHM6a" in shm:
        do_notes(pgconn, writer, sites, missing)
        pprint("do_notes() is done")

    # Send to client
    writer.close()
    msg = MIMEMultipart()
    msg["Subject"] = "Transforming Drainage Dataset"
    msg["From"] = "ISU Data Team <isudatateam@iastate.edu>"
    msg["To"] = email
    msg.preamble = "Data"
    # conservative limit of 8 MB
    # if os.stat('/tmp/cscap.xlsx').st_size > 8000000:
    tmpfn = ("td_%s.xlsx") % (
        datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S"),
    )
    shutil.copyfile("/tmp/td.xlsx", "/var/webtmp/%s" % (tmpfn,))
    uri = "https://datateam.agron.iastate.edu/tmp/%s" % (tmpfn,)
    text = EMAILTEXT % (
        datetime.datetime.utcnow().strftime("%d %B %Y %H:%M:%S"),
        uri,
    )

    msg.attach(MIMEText(text))

    _s = smtplib.SMTP("localhost")
    _s.sendmail(msg["From"], msg["To"], msg.as_string())
    _s.quit()
    os.unlink("/tmp/td.xlsx")
    cursor = pgconn.cursor()
    cursor.execute(
        "INSERT into website_downloads(email) values (%s)", (email,)
    )
    cursor.close()
    pgconn.commit()
    pprint("is done!!!")
    return b"Email Delivered!"


def application(environ, start_response):
    """Do Stuff"""
    form = parse_formvars(environ)
    agree = form.get("agree")
    start_response("200 OK", [("Content-type", "text/plain")])
    if agree != "AGREE":
        return [b"You did not agree to download terms."]

    return [do_work(form)]
