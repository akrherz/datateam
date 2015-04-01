'''
 Scrape out the Soil Texture data from Google Drive
'''
import util
import sys
import gdata.docs.client
import ConfigParser
import psycopg2

YEAR = sys.argv[1]

config = ConfigParser.ConfigParser()
config.read('mytokens.cfg')

pgconn = psycopg2.connect(database='sustainablecorn',
                          host=config.get('database', 'host'))
pcursor = pgconn.cursor()

# Get me a client, stat
spr_client = util.get_spreadsheet_client(config)
docs_client = util.get_docs_client(config)

allowed_depths = ['0 - 10', '10 - 20', '20 - 40', '40 - 60']

query = gdata.docs.client.DocsQuery(show_collections='false',
                                    title='Soil Texture Data')
feed = docs_client.GetAllResources(query=query)

for entry in feed:
    if entry.get_resource_type() != 'spreadsheet':
        continue
    spreadsheet = util.Spreadsheet(docs_client, spr_client, entry)
    spreadsheet.get_worksheets()
    if YEAR not in spreadsheet.worksheets:
        print(("Missing %s from %s"
               ) % (YEAR, spreadsheet.title))
        continue
    worksheet = spreadsheet.worksheets[YEAR]
    worksheet.get_cell_feed()
    siteid = spreadsheet.title.split()[0]
    print 'Processing %s Soil Texture Year %s' % (siteid, YEAR),
    if (worksheet.get_cell_value(1, 1) != 'plotid' or
        worksheet.get_cell_value(1, 2) != 'depth'):
        print 'FATAL site: %s soil nitrate has corrupt headers' % (siteid,)
        continue
    for row in range(4,worksheet.rows+1):
        plotid = worksheet.get_cell_value(row, 1)
        depth = worksheet.get_cell_value(row, 2)
        #if depth not in allowed_depths:
        #    print 'site: %s year: %s has illegal depth: %s' % (siteid, YEAR,
        #                                                       depth)
        #    continue
        if plotid is None or depth is None:
            continue
        subsample = "1"
        for col in range(3, worksheet.cols+1):
            varname = worksheet.get_cell_value(1,col).strip().split()[0]
            val = worksheet.get_cell_value(row, col)
            if varname == 'subsample':
                subsample = val
                continue
            elif varname[:4] != 'SOIL':
                print 'Invalid varname: %s site: %s year: %s' % (
                                    worksheet.get_cell_value(1,col).strip(),
                                    siteid, YEAR)
                continue
            if subsample != "1":
                continue
            try:
                pcursor.execute("""
                    INSERT into soil_data(site, plotid, varname, year, 
                    depth, value, subsample)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """, (siteid, plotid, varname, YEAR, depth, val, subsample))
            except Exception, exp:
                print 'HARVEST_SOIL_TEXTURE TRACEBACK'
                print exp
                print '%s %s %s %s %s' % (siteid, plotid, varname, depth, val,
                                          subsample)
                sys.exit()
    print "...done"
pcursor.close()
pgconn.commit()
pgconn.close()
