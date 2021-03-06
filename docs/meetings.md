DataTeam Meeting Notes
======================

24 Sep 2019 :: Lori, Gio, Steph, Sam

- isudatateam google site has a job board I should review.
- TD website work is scheduled December thru Feb 2020.
- Look into the Agricultural Research Data Network.

  4 Apr 2017
  Gio, Lori, Katie
  - Katie's last day with our group is next week, so we shall do lunch
  - [ ] Add windspeed and RH% values to climodat
  - [ ] make free drainage always appear first on plots
  - [ ] Merge CLAY sites on the plotting, retain uniqueids in legend
  - [ ] repurpose the CSCAP export for TD
  - [ ] aggregate nitrogen application by year to get totals by crop
  - [ ] generate a report of missing data within TD database
  - [ ] plot of percentage of time drainage is in a certain mode

 28 Feb 2017
  Gio, Lori
  - There is a pending three week deadline to get TD work done
  - [ ] Gio has a Export Data Tool List doc with the groupings I need for dl
  - Discussion on doing Gio's time shifting to fix the problems with timestamps
  - [ ] Edit on the TD tools does not work :/
  - [ ] There are examples of duplicated times in the water table data
  - Gio's metadata sheets have per year drainage status by plot id
  - [ ] work on drainflow first.

 20 Dec 2016
  Gio, Lori, Suresh, Katie
  - This is Suresh's last meeting :(
  - Lots of discussion about missing ICASA variables and how we can ask AgMIP
    for guidance on what to do with the unknown variables
  - Need to throw this all at AgMIP eventually with details on our protocols
    and units, etc
  - Dr Arbuckle will be adding some additional variables to the dictionary 
    of the social-economic data, where appropriate
  - TD data upload deadline looms and hopefully more data shows up soon
  - Suggestion to implement more comments in the backend data sheets when data
    is modified.  daryl can track this lifecycle
  - [ ] convert all the DMS lat/lon values into decimal in the history sheet

  2 Nov 2016
  Gio, Lori
  - I am on the TD modelling list, so I should get meeting announcements
  - next TD team meeting is next wednesday at 2
  - [ ] implement CSCAP's editing on the TD charts
  - [ ] syncing between CSCAP to TD data stores
  - [x] take UBWC out of the TD water table plotting
  - we should email around action items from workgroup calls
  - [ ] need to bubble up the CSCAP weather observations!  Then TD too
  - [x] send Gio TD database connection details

 19 Jul 2016
  Steph, Lori, Suresh, Gio
  - `planthybrid` is a poor term for non-corn plants
  - [x] duplicated cash crop entries in management tab will cause issues
  - n/a for cashcrop for fall 2015 operations is OK
  - [ ] consolidate the weather stations listed to collapse site ids
  - [ ] do year comparisons of other soil variables
  - Gio has new plot ids setup for NAEW sites, simplified things greatly
  - [ ] write Gio and tell him that his NAEW work is awesomely awesome
  - [ ] write and run script that checks units found on various pages
  - [ ] create water retention plots
  - next meeting 1 PM, 3 Aug
 
 10 Jun 2016
  Lori, Gio, Suresh
  - Gio's got a Google Form cronjob that is modifying the form each hour
  - unsure yet how to handle the SOC issues at MASON and KELLOGG
  - Hope is to upload to NAL sometime in Feb or Mar
  - Talked about download form, it is okay for the filter to work in one
    direction and not worry about going backwards
  - Add rows to exported sheet from the protocol smartsheet columns
    - TD project has site specific ones in this case
  - [ ] deal with the embedded notes in the sheets now that Google Sheets v4
    is out and available
  - [x] Add Gio on github to datateam repo
  - setup Gio for direct database access for his R code
  - [ ] Rectifiy any CSCAP management changes since the copy to TD sheet
  - Backend metadata sheet can not sort the updated date column, sigh
  - International Drainage Symposium is in September
  - Next meeting is 29 June

 28 Apr 2016
  Lori, Gio, Suresh, Katie
  - Lori reported on her Globus meeting, most of the folks there were HPC
  - We are encouraged to register for the digitial Ag meeting 16-17 May
  - [x] I showed the new data editing, Lori wanted the text changed
  - [x] modify highcharts pages to use fullpage bootstrap template
  - Our next meeting is 18 May
 
 19 Apr 2016
  Lori, Gio, Suresh
  - Purpose is to discuss Gio's data download thoughts
  - [ ] When I email the team a listing of text, the result is not pretty on 
    their end
  - [ ] need to again review the IPM plotids for Suresh and resend email
  - Lori discussed Syngenta meeting, interested in 4mon/yr coordinator
  - [x] ISUAG.USB is not in download form
  - Gio's interface wants drill down with things getting enabled / grayed out
  - [ ] Allow for deselect of sites when a full state is selected/unselected
  - All variables on by default for Agro/Soils
  - Divide output into multiple tabs
  - Is the year filter at the end problematic?  Likely not.

  6 Apr 2016
  Lori, Gio, Suresh, Katie
  - Discussion on what will happen with the writing worshop and perhaps there
    would be time for us to work on it some
  - Volume 5 of the primary reports for the project is coming from us
  - Katie has been working on some survey data from Dr Morton that will 
    eventually come to the db
  - Discussion of the failure to take the team photo at the TD Project Meeting
  - Getting the soil data sheets generated for TD is a priority, but we do
    not know enough yet to generate them (like depths)
  - Gio wants auto-sync setup for the drainage sheets
  - Discussion about the STJOHNS elevation difference issue
  - TD has three tiers for data: Required, Recommended, and Optional
  - We have a pressing need to get the weather data processed
  - [ ] Would like to see precipitation on the plots by 15 Apr
  - source of weather data included on the plot and download
  - Inclusion of the management data for weirs height
  - Need to cross check IPM plotids for Suresh

 16 Mar 2016
  Lori, Gio, Suresh
  - There is a chance of Canadian collaborators coming to the TD project
  - Need to have TD plotting tools running by the time of their meeting
  - Need to differentiate years within projects as some data is shared
    and others not
  - [ ] remove individual plots on the watertable plotting
  - Verify what happens when you click the ALL station in site progress
  - [ ] Fix the titles on the Decagon highcharts plots
  - Attempt to get revisions on spreadsheets again via Google
  - Perhaps we should archive some edits needed in SS Site Edits/Review

  2 Mar 2016
  Lori, Gio, Suresh, Katie
  - [x] fix issue with empty smartsheet rows causing totals to be off
  - Probably having lunch together on the 7th
  - [ ] Need to create a highcharts plot of soil organic carbon vs ph
  - soil organic carbon should decrease with increasing depth
  - Gio wants the data export separated for soil and agronomic